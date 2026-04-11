"""Enhanced thread management with sender/recipient matching.

Provides comprehensive thread view that includes all related correspondence,
timeline formatting, and LLM-powered thread summaries.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mail_manager.db import MailDatabase
    from mail_manager.llm.client import LLMClient

logger = logging.getLogger(__name__)


def normalize_subject(subject: str) -> str:
    """Normalize email subject for thread matching.

    Removes common prefixes like Re:, Fwd:, FW:, 回复:, 转发: etc.
    to enable subject-based thread association.

    Args:
        subject: Original email subject.

    Returns:
        Normalized subject string (lowercase, stripped of prefixes).

    Example:
        >>> normalize_subject("Re: Re: Project Update")
        'project update'
        >>> normalize_subject("Fwd: 会议通知")
        '会议通知'
    """
    if not subject:
        return ""

    # Common reply/forward prefixes in multiple languages
    prefixes = [
        r"^re:\s*",
        r"^fwd:\s*",
        r"^fw:\s*",
        r"^回复:\s*",
        r"^转发:\s*",
        r"^回覆:\s*",
        r"^答覆:\s*",
    ]

    result = subject.strip().lower()

    # Repeatedly remove prefixes until no more match
    changed = True
    while changed:
        changed = False
        for pattern in prefixes:
            new_result = re.sub(pattern, "", result, flags=re.IGNORECASE)
            if new_result != result:
                result = new_result.strip()
                changed = True

    return result


def calculate_text_similarity(text1: str, text2: str) -> float:
    """Calculate simple text similarity based on common words.

    Uses word-level Jaccard similarity for quick comparison.
    For more accurate similarity, use embedding-based methods.

    Args:
        text1: First text to compare.
        text2: Second text to compare.

    Returns:
        Similarity score between 0.0 and 1.0.
    """
    if not text1 or not text2:
        return 0.0

    # Tokenize into words (Chinese characters handled separately)
    def tokenize(text: str) -> set[str]:
        # Simple tokenization: split on whitespace and punctuation
        words = set(re.findall(r"[\w]+", text.lower()))
        # Also add individual characters for Chinese
        chinese_chars = set(re.findall(r"[\u4e00-\u9fff]", text))
        return words | chinese_chars

    words1 = tokenize(text1)
    words2 = tokenize(text2)

    if not words1 or not words2:
        return 0.0

    intersection = words1 & words2
    union = words1 | words2

    return len(intersection) / len(union) if union else 0.0


def get_enhanced_thread_timeline(
    db: MailDatabase,
    seed_message_id: str,
    include_sender_thread: bool = True,
    include_subject_match: bool = True,
    subject_similarity_threshold: float = 0.7,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Get enhanced thread timeline including related emails.

    Starts with base timeline from db.get_thread_timeline(), then expands to include:
    1. Emails from same sender/recipient participants
    2. Emails with similar subjects (normalized, removing Re:/Fwd: prefixes)

    Args:
        db: MailDatabase instance for email queries.
        seed_message_id: Message ID to start the thread from.
        include_sender_thread: If True, include emails from thread participants.
        include_subject_match: If True, include emails with similar subjects.
        subject_similarity_threshold: Minimum similarity score for subject matching.
        limit: Maximum number of emails to return.

    Returns:
        List of email dictionaries sorted by date, with duplicates removed.
    """
    timeline = db.get_thread_timeline(seed_message_id, limit)
    timeline.sort(key=lambda x: x.get("date") or "")

    if not timeline:
        return timeline

    existing_ids: set[str] = {e["message_id"] for e in timeline}

    # Subject-based matching
    if include_subject_match:
        seed_email = timeline[0]
        seed_subject = seed_email.get("subject", "")
        normalized_seed = normalize_subject(seed_subject)

        if normalized_seed and len(normalized_seed) >= 3:
            # Search for emails with similar subjects
            potential_matches = db.search_emails(limit=50)
            for email in potential_matches:
                msg_id = email.get("message_id")
                if msg_id and msg_id not in existing_ids:
                    email_subject = email.get("subject", "")
                    normalized_email = normalize_subject(email_subject)

                    if normalized_email and len(normalized_email) >= 3:
                        similarity = calculate_text_similarity(normalized_seed, normalized_email)
                        if similarity >= subject_similarity_threshold:
                            timeline.append(email)
                            existing_ids.add(msg_id)

    # Participant-based matching
    if include_sender_thread and len(timeline) < limit:
        participants: set[str] = set()
        for email in timeline:
            sender = email.get("sender")
            if sender:
                participants.add(sender)

            recipient = email.get("recipient")
            if recipient:
                for r in recipient.split(","):
                    stripped = r.strip()
                    if stripped:
                        participants.add(stripped)

        for participant in participants:
            if len(timeline) >= limit:
                break
            related = db.search_emails(sender=participant, limit=20)
            for email in related:
                msg_id = email.get("message_id")
                if msg_id and msg_id not in existing_ids:
                    timeline.append(email)
                    existing_ids.add(msg_id)
                    if len(timeline) >= limit:
                        break

    timeline.sort(key=lambda x: x.get("date") or "")
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
            f"From: {sender}\nDate: {date}\nSubject: {subject}\nPreview: {body_preview}..."
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
