"""LLM integration module for AI-powered features.

Provides a thin wrapper around OpenAI SDK for consistent interface and easy testing.
"""

from mail_manager.llm.client import LLMClient, LLMResponse

__all__ = ["LLMClient", "LLMResponse"]
