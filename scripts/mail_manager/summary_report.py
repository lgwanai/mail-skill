"""Email summary report functionality.

Provides email grouping by sender and individual email summarization
using LLM for structured summary extraction.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from itertools import groupby
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mail_manager.llm.client import LLMClient

from mail_manager.llm.prompts import EMAIL_SUMMARY_PROMPT, OVERALL_SUMMARY_PROMPT


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


def group_emails_by_sender(emails: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group emails by sender address.

    Groups a list of email dictionaries by their sender field, sorting
    each group by date. Emails with missing or empty sender are skipped.

    Args:
        emails: List of email dictionaries with 'sender' and 'date' fields.

    Returns:
        Dict mapping sender email addresses to lists of emails from that sender.
        Each list is sorted by date (ascending).

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

    # Filter out emails with missing or empty sender
    valid_emails = [e for e in emails if e.get("sender")]

    if not valid_emails:
        return {}

    # Sort by sender first (required for groupby), then by date within groups
    sorted_emails = sorted(valid_emails, key=lambda e: (e.get("sender", ""), e.get("date")))

    # Group by sender
    result: dict[str, list[dict[str, Any]]] = {}
    for sender, group in groupby(sorted_emails, key=lambda e: e.get("sender", "")):
        if sender:  # Double-check sender is not empty
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
        sender=sender,
        subject=subject,
        date=str(date),
        body=body_text,
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
        sender_summaries="\n".join(summaries_text),
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
