"""
Email detail formatting module for Markdown output.

Provides functions to format email details as Markdown for CLI display,
including headers, classification info, attachments with preview links,
and thread context.
"""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import quote


def _format_header_line(label: str, value: str | None) -> str:
    """Format a single header line as Markdown.

    Args:
        label: The label for the header (e.g., "From", "To").
        value: The value for the header, or None/empty to skip.

    Returns:
        Formatted "**Label:** value" string, or empty string if value is None/empty.
    """
    if not value:
        return ""
    return f"**{label}:** {value}"


def _format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes.

    Returns:
        Human-readable size string (e.g., "2.3 MB", "156 KB").
    """
    if size_bytes >= 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
    elif size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.0f} KB"
    else:
        return f"{size_bytes} B"


def _truncate_subject(subject: str, max_length: int = 50) -> str:
    """Truncate subject to max_length characters.

    Args:
        subject: The subject string to truncate.
        max_length: Maximum length (default 50).

    Returns:
        Truncated subject with "..." if needed.
    """
    if len(subject) <= max_length:
        return subject
    return subject[:max_length - 3] + "..."


def format_headers(email: dict[str, Any]) -> str:
    """Format email headers as Markdown.

    Args:
        email: Email dictionary with sender, recipient, cc, date fields.

    Returns:
        Markdown-formatted header section.
    """
    lines = []

    from_line = _format_header_line("From", email.get("sender"))
    if from_line:
        lines.append(from_line)

    to_line = _format_header_line("To", email.get("recipient"))
    if to_line:
        lines.append(to_line)

    cc_line = _format_header_line("Cc", email.get("cc"))
    if cc_line:
        lines.append(cc_line)

    date_line = _format_header_line("Date", email.get("date"))
    if date_line:
        lines.append(date_line)

    return "\n".join(lines)


def format_classification(email: dict[str, Any]) -> str:
    """Format classification info as Markdown.

    Args:
        email: Email dictionary with importance, category, classification_confidence fields.

    Returns:
        Markdown-formatted classification section, or empty string if default classification.
    """
    importance = email.get("importance", "normal")
    category = email.get("category", "uncategorized")
    confidence = email.get("classification_confidence", 0.0)
    manual_override = email.get("manual_override", False)

    # Return empty if default classification
    if importance == "normal" and category == "uncategorized":
        return ""

    lines = ["### Classification"]

    # Format importance line with confidence if applicable
    confidence_str = ""
    if confidence > 0.5 and not manual_override:
        confidence_str = f" (confidence: {confidence:.2f})"

    lines.append(f"- **Importance:** {importance}{confidence_str}")
    lines.append(f"- **Category:** {category}")

    return "\n".join(lines)


def format_attachments_detail(
    email: dict[str, Any],
    port: int,
    attachments_dir: str,
) -> str:
    """Format attachments with preview URLs as Markdown.

    Args:
        email: Email dictionary with attachments list.
        port: Port number for the preview server.
        attachments_dir: Base directory for attachments.

    Returns:
        Markdown-formatted attachments section, or empty string if no attachments.
    """
    attachments = email.get("attachments", [])
    if not attachments:
        return ""

    lines = ["### Attachments"]

    for i, att in enumerate(attachments, 1):
        filename = att.get("filename", "unknown")
        size = att.get("size", 0)
        local_path = att.get("local_path", "")

        # Generate preview URL
        if local_path:
            rel_path = os.path.relpath(local_path, attachments_dir)
            encoded_path = quote(rel_path)
            url = f"http://127.0.0.1:{port}/{encoded_path}"
            size_str = _format_file_size(size)

            # Format line: 1. [filename.pdf](url) - 2.3 MB
            line = f"{i}. [{filename}]({url}) - {size_str}"
            lines.append(line)
        else:
            # No local path, just show filename and size
            size_str = _format_file_size(size)
            line = f"{i}. {filename} - {size_str}"
            lines.append(line)

    return "\n".join(lines)


def format_thread_context(
    email: dict[str, Any],
    timeline: list[dict[str, Any]],
    current_message_id: str,
) -> str:
    """Format thread context as Markdown.

    Args:
        email: Current email dictionary.
        timeline: List of emails in the thread, sorted by date.
        current_message_id: Message ID of the current email.

    Returns:
        Markdown-formatted thread context section, or empty string if no thread.
    """
    # Return empty if only one email (no thread context)
    if len(timeline) <= 1:
        return ""

    lines = ["### Thread Context"]

    # Sort timeline by date ascending
    sorted_timeline = sorted(timeline, key=lambda x: x.get("date", "") or "")

    # Find current email position
    current_idx = None
    for i, e in enumerate(sorted_timeline):
        if e.get("message_id") == current_message_id:
            current_idx = i
            break

    for i, e in enumerate(sorted_timeline):
        msg_id = e.get("message_id", "")
        subject = _truncate_subject(e.get("subject", ""))
        date = (e.get("date") or "")[:10]  # Just the date part

        if msg_id == current_message_id:
            # Current email - bold
            lines.append(f"- **[Current] {subject}** ({date})")
        elif current_idx is not None and i < current_idx:
            # Parent email
            lines.append(f"- [Parent] {subject} ({date})")
        else:
            # Reply email
            lines.append(f"- [Reply] {subject} ({date})")

    return "\n".join(lines)


def format_email_detail(
    email: dict[str, Any],
    port: int | None = None,
    attachments_dir: str | None = None,
) -> str:
    """Format complete email detail as Markdown.

    Args:
        email: Email dictionary with all fields.
        port: Optional port for attachment preview URLs.
        attachments_dir: Optional base directory for attachments.

    Returns:
        Complete Markdown-formatted email detail.
    """
    sections = []

    # Header section with subject as H2
    subject = email.get("subject", "(No Subject)")
    sections.append(f"## {subject}")

    # Headers
    headers = format_headers(email)
    if headers:
        sections.append(headers)

    # Classification (if available)
    classification = format_classification(email)
    if classification:
        sections.append("")
        sections.append(classification)

    # Attachments (if available and port provided)
    if port and attachments_dir:
        attachments = format_attachments_detail(email, port, attachments_dir)
        if attachments:
            sections.append("")
            sections.append(attachments)

    # Body
    body_text = email.get("body_text", "")
    if body_text:
        sections.append("")
        sections.append("---")
        sections.append("")
        sections.append(body_text)

    return "\n".join(sections)
