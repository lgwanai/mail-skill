"""Email summary report functionality.

Provides email grouping by sender and individual email summarization
using LLM for structured summary extraction.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from itertools import groupby
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mail_manager.llm.client import LLMClient

from mail_manager.llm.prompts import EMAIL_SUMMARY_PROMPT, OVERALL_SUMMARY_PROMPT


def _escape_braces(text: str) -> str:
    """Escape { and } so str.format() treats them as literal text."""
    return text.replace("{", "{{").replace("}", "}}")


@dataclass
class EmailSummary:
    """Structured summary of an individual email.

    Holds the key information extracted from an email for reporting purposes.

    Attributes:
        subject: The email subject line.
        key_points: List of main points from the email body.
        action_items: List of actions requested or implied.
        deadline: Due date if mentioned (YYYY-MM-DD format), or None.
        priority: Priority level (high/medium/low).
        one_liner: Single sentence summary of the email.
    """

    subject: str
    key_points: list[str] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)
    deadline: str | None = None
    priority: str = "medium"
    one_liner: str = ""


@dataclass
class OverallSummary:
    """Overall summary aggregating all email summaries.

    Holds consolidated information from all individual email summaries
    for reporting purposes.

    Attributes:
        overview: 2-3 sentence overview of all emails.
        key_themes: List of main themes identified across emails.
        all_action_items: List of action items with sender attribution.
            Each item is a dict with 'item', 'sender', and 'priority' keys.
        upcoming_deadlines: List of deadlines sorted by date.
            Each item is a dict with 'date', 'description', and 'sender' keys.
        recommended_priority: List of top 3 items to prioritize.
    """

    overview: str = ""
    key_themes: list[str] = field(default_factory=list)
    all_action_items: list[dict[str, str]] = field(default_factory=list)
    upcoming_deadlines: list[dict[str, str]] = field(default_factory=list)
    recommended_priority: list[str] = field(default_factory=list)


@dataclass
class ReplyInfo:
    """Information about a reply to an email.

    Holds details about an email sent in response to received email.

    Attributes:
        message_id: Message ID of the sent email.
        subject: Subject of the sent email.
        date: Date the reply was sent.
        one_liner: Brief summary of reply content.
    """

    message_id: str
    subject: str = ""
    date: datetime | None = None
    one_liner: str = ""


SENT_FOLDER_NAMES = [
    "Sent",
    "Sent Messages",
    "Sent Items",
    "已发送",
    "已发送邮件",
    "发件箱",
]


def match_sent_emails_to_received(
    sent_emails: list[dict[str, Any]],
    received_emails: list[dict[str, Any]],
) -> dict[str, ReplyInfo]:
    """Match sent emails to received emails based on in_reply_to and subject.

    Args:
        sent_emails: List of sent email dictionaries.
        received_emails: List of received email dictionaries.

    Returns:
        Dict mapping received message_id to ReplyInfo.

    Example:
        >>> sent = [{"message_id": "s1", "in_reply_to": "r1", "subject": "Re: Test"}]
        >>> received = [{"message_id": "r1", "subject": "Test"}]
        >>> matches = match_sent_emails_to_received(sent, received)
        >>> "r1" in matches
        True
    """
    from mail_manager.thread_manager import normalize_subject

    matches: dict[str, ReplyInfo] = {}

    received_by_id: dict[str, dict[str, Any]] = {}
    received_by_subject: dict[str, dict[str, Any]] = {}
    for email in received_emails:
        normalized_subj = normalize_subject(email.get("subject", ""))
        msg_id = email.get("message_id", "")
        if msg_id:
            received_by_id[msg_id] = email
        if normalized_subj and len(normalized_subj) >= 3:
            normalized_subj_clean = normalized_subj.replace(" ", "")
            received_by_subject[normalized_subj_clean] = email

    for sent in sent_emails:
        in_reply_to = sent.get("in_reply_to", "")
        if in_reply_to:
            target_id = in_reply_to.strip()
            if target_id.startswith("<") and target_id.endswith(">"):
                target_id = target_id[1:-1]
            if target_id in received_by_id:
                matches[target_id] = ReplyInfo(
                    message_id=sent.get("message_id", ""),
                    subject=sent.get("subject", ""),
                    date=sent.get("date"),
                    one_liner=(sent.get("body_text", "") or "")[:100],
                )
                continue

        sent_subject = normalize_subject(sent.get("subject", ""))
        if sent_subject and len(sent_subject) >= 3:
            sent_subject_clean = sent_subject.replace(" ", "")
            for subj_key, received_email in received_by_subject.items():
                if sent_subject_clean == subj_key:
                    msg_id = received_email.get("message_id", "")
                    if msg_id and msg_id not in matches:
                        matches[msg_id] = ReplyInfo(
                            message_id=sent.get("message_id", ""),
                            subject=sent.get("subject", ""),
                            date=sent.get("date"),
                            one_liner=(sent.get("body_text", "") or "")[:100],
                        )
                    break

    return matches


def group_emails_by_sender(emails: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group emails by sender address.

    Groups a list of email dictionaries by their sender field, sorting
    each group by date. Emails with missing or empty sender are grouped
    under "未知发件人" (Unknown Sender).

    Args:
        emails: List of email dictionaries with 'sender' and 'date' fields.

    Returns:
        Dict mapping sender email addresses to lists of emails from that sender.
        Each list is sorted by date (ascending). Emails without sender are
        grouped under "未知发件人".

    Example:
        >>> emails = [
        ...     {"sender": "alice@example.com", "subject": "Hi", "date": datetime(2024, 1, 15)},
        ...     {"sender": "alice@example.com", "subject": "Re: Hi", "date": datetime(2024, 1, 16)},
        ... ]
        >>> result = group_emails_by_sender(emails)
        >>> list(result.keys())
        ['alice@example.com']
        >>> len(result['alice@example.com'])
        2
    """
    if not emails:
        return {}

    UNKNOWN_SENDER = "未知发件人"

    # Process all emails - don't skip any
    processed_emails = []
    for e in emails:
        sender = e.get("sender", "")
        if not sender or not sender.strip():
            e = {**e, "sender": UNKNOWN_SENDER}
        processed_emails.append(e)

    if not processed_emails:
        return {}

    # Sort by sender first (required for groupby), then by date within groups
    sorted_emails = sorted(processed_emails, key=lambda e: (e.get("sender", ""), e.get("date")))

    # Group by sender
    result: dict[str, list[dict[str, Any]]] = {}
    for sender, group in groupby(sorted_emails, key=lambda e: e.get("sender", "")):
        result[sender] = sorted(list(group), key=lambda e: e.get("date"))

    return result


def summarize_email(llm_client: LLMClient, email: dict[str, Any]) -> EmailSummary:
    """Summarize a single email using LLM.

    Uses the LLM client to extract structured summary information from an email.

    Args:
        llm_client: LLM client for making chat completion requests.
        email: Email dictionary with sender, subject, date, and body_text fields.

    Returns:
        EmailSummary with extracted key points, action items, deadline, priority,
        and one-liner summary. Returns fallback values on JSON parsing errors.

    Example:
        >>> from mail_manager.llm.client import LLMClient
        >>> llm = LLMClient()
        >>> email = {"sender": "a@b.com", "subject": "Test", "date": datetime.now(), "body_text": "Hello"}
        >>> summary = summarize_email(llm, email)
        >>> summary.subject
        'Test'
    """
    # Extract email fields with defaults
    sender = email.get("sender", "Unknown")
    subject = email.get("subject", "No Subject")
    date = email.get("date", "Unknown")
    body_text = email.get("body_text", "") or ""

    # Truncate long body text to avoid token limits
    max_body_length = 2000
    if len(body_text) > max_body_length:
        body_text = body_text[:max_body_length] + "..."

    # Format the prompt with email details
    prompt = EMAIL_SUMMARY_PROMPT.format(
        sender=_escape_braces(sender),
        subject=_escape_braces(subject),
        date=str(date),
        body=_escape_braces(body_text),
    )

    # Call LLM with low temperature for consistent JSON output
    response = llm_client.chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=500,
    )

    # Parse JSON from response, handling markdown code blocks
    content = response.content.strip()

    # Remove markdown code block wrapper if present
    if content.startswith("```"):
        # Match ```json or just ``` at start and ``` at end
        content = re.sub(r"^```(?:json)?\s*\n?", "", content)
        content = re.sub(r"\n?```\s*$", "", content)
        content = content.strip()

    # Parse JSON with fallback values
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        # Return fallback summary on parse error
        return EmailSummary(
            subject=subject,
            key_points=[],
            action_items=[],
            deadline=None,
            priority="medium",
            one_liner="",
        )

    return EmailSummary(
        subject=subject,
        key_points=data.get("key_points", []),
        action_items=data.get("action_items", []),
        deadline=data.get("deadline"),
        priority=data.get("priority", "medium"),
        one_liner=data.get("one_liner", ""),
    )


def generate_overall_summary(
    llm_client: LLMClient,
    sender_summaries: dict[str, list[EmailSummary]],
) -> OverallSummary:
    """Generate overall summary from sender-grouped summaries.

    Aggregates all individual email summaries into a consolidated overview
    with key themes, action items, deadlines, and priority recommendations.

    Args:
        llm_client: LLM client for making chat completion requests.
        sender_summaries: Dict mapping sender email to their list of EmailSummary.

    Returns:
        OverallSummary with consolidated information. Returns fallback values
        on JSON parsing errors.

    Example:
        >>> from mail_manager.llm.client import LLMClient
        >>> llm = LLMClient()
        >>> summaries = {"alice@example.com": [EmailSummary(subject="Test", ...)]}
        >>> overall = generate_overall_summary(llm, summaries)
        >>> overall.overview
        'Summary of all emails...'
    """
    # Format sender summaries for prompt
    summaries_text: list[str] = []
    for sender, summaries in sender_summaries.items():
        summaries_text.append(f"\n### Sender: {sender}")
        for i, s in enumerate(summaries, 1):
            summaries_text.append(f"\n{i}. {s.subject}")
            summaries_text.append(f"   Summary: {s.one_liner}")
            if s.action_items:
                summaries_text.append(f"   Actions: {', '.join(s.action_items)}")
            if s.deadline:
                summaries_text.append(f"   Deadline: {s.deadline}")

    # Format the prompt
    prompt = OVERALL_SUMMARY_PROMPT.format(
        sender_summaries=_escape_braces("\n".join(summaries_text)),
    )

    # Call LLM with low temperature for consistent JSON output
    response = llm_client.chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=1000,
    )

    # Parse JSON from response, handling markdown code blocks
    content = response.content.strip()

    # Remove markdown code block wrapper if present
    if content.startswith("```"):
        # Match ```json or just ``` at start and ``` at end
        content = re.sub(r"^```(?:json)?\s*\n?", "", content)
        content = re.sub(r"\n?```\s*$", "", content)
        content = content.strip()

    # Parse JSON with fallback values
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        # Return fallback summary on parse error
        return OverallSummary(
            overview="",
            key_themes=[],
            all_action_items=[],
            upcoming_deadlines=[],
            recommended_priority=[],
        )

    return OverallSummary(
        overview=data.get("overview", ""),
        key_themes=data.get("key_themes", []),
        all_action_items=data.get("all_action_items", []),
        upcoming_deadlines=data.get("upcoming_deadlines", []),
        recommended_priority=data.get("recommended_priority", []),
    )


def format_summary_report(
    recipient: str,
    date_from: date,
    date_to: date,
    sender_summaries: dict[str, list[tuple[dict[str, Any], EmailSummary]]],
    overall: OverallSummary,
    reply_info: dict[str, ReplyInfo] | None = None,
) -> str:
    """Format complete summary report as Markdown.

    Args:
        recipient: Email address of the recipient.
        date_from: Report start date.
        date_to: Report end date.
        sender_summaries: Dict mapping sender to list of (email, EmailSummary) tuples.
        overall: OverallSummary object with aggregated information.
        reply_info: Optional dict mapping received message_id to ReplyInfo.

    Returns:
        Markdown-formatted report string.

    Example:
        >>> report = format_summary_report(
        ...     recipient="user@example.com",
        ...     date_from=date(2024, 1, 1),
        ...     date_to=date(2024, 1, 7),
        ...     sender_summaries={},
        ...     overall=OverallSummary(overview="No emails"),
        ... )
        >>> "# Email Summary Report" in report
        True
    """
    sections: list[str] = []

    # Header
    sections.append("# Email Summary Report")
    sections.append("")
    sections.append(f"**Recipient:** {recipient}")
    sections.append(f"**Period:** {date_from} to {date_to}")
    sections.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    sections.append("")

    # Overview section
    sections.append("## Overview")
    sections.append("")
    sections.append(overall.overview)
    sections.append("")

    # Key themes
    if overall.key_themes:
        sections.append("### Key Themes")
        for theme in overall.key_themes:
            sections.append(f"- {theme}")
        sections.append("")

    # Recommended priority
    if overall.recommended_priority:
        sections.append("### Recommended Priority")
        for i, item in enumerate(overall.recommended_priority, 1):
            sections.append(f"{i}. {item}")
        sections.append("")

    # All action items
    if overall.all_action_items:
        sections.append("## All Action Items")
        sections.append("")
        sections.append("| Priority | Action | Sender |")
        sections.append("|----------|--------|--------|")
        for item in sorted(
            overall.all_action_items,
            key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(x.get("priority", "medium"), 1),
        ):
            sections.append(
                f"| {item.get('priority', 'medium').upper()} | {item.get('item', '')} | {item.get('sender', '')} |"
            )
        sections.append("")

    # Upcoming deadlines
    if overall.upcoming_deadlines:
        sections.append("## Upcoming Deadlines")
        sections.append("")
        sections.append("| Date | Description | Sender |")
        sections.append("|------|-------------|--------|")
        for dl in sorted(overall.upcoming_deadlines, key=lambda x: x.get("date", "")):
            sections.append(
                f"| {dl.get('date', '')} | {dl.get('description', '')} | {dl.get('sender', '')} |"
            )
        sections.append("")

    # Per-sender sections
    sections.append("## Emails by Sender")
    sections.append("")

    total_emails = sum(len(emails) for emails in sender_summaries.values())
    replied_count = sum(
        1 for emails in sender_summaries.values() for email, _ in emails if email.get("is_replied")
    )
    sections.append(
        f"*Total emails: {total_emails} from {len(sender_summaries)} senders ({replied_count} 已回复)*"
    )
    sections.append("")

    for sender, email_summaries in sender_summaries.items():
        sections.append(f"### {sender}")
        sections.append("")

        for email, summary in email_summaries:
            # Email header
            subject = email.get("subject", "No Subject")
            email_date = email.get("date")
            if isinstance(email_date, datetime):
                date_str = email_date.strftime("%Y-%m-%d")
            elif email_date:
                date_str = str(email_date)[:10]
            else:
                date_str = "Unknown"

            # Check reply status
            is_replied = email.get("is_replied", False)
            replied_at = email.get("replied_at")
            reply_status = ""
            if is_replied:
                if replied_at:
                    if isinstance(replied_at, datetime):
                        reply_status = f" ✅ 已回复 ({replied_at.strftime('%Y-%m-%d')})"
                    else:
                        reply_status = f" ✅ 已回复 ({str(replied_at)[:10]})"
                else:
                    reply_status = " ✅ 已回复"

            msg_id = email.get("message_id", "")
            reply_detail = ""
            if reply_info and msg_id in reply_info:
                info = reply_info[msg_id]
                reply_date = info.date
                if isinstance(reply_date, datetime):
                    reply_date_str = reply_date.strftime("%Y-%m-%d")
                elif reply_date:
                    reply_date_str = str(reply_date)[:10]
                else:
                    reply_date_str = ""
                reply_detail = f" 📤 已回复于 {reply_date_str}" if reply_date_str else " 📤 已回复"
                reply_status = ""

            sections.append(f"#### {subject}{reply_status}{reply_detail}")
            sections.append(f"*Date: {date_str}*")
            sections.append("")

            if reply_info and msg_id in reply_info:
                info = reply_info[msg_id]
                sections.append("**Reply Summary:**")
                sections.append(f"> {(info.one_liner or '')[:200]}")
                sections.append("")

            # One-liner
            if summary.one_liner:
                sections.append(f"> {summary.one_liner}")
                sections.append("")

            # Key points
            if summary.key_points:
                sections.append("**Key Points:**")
                for point in summary.key_points:
                    sections.append(f"- {point}")
                sections.append("")

            # Action items
            if summary.action_items:
                sections.append("**Action Items:**")
                for action in summary.action_items:
                    sections.append(f"- [ ] {action}")
                sections.append("")

            # Deadline
            if summary.deadline:
                sections.append(f"**Deadline:** {summary.deadline}")
                sections.append("")

            sections.append("---")
            sections.append("")

    return "\n".join(sections)


def generate_email_summary_report(
    db: Any,
    llm_client: "LLMClient",
    recipient: str,
    date_from: date | None = None,
    date_to: date | None = None,
    days_back: int = 7,
    limit: int = 100,
    output_path: str | None = None,
    include_sent: bool = True,
) -> str:
    """Generate complete email summary report.

    Orchestrates the full report generation pipeline:
    1. Fetches emails by date range
    2. Groups emails by sender
    3. Summarizes each email using LLM
    4. Generates overall summary
    5. Formats as Markdown

    Args:
        db: MailDatabase instance with search_emails method.
        llm_client: LLM client for summarization.
        recipient: Email address of the recipient.
        date_from: Start date (default: days_back from today).
        date_to: End date (default: today).
        days_back: Number of days to look back if date_from not specified.
        limit: Maximum emails to process.
        output_path: Optional path to save report as file.
        include_sent: Whether to include sent emails for reply matching.

    Returns:
        Markdown-formatted report string, or message if no emails found.

    Example:
        >>> from mail_manager.db import MailDatabase
        >>> from mail_manager.llm.client import LLMClient
        >>> db = MailDatabase("emails.db")
        >>> llm = LLMClient()
        >>> report = generate_email_summary_report(
        ...     db=db, llm_client=llm, recipient="user@example.com"
        ... )
        >>> "# Email Summary Report" in report
        True
    """
    from datetime import timedelta

    if date_to is None:
        date_to = date.today()
    if date_from is None:
        date_from = date_to - timedelta(days=days_back)

    emails = db.search_emails(
        date_from=date_from.isoformat() if date_from else None,
        date_to=date_to.isoformat() if date_to else None,
        limit=limit,
    )

    if not emails:
        return f"No emails found for {recipient} between {date_from} and {date_to}."

    sender_groups = group_emails_by_sender(emails)

    sender_summaries: dict[str, list[tuple[dict[str, Any], EmailSummary]]] = {}
    all_summaries: dict[str, list[EmailSummary]] = {}
    failed_emails: list[dict[str, Any]] = []

    for sender, sender_emails in sender_groups.items():
        sender_summaries[sender] = []
        all_summaries[sender] = []

        for email in sender_emails:
            try:
                summary = summarize_email(llm_client, email)
                sender_summaries[sender].append((email, summary))
                all_summaries[sender].append(summary)
            except Exception as e:
                failed_emails.append(email)
                fallback = EmailSummary(
                    subject=email.get("subject", "无主题"),
                    key_points=["(摘要生成失败)"],
                    action_items=[],
                    deadline=None,
                    priority="medium",
                    one_liner=f"摘要失败: {str(e)[:50]}",
                )
                sender_summaries[sender].append((email, fallback))
                all_summaries[sender].append(fallback)

    reply_info: dict[str, ReplyInfo] = {}
    if include_sent:
        sent_emails: list[dict[str, Any]] = []
        for folder_name in SENT_FOLDER_NAMES:
            sent = db.search_emails(
                folder=folder_name,
                date_from=date_from.isoformat() if date_from else None,
                date_to=date_to.isoformat() if date_to else None,
                limit=limit,
            )
            sent_emails.extend(sent)

        seen_ids: set[str] = set()
        unique_sent: list[dict[str, Any]] = []
        for e in sent_emails:
            msg_id = e.get("message_id", "")
            if msg_id and msg_id not in seen_ids:
                unique_sent.append(e)
                seen_ids.add(msg_id)

        if unique_sent:
            reply_info = match_sent_emails_to_received(unique_sent, emails)

    overall = generate_overall_summary(llm_client, all_summaries)

    report = format_summary_report(
        recipient=recipient,
        date_from=date_from,
        date_to=date_to,
        sender_summaries=sender_summaries,
        overall=overall,
        reply_info=reply_info,
    )

    # Step 6: Save to file if path provided
    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)

    return report
