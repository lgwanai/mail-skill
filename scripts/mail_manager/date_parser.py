"""
Chinese date expression parser for natural language search.

Converts natural language date phrases like "昨天", "上周", "最近3天" to DateRange objects.
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass
class DateRange:
    """Represents a date range with inclusive start and end dates."""

    date_from: date
    date_to: date


def parse_date_expression(query: str, reference_date: date | None = None) -> DateRange | None:
    """
    Parse a Chinese date expression to a DateRange.

    Args:
        query: Chinese date expression (e.g., "昨天", "上周", "最近3天")
        reference_date: Reference date for calculation (defaults to today)

    Returns:
        DateRange if expression is recognized, None otherwise
    """
    if not query or not query.strip():
        return None

    query = query.strip()
    ref = reference_date or date.today()

    # Single day expressions
    if query == "昨天":
        yesterday = ref - timedelta(days=1)
        return DateRange(yesterday, yesterday)

    if query == "前天":
        day_before = ref - timedelta(days=2)
        return DateRange(day_before, day_before)

    if query == "今天":
        return DateRange(ref, ref)

    # Week expressions
    if query == "上周":
        return _get_last_week_range(ref)

    if query == "本周":
        return _get_this_week_range(ref)

    # Relative N days expressions: "最近N天" or "过去N天"
    match = re.match(r"^(最近|过去)(\d+)天$", query)
    if match:
        n = int(match.group(2))
        date_from = ref - timedelta(days=n - 1)
        return DateRange(date_from, ref)

    # Month expressions
    if query == "上个月":
        return _get_last_month_range(ref)

    if query == "本月":
        return _get_this_month_range(ref)

    # Specific date: "N月N日" or "N月N号"
    match = re.match(r"^(\d+)月(\d+)[日号]$", query)
    if match:
        month = int(match.group(1))
        day = int(match.group(2))
        try:
            specific_date = date(ref.year, month, day)
            return DateRange(specific_date, specific_date)
        except ValueError:
            # Invalid date (e.g., Feb 30)
            return None

    return None


def _get_this_week_range(ref: date) -> DateRange:
    """Get this week's date range (Monday to Sunday)."""
    # weekday() returns 0 for Monday, 6 for Sunday
    days_since_monday = ref.weekday()
    monday = ref - timedelta(days=days_since_monday)
    sunday = monday + timedelta(days=6)
    return DateRange(monday, sunday)


def _get_last_week_range(ref: date) -> DateRange:
    """Get last week's date range (Monday to Sunday)."""
    this_week = _get_this_week_range(ref)
    last_monday = this_week.date_from - timedelta(days=7)
    last_sunday = this_week.date_to - timedelta(days=7)
    return DateRange(last_monday, last_sunday)


def _get_this_month_range(ref: date) -> DateRange:
    """Get this month's date range (1st to last day of month)."""
    first_day = date(ref.year, ref.month, 1)
    last_day_num = calendar.monthrange(ref.year, ref.month)[1]
    last_day = date(ref.year, ref.month, last_day_num)
    return DateRange(first_day, last_day)


def _get_last_month_range(ref: date) -> DateRange:
    """Get last month's date range (1st to last day of previous month)."""
    # Calculate first day of this month, then subtract one day
    first_of_this_month = date(ref.year, ref.month, 1)
    last_of_prev_month = first_of_this_month - timedelta(days=1)
    first_of_prev_month = date(last_of_prev_month.year, last_of_prev_month.month, 1)
    return DateRange(first_of_prev_month, last_of_prev_month)


def extract_date_from_query(
    query: str, reference_date: date | None = None
) -> tuple[DateRange | None, str]:
    """
    Extract date expression from a mixed query string.

    Extracts date expressions from the beginning or end of a query,
    returning the date range and the remaining query text.

    Args:
        query: Mixed query string (e.g., "上周的邮件")
        reference_date: Reference date for calculation (defaults to today)

    Returns:
        Tuple of (DateRange | None, remaining_query)
        - remaining_query has the date expression removed and is stripped
        - Returns (None, original_query) if no date expression found
    """
    if not query or not query.strip():
        return None, ""

    query = query.strip()
    ref = reference_date or date.today()

    # Patterns to try at the beginning
    beginning_patterns = [
        # Week/month expressions
        (r"^(上周|本周|上个月|本月)", 1),
        # Relative days: "最近N天" or "过去N天"
        (r"^(最近|过去)\d+天", 0),
        # Single day expressions
        (r"^(昨天|前天|今天)", 1),
        # Specific date: "N月N日" or "N月N号"
        (r"^\d+月\d+[日号]", 0),
    ]

    # Try matching at the beginning
    for pattern, group_idx in beginning_patterns:
        match = re.match(pattern, query)
        if match:
            if group_idx > 0:
                date_expr = match.group(group_idx)
            else:
                date_expr = match.group(0)
            date_range = parse_date_expression(date_expr, ref)
            if date_range:
                remaining = query[match.end() :]
                # Remove leading "的" connector
                remaining = re.sub(r"^的+", "", remaining)
                remaining = remaining.strip()
                return date_range, remaining

    # Try matching at the end
    end_patterns = [
        # Week/month expressions
        (r"(上周|本周|上个月|本月)$", 1),
        # Single day expressions
        (r"(昨天|前天|今天)$", 1),
        # Specific date: "N月N日" or "N月N号"
        (r"\d+月\d+[日号]$", 0),
        # Relative days at end (less common but possible)
        (r"(最近|过去)\d+天$", 0),
    ]

    for pattern, group_idx in end_patterns:
        match = re.search(pattern, query)
        if match:
            if group_idx > 0:
                date_expr = match.group(group_idx)
            else:
                date_expr = match.group(0)
            date_range = parse_date_expression(date_expr, ref)
            if date_range:
                remaining = query[: match.start()]
                remaining = remaining.strip()
                # Remove trailing "的" connector
                remaining = re.sub(r"的+$", "", remaining)
                remaining = remaining.strip()
                return date_range, remaining

    return None, query
