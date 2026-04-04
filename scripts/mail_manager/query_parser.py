"""Natural language query parser for email search."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from .date_parser import DateRange, extract_date_from_query


@dataclass
class ParsedQuery:
    """Represents a parsed natural language query."""

    original_query: str
    date_range: DateRange | None
    sender: str | None
    keywords: str


def extract_sender_from_query(query: str) -> tuple[str | None, str]:
    """
    Extract sender pattern from a query string.

    Extracts sender patterns like "X发的", "来自X", "from X" and returns
    the sender and the remaining query text.

    Args:
        query: Query string potentially containing sender pattern

    Returns:
        Tuple of (sender | None, remaining_query)
    """
    if not query or not query.strip():
        return None, ""

    query = query.strip()

    # Pattern: "X发的" or "X发来的" at the beginning
    match = re.match(r"^(.+?)(发的|发来的)", query)
    if match:
        sender = match.group(1).strip()
        remaining = query[match.end() :]
        remaining = re.sub(r"^的+", "", remaining)
        return sender, remaining.strip()

    # Pattern: "来自X" or "来自X的" anywhere
    match = re.search(r"来自(.+?)(?:的|$)", query)
    if match:
        sender = match.group(1).strip()
        # Remove the "来自X的" or "来自X" part
        remaining = query[: match.start()] + query[match.end() :]
        remaining = remaining.strip()
        return sender, remaining

    # Pattern: "from X" (English, case insensitive)
    match = re.search(r"\bfrom\s+(\S+)", query, re.IGNORECASE)
    if match:
        sender = match.group(1).strip()
        remaining = query[: match.start()] + query[match.end() :]
        return sender, remaining.strip()

    return None, query


def clean_keywords(text: str) -> str:
    """
    Clean keyword text by removing stop words.

    Args:
        text: Text to clean

    Returns:
        Cleaned text with stop words removed
    """
    if not text or not text.strip():
        return ""

    text = text.strip()

    # Remove common stop words
    stop_words = ["的", "邮件", "所有", "全部", "相关", "收到", "收到"]
    for word in stop_words:
        text = text.replace(word, "")

    return text.strip()


def parse_natural_query(query: str, reference_date: date | None = None) -> ParsedQuery:
    """
    Parse a natural language query into structured components.

    Pipeline:
    1. Extract date expression
    2. Extract sender from remaining text
    3. Clean keywords from final remaining text

    Args:
        query: Natural language query string
        reference_date: Reference date for date calculations (defaults to today)

    Returns:
        ParsedQuery with date_range, sender, and keywords
    """
    if not query or not query.strip():
        return ParsedQuery(
            original_query=query or "",
            date_range=None,
            sender=None,
            keywords="",
        )

    original = query.strip()

    # Step 1: Extract date expression
    date_range, remaining = extract_date_from_query(original, reference_date)

    # Step 2: Extract sender from remaining text
    sender, remaining = extract_sender_from_query(remaining)

    # Step 3: Clean keywords
    keywords = clean_keywords(remaining)

    return ParsedQuery(
        original_query=original,
        date_range=date_range,
        sender=sender,
        keywords=keywords,
    )


def _parse_sender_field(sender: str) -> tuple[str, str]:
    """
    Parse a sender field into name and email.

    Handles formats like "Name <email@domain.com>" or just "email@domain.com"
    or just "Name".

    Args:
        sender: Sender string from email header

    Returns:
        Tuple of (name, email) - either may be empty string
    """
    sender = sender.strip()

    # Pattern: "Name <email@domain.com>"
    match = re.match(r"^(.+?)\s*<(.+?)>$", sender)
    if match:
        return match.group(1).strip(), match.group(2).strip()

    # Check if it looks like an email
    if "@" in sender and not sender.startswith("<"):
        return "", sender

    # Just a name
    return sender, ""


def match_senders(query_sender: str, sender_list: list[str]) -> list[str]:
    """
    Match a sender pattern against a list of sender strings.

    Matches by checking if query_sender is a substring of either
    the name or email portion of each sender (case-insensitive).

    Args:
        query_sender: Sender pattern extracted from query
        sender_list: List of sender strings from database

    Returns:
        List of matching sender strings from sender_list
    """
    if not query_sender or not sender_list:
        return []

    query_lower = query_sender.lower()
    matches = []

    for sender in sender_list:
        name, email = _parse_sender_field(sender)

        # Check if query matches name (case-insensitive)
        if name and query_lower in name.lower():
            matches.append(sender)
            continue

        # Check if query matches email (case-insensitive)
        if email and query_lower in email.lower():
            matches.append(sender)
            continue

        # If no structured format, check against whole string
        if query_lower in sender.lower():
            matches.append(sender)

    return matches
