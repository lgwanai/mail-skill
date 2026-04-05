"""Enhanced thread management with sender/recipient matching.

Provides comprehensive thread view that includes all related correspondence,
timeline formatting, and LLM-powered thread summaries.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mail_manager.db import MailDatabase
    from mail_manager.llm.client import LLMClient

logger = logging.getLogger(__name__)


def get_enhanced_thread_timeline(
    db: MailDatabase,
    seed_message_id: str,
    include_sender_thread: bool = True,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Get enhanced thread timeline including emails from thread participants.

    Starts with base timeline from db.get_thread_timeline(), then optionally
    expands to include emails from the same sender/recipient.

    Args:
        db: MailDatabase instance for email queries.
        seed_message_id: Message ID to start the thread from.
        include_sender_thread: If True, include emails from thread participants.
        limit: Maximum number of emails to return.

    Returns:
        List of email dictionaries sorted by date, with duplicates removed.
    """
    # Start with existing timeline from db
    timeline = db.get_thread_timeline(seed_message_id, limit)

    # Always sort by date ascending, even without sender thread expansion
    timeline.sort(key=lambda x: x.get("date") or "")

    if not include_sender_thread or not timeline:
        return timeline

    # Extract unique participants (sender + recipients)
    participants: set[str] = set()
    for email in timeline:
        sender = email.get("sender")
        if sender:
            participants.add(sender)

        recipient = email.get("recipient")
        if recipient:
            # Recipients may be comma-separated
            for r in recipient.split(","):
                stripped = r.strip()
                if stripped:
                    participants.add(stripped)

    # Track existing message IDs for deduplication
    existing_ids: set[str] = {e["message_id"] for e in timeline}

    # Find related emails by participants
    for participant in participants:
        related = db.search_emails(sender=participant, limit=20)
        for email in related:
            msg_id = email.get("message_id")
            if msg_id and msg_id not in existing_ids:
                timeline.append(email)
                existing_ids.add(msg_id)

    # Sort by date ascending
    timeline.sort(key=lambda x: x.get("date") or "")

    # Respect limit
    return timeline[:limit]


def generate_thread_summary(
    llm_client: LLMClient,
    timeline: list[dict[str, Any]],
    current_email: dict[str, Any] | None = None,
) -> str:
    """Generate a concise summary of the email thread using LLM.

    Args:
        llm_client: LLM client for generating summaries.
        timeline: List of emails in the thread.
        current_email: Optional current email to exclude from summary context.

    Returns:
        Thread summary string, or empty string for empty/single-email timelines.
    """
    # Return empty for empty or single-email timelines
    if len(timeline) <= 1:
        return ""

    from mail_manager.llm.prompts import THREAD_SUMMARY_PROMPT

    # Build thread context for LLM
    thread_text: list[str] = []
    for email in timeline:
        # Skip current email if provided
        if current_email and email.get("message_id") == current_email.get("message_id"):
            continue

        sender = email.get("sender", "Unknown")
        date = email.get("date", "Unknown")
        subject = email.get("subject", "No Subject")
        body_preview = (email.get("body_text") or "")[:200]

        thread_text.append(
            f"From: {sender}\n"
            f"Date: {date}\n"
            f"Subject: {subject}\n"
            f"Preview: {body_preview}..."
        )

    # If only current email was in timeline, return empty
    if not thread_text:
        return ""

    # Build prompt
    thread_content = "\n---\n".join(thread_text)
    prompt = f"{THREAD_SUMMARY_PROMPT}\n\n{thread_content}\n\nSummary:"

    # Call LLM
    response = llm_client.chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=200,
    )

    return response.content


def format_thread_view(
    timeline: list[dict[str, Any]],
    current_message_id: str | None = None,
    display_mode: str = "full",
    thread_summary: str | None = None,
    llm_client: LLMClient | None = None,
    port: int | None = None,
    attachments_dir: str | None = None,
) -> str:
    """Format thread timeline for display.

    Args:
        timeline: List of emails in the thread, sorted by date.
        current_message_id: Message ID of the current email to highlight.
        display_mode: "full" for detailed view, "summary" for condensed view.
        thread_summary: Pre-generated thread summary (optional).
        llm_client: Optional LLM client for generating summary on the fly.
        port: Optional port for attachment preview URLs.
        attachments_dir: Optional base directory for attachments.

    Returns:
        Markdown-formatted thread view string.
    """
    if not timeline:
        return "No thread to display."

    sections: list[str] = []

    # Find current email if specified
    current_email: dict[str, Any] | None = None
    if current_message_id:
        for email in timeline:
            if email.get("message_id") == current_message_id:
                current_email = email
                break

    # Add thread summary if available
    if thread_summary:
        sections.append(f"**Thread Summary:** {thread_summary}")
        sections.append("")
    elif llm_client and current_email and len(timeline) > 1:
        # Generate summary on the fly
        summary = generate_thread_summary(llm_client, timeline, current_email)
        if summary:
            sections.append(f"**Thread Summary:** {summary}")
            sections.append("")

    if display_mode == "summary":
        # Summary mode: brief info for each email
        sections.append("## Thread Timeline")
        for email in timeline:
            date = str(email.get("date") or "")[:10]
            sender = email.get("sender", "Unknown")
            subject = (email.get("subject") or "No Subject")[:50]

            if current_message_id and email.get("message_id") == current_message_id:
                sections.append(f"- **[Current] {date}** {sender}: {subject}")
            else:
                sections.append(f"- {date} {sender}: {subject}")
    else:
        # Full mode: detailed view
        from mail_manager.detail import format_email_detail

        sections.append("## Thread Timeline")

        # If no current_message_id specified, show full details for all emails
        if not current_message_id:
            for email in timeline:
                sections.append(format_email_detail(email, port, attachments_dir))
                sections.append("")
        else:
            # Show current email with full detail, others as summary
            for email in timeline:
                msg_id = email.get("message_id", "")

                if msg_id == current_message_id:
                    sections.append("### Current Email")
                    sections.append(format_email_detail(email, port, attachments_dir))
                else:
                    # Other emails shown as summary
                    date = str(email.get("date") or "")[:10]
                    sender = email.get("sender", "Unknown")
                    subject = (email.get("subject") or "No Subject")[:50]
                    sections.append(f"- **{date}** {sender}: {subject}")

    return "\n".join(sections)
