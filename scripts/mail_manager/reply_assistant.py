"""AI reply composition with feedback learning.

Provides AI-powered reply suggestions based on email context, thread history,
and learned feedback from previous interactions.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mail_manager.db import MailDatabase
    from mail_manager.llm.client import LLMClient

logger = logging.getLogger(__name__)


def compose_ai_reply(
    llm_client: LLMClient,
    original_email: dict[str, Any],
    thread_context: list[dict[str, Any]] | None = None,
    user_intent: str | None = None,
    few_shot_examples: list[dict[str, str]] | None = None,
) -> str:
    """Compose AI-suggested reply for an email.

    Args:
        llm_client: LLM client for generation.
        original_email: The email to reply to, with keys: sender, subject,
            date, body_text.
        thread_context: Previous emails in thread (optional).
        user_intent: Specific intent for reply (optional).
        few_shot_examples: Examples from feedback (optional).

    Returns:
        Suggested reply text.
    """
    from mail_manager.llm.prompts import REPLY_SYSTEM_PROMPT

    # Build context string
    context = f"""Original Email:
From: {original_email.get('sender', 'Unknown')}
Subject: {original_email.get('subject', 'No Subject')}
Date: {original_email.get('date', 'Unknown')}
Body:
{original_email.get('body_text', '')[:1000]}
"""

    # Add thread summary if available
    if thread_context and len(thread_context) > 1:
        from mail_manager.thread_manager import generate_thread_summary

        summary = generate_thread_summary(llm_client, thread_context, original_email)
        if summary:
            context = f"Thread Context:\n{summary}\n\n{context}"

    # Build conversation history with few-shot examples
    conversation: list[dict[str, str]] = []
    if few_shot_examples:
        for example in few_shot_examples[:3]:  # Limit to 3 examples
            conversation.append({"role": "user", "content": example["original"]})
            conversation.append({"role": "assistant", "content": example["reply"]})

    # Build user message
    user_message = "Please compose a reply to this email."
    if user_intent:
        user_message = f"Please compose a reply with this intent: {user_intent}"

    # Add context as part of conversation
    full_message = f"{context}\n\n{user_message}"

    response = llm_client.chat_with_history(
        system_prompt=REPLY_SYSTEM_PROMPT,
        conversation=conversation,
        user_message=full_message,
    )
    return response.content


def store_reply_feedback(
    db: MailDatabase,
    original_message_id: str,
    original_email: str,
    suggested_reply: str,
    user_edited_reply: str | None = None,
    is_positive: bool = True,
) -> None:
    """Store feedback for learning.

    Args:
        db: MailDatabase instance for storage.
        original_message_id: Message ID of the original email.
        original_email: Content of the original email.
        suggested_reply: The AI-suggested reply.
        user_edited_reply: User's edited version (optional).
        is_positive: Whether the feedback is positive (default True).
    """
    db.save_reply_feedback(
        original_message_id=original_message_id,
        original_email=original_email,
        suggested_reply=suggested_reply,
        user_edited_reply=user_edited_reply,
        is_positive=is_positive,
    )


def get_few_shot_examples(
    db: MailDatabase,
    limit: int = 5,
) -> list[dict[str, str]]:
    """Get few-shot examples from positive feedback.

    Args:
        db: MailDatabase instance for retrieval.
        limit: Maximum number of examples to return.

    Returns:
        List of dicts with 'original' and 'reply' keys.
    """
    feedback = db.get_reply_feedback(limit=limit, positive_only=True)
    examples: list[dict[str, str]] = []
    for fb in feedback:
        # Use edited reply if available, otherwise suggested
        reply = fb.get("user_edited_reply") or fb.get("suggested_reply")
        if reply:
            examples.append(
                {
                    "original": fb.get("original_email", ""),
                    "reply": reply,
                }
            )
    return examples
