"""Email summary report functionality.

Provides email grouping by sender and individual email summarization
using LLM for structured summary extraction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import groupby
from typing import Any


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
