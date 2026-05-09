"""LLM client abstraction for all AI-powered features.

Provides a thin wrapper around OpenAI SDK for consistent interface and easy testing.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from openai import APIError, OpenAI, RateLimitError

from mail_manager.errors import MailSkillError


class AIConfigError(Exception):
    """Raised when AI features are not configured."""

    pass


def is_ai_enabled() -> bool:
    """Check if AI features are enabled (configured).

    Returns:
        True if LLM_API_KEY is configured, False otherwise.
    """
    return bool(os.getenv("LLM_API_KEY"))


@dataclass
class LLMResponse:
    """Standard LLM response structure."""

    content: str
    model: str
    usage: dict[str, int]
    finish_reason: str


class LLMClient:
    """Thin wrapper around OpenAI SDK for LLM operations."""

    def __init__(self) -> None:
        """Initialize LLM client with environment configuration.

        Uses environment variables:
        - LLM_API_KEY: Required for API access
        - LLM_API_BASE: Optional, for custom endpoints
        - LLM_MODEL_NAME: Model for chat completions (default: gpt-4o-mini)
        - LLM_TIMEOUT: Request timeout in seconds (default: 30)

        Raises:
            AIConfigError: If LLM_API_KEY is not configured.
        """
        api_key = os.getenv("LLM_API_KEY")
        if not api_key:
            raise AIConfigError(
                "AI features not configured. "
                "Please set LLM_API_KEY in config.txt to enable AI features."
            )

        api_base = os.getenv("LLM_API_BASE")
        try:
            timeout = int(os.getenv("LLM_TIMEOUT", "30"))
        except (ValueError, TypeError):
            timeout = 30

        self.client = OpenAI(api_key=api_key, base_url=api_base, timeout=timeout)
        self.model = os.getenv("LLM_MODEL_NAME", "gpt-4o-mini")

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        """Send chat completion request.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            temperature: Sampling temperature (0.0 to 2.0).
            max_tokens: Maximum tokens in response.

        Returns:
            LLMResponse with content, model, usage, and finish_reason.

        Raises:
            MailSkillError: If API call fails.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            if not response.choices:
                raise MailSkillError("LLM returned empty response choices")

            choice = response.choices[0]
            usage = response.usage
            return LLMResponse(
                content=choice.message.content or "",
                model=response.model or self.model,
                usage={
                    "prompt_tokens": usage.prompt_tokens if usage else 0,
                    "completion_tokens": usage.completion_tokens if usage else 0,
                    "total_tokens": usage.total_tokens if usage else 0,
                },
                finish_reason=choice.finish_reason or "unknown",
            )
        except (APIError, RateLimitError) as e:
            raise MailSkillError(f"LLM API error: {e}") from e
        except (IndexError, AttributeError, KeyError) as e:
            raise MailSkillError(f"Unexpected LLM response format: {e}") from e

    def chat_with_history(
        self,
        system_prompt: str,
        conversation: list[dict[str, str]],
        user_message: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> LLMResponse:
        """Chat with conversation history context.

        Args:
            system_prompt: System prompt to set behavior.
            conversation: List of prior messages with 'role' and 'content'.
            user_message: Current user message.
            temperature: Sampling temperature (0.0 to 2.0).
            max_tokens: Maximum tokens in response.

        Returns:
            LLMResponse with content, model, usage, and finish_reason.
        """
        messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation)
        messages.append({"role": "user", "content": user_message})
        return self.chat(messages, temperature=temperature, max_tokens=max_tokens)
