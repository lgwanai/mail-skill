"""
Unit tests for Chinese date expression parser.

Tests the parse_date_expression function and DateRange dataclass
for converting natural language date phrases to date ranges.
"""

from __future__ import annotations

from datetime import date

import pytest

from scripts.mail_manager.date_parser import (
    DateRange,
    extract_date_from_query,
    parse_date_expression,
)


class TestDateRange:
    """Tests for the DateRange dataclass."""

    def test_date_range_is_dataclass(self) -> None:
        """DateRange should be a dataclass with date_from and date_to."""
        from dataclasses import fields

        field_names = [f.name for f in fields(DateRange)]
        assert "date_from" in field_names
        assert "date_to" in field_names

    def test_date_range_creation(self) -> None:
        """DateRange can be created with date_from and date_to."""
        range_obj = DateRange(
            date_from=date(2024, 1, 1),
            date_to=date(2024, 1, 7),
        )
        assert range_obj.date_from == date(2024, 1, 1)
        assert range_obj.date_to == date(2024, 1, 7)

    def test_date_range_equality(self) -> None:
        """DateRange instances with same dates are equal."""
        range1 = DateRange(date(2024, 1, 1), date(2024, 1, 7))
        range2 = DateRange(date(2024, 1, 1), date(2024, 1, 7))
        assert range1 == range2


class TestParseDateExpression:
    """Tests for parse_date_expression function."""

    # Reference date for deterministic testing: Wednesday, Jan 17, 2024
    REFERENCE_DATE = date(2024, 1, 17)

    def test_parse_yesterday(self) -> None:
        """parse_date_expression('昨天') returns DateRange for yesterday."""
        result = parse_date_expression("昨天", self.REFERENCE_DATE)
        assert result is not None
        assert result.date_from == date(2024, 1, 16)
        assert result.date_to == date(2024, 1, 16)

    def test_parse_day_before_yesterday(self) -> None:
        """parse_date_expression('前天') returns DateRange for day before yesterday."""
        result = parse_date_expression("前天", self.REFERENCE_DATE)
        assert result is not None
        assert result.date_from == date(2024, 1, 15)
        assert result.date_to == date(2024, 1, 15)

    def test_parse_today(self) -> None:
        """parse_date_expression('今天') returns DateRange for today."""
        result = parse_date_expression("今天", self.REFERENCE_DATE)
        assert result is not None
        assert result.date_from == date(2024, 1, 17)
        assert result.date_to == date(2024, 1, 17)

    def test_parse_last_week(self) -> None:
        """parse_date_expression('上周') returns DateRange for last week (Mon-Sun)."""
        # Reference: Wed Jan 17, 2024
        # This week: Jan 15 (Mon) - Jan 21 (Sun)
        # Last week: Jan 8 (Mon) - Jan 14 (Sun)
        result = parse_date_expression("上周", self.REFERENCE_DATE)
        assert result is not None
        assert result.date_from == date(2024, 1, 8)
        assert result.date_to == date(2024, 1, 14)

    def test_parse_this_week(self) -> None:
        """parse_date_expression('本周') returns DateRange for this week (Mon-Sun)."""
        # Reference: Wed Jan 17, 2024
        # This week: Jan 15 (Mon) - Jan 21 (Sun)
        result = parse_date_expression("本周", self.REFERENCE_DATE)
        assert result is not None
        assert result.date_from == date(2024, 1, 15)
        assert result.date_to == date(2024, 1, 21)

    def test_parse_last_n_days(self) -> None:
        """parse_date_expression('最近N天') returns DateRange for last N days."""
        # Reference: Jan 17, 2024
        # Last 3 days: Jan 15, 16, 17
        result = parse_date_expression("最近3天", self.REFERENCE_DATE)
        assert result is not None
        assert result.date_from == date(2024, 1, 15)
        assert result.date_to == date(2024, 1, 17)

    def test_parse_past_n_days(self) -> None:
        """parse_date_expression('过去N天') returns DateRange for past N days."""
        # Reference: Jan 17, 2024
        # Past 7 days: Jan 11-17
        result = parse_date_expression("过去7天", self.REFERENCE_DATE)
        assert result is not None
        assert result.date_from == date(2024, 1, 11)
        assert result.date_to == date(2024, 1, 17)

    def test_parse_last_month(self) -> None:
        """parse_date_expression('上个月') returns DateRange for last calendar month."""
        # Reference: Jan 17, 2024
        # Last month: Dec 1-31, 2023
        result = parse_date_expression("上个月", self.REFERENCE_DATE)
        assert result is not None
        assert result.date_from == date(2023, 12, 1)
        assert result.date_to == date(2023, 12, 31)

    def test_parse_this_month(self) -> None:
        """parse_date_expression('本月') returns DateRange for current month."""
        # Reference: Jan 17, 2024
        # This month: Jan 1-31, 2024
        result = parse_date_expression("本月", self.REFERENCE_DATE)
        assert result is not None
        assert result.date_from == date(2024, 1, 1)
        assert result.date_to == date(2024, 1, 31)

    def test_parse_specific_date_with_day(self) -> None:
        """parse_date_expression('N月N日') returns DateRange for specific date."""
        # Reference: Jan 17, 2024
        # 3月15日 -> March 15, 2024
        result = parse_date_expression("3月15日", self.REFERENCE_DATE)
        assert result is not None
        assert result.date_from == date(2024, 3, 15)
        assert result.date_to == date(2024, 3, 15)

    def test_parse_specific_date_with_hao(self) -> None:
        """parse_date_expression('N月N号') returns DateRange for specific date."""
        result = parse_date_expression("5月20号", self.REFERENCE_DATE)
        assert result is not None
        assert result.date_from == date(2024, 5, 20)
        assert result.date_to == date(2024, 5, 20)

    def test_parse_invalid_specific_date(self) -> None:
        """parse_date_expression returns None for invalid specific date (e.g., Feb 30)."""
        result = parse_date_expression("2月30日", self.REFERENCE_DATE)
        assert result is None

    def test_parse_invalid_expression_returns_none(self) -> None:
        """parse_date_expression returns None for unrecognized expressions."""
        result = parse_date_expression("invalid", self.REFERENCE_DATE)
        assert result is None

    def test_parse_empty_string_returns_none(self) -> None:
        """parse_date_expression returns None for empty string."""
        result = parse_date_expression("", self.REFERENCE_DATE)
        assert result is None

    def test_parse_whitespace_returns_none(self) -> None:
        """parse_date_expression returns None for whitespace-only string."""
        result = parse_date_expression("   ", self.REFERENCE_DATE)
        assert result is None


class TestParseDateExpressionEdgeCases:
    """Tests for edge cases in date parsing."""

    def test_last_week_year_boundary(self) -> None:
        """Last week calculation handles year boundary correctly."""
        # Reference: Jan 3, 2024 (Wednesday)
        # This week: Jan 1-7, 2024
        # Last week: Dec 25-31, 2023
        reference = date(2024, 1, 3)
        result = parse_date_expression("上周", reference)
        assert result is not None
        assert result.date_from == date(2023, 12, 25)
        assert result.date_to == date(2023, 12, 31)

    def test_last_month_year_boundary(self) -> None:
        """Last month calculation handles year boundary correctly."""
        # Reference: Jan 17, 2024
        # Last month: Dec 2023
        result = parse_date_expression("上个月", date(2024, 1, 17))
        assert result is not None
        assert result.date_from == date(2023, 12, 1)
        assert result.date_to == date(2023, 12, 31)

    def test_last_month_february_leap_year(self) -> None:
        """Last month handles February in leap year."""
        # Reference: March 15, 2024 (leap year)
        # Last month: Feb 2024 (29 days in leap year)
        result = parse_date_expression("上个月", date(2024, 3, 15))
        assert result is not None
        assert result.date_from == date(2024, 2, 1)
        assert result.date_to == date(2024, 2, 29)

    def test_last_month_february_non_leap_year(self) -> None:
        """Last month handles February in non-leap year."""
        # Reference: March 15, 2023 (non-leap year)
        # Last month: Feb 2023 (28 days)
        result = parse_date_expression("上个月", date(2023, 3, 15))
        assert result is not None
        assert result.date_from == date(2023, 2, 1)
        assert result.date_to == date(2023, 2, 28)

    def test_default_reference_date_is_today(self) -> None:
        """parse_date_expression uses today as default reference date."""
        # Just verify it doesn't raise an error
        result = parse_date_expression("今天")
        assert result is not None
        assert result.date_from == result.date_to
        assert result.date_to == date.today()

    def test_last_n_days_large_number(self) -> None:
        """parse_date_expression handles large N in '最近N天'."""
        result = parse_date_expression("最近30天", date(2024, 1, 17))
        assert result is not None
        assert result.date_from == date(2023, 12, 19)
        assert result.date_to == date(2024, 1, 17)


class TestExtractDateFromQuery:
    """Tests for extract_date_from_query function."""

    REFERENCE_DATE = date(2024, 1, 17)

    def test_extract_from_beginning_with_de(self) -> None:
        """Extract date from beginning with '的' connector."""
        # "上周的邮件" -> DateRange(last_week), "邮件"
        date_range, remaining = extract_date_from_query("上周的邮件", self.REFERENCE_DATE)
        assert date_range is not None
        assert date_range.date_from == date(2024, 1, 8)
        assert date_range.date_to == date(2024, 1, 14)
        assert remaining == "邮件"

    def test_extract_from_beginning_without_connector(self) -> None:
        """Extract date from beginning without connector."""
        # "昨天邮件" -> DateRange(yesterday), "邮件"
        date_range, remaining = extract_date_from_query("昨天邮件", self.REFERENCE_DATE)
        assert date_range is not None
        assert date_range.date_from == date(2024, 1, 16)
        assert date_range.date_to == date(2024, 1, 16)
        assert remaining == "邮件"

    def test_extract_yesterday_from_mixed_query(self) -> None:
        """Extract '昨天' from mixed query."""
        # "昨天收到的预算邮件"
        date_range, remaining = extract_date_from_query("昨天收到的预算邮件", self.REFERENCE_DATE)
        assert date_range is not None
        assert date_range.date_from == date(2024, 1, 16)
        assert remaining == "收到的预算邮件"

    def test_extract_from_end(self) -> None:
        """Extract date from end of query."""
        # "邮件昨天" -> DateRange(yesterday), "邮件"
        date_range, remaining = extract_date_from_query("邮件昨天", self.REFERENCE_DATE)
        assert date_range is not None
        assert date_range.date_from == date(2024, 1, 16)
        assert remaining == "邮件"

    def test_no_date_in_query(self) -> None:
        """Return None when no date expression found."""
        # "预算讨论" -> None, "预算讨论"
        date_range, remaining = extract_date_from_query("预算讨论", self.REFERENCE_DATE)
        assert date_range is None
        assert remaining == "预算讨论"

    def test_extract_with_multiple_de_connectors(self) -> None:
        """Remove multiple '的' connectors after date."""
        date_range, remaining = extract_date_from_query("上周的的邮件", self.REFERENCE_DATE)
        assert date_range is not None
        assert remaining == "邮件"

    def test_extract_from_empty_string(self) -> None:
        """Handle empty string input."""
        date_range, remaining = extract_date_from_query("", self.REFERENCE_DATE)
        assert date_range is None
        assert remaining == ""

    def test_extract_from_whitespace_only(self) -> None:
        """Handle whitespace-only input."""
        date_range, remaining = extract_date_from_query("   ", self.REFERENCE_DATE)
        assert date_range is None
        assert remaining == ""

    def test_extract_specific_date_from_beginning(self) -> None:
        """Extract specific date (N月N日) from beginning."""
        date_range, remaining = extract_date_from_query("3月15日的会议", self.REFERENCE_DATE)
        assert date_range is not None
        assert date_range.date_from == date(2024, 3, 15)
        assert remaining == "会议"

    def test_extract_relative_days_from_beginning(self) -> None:
        """Extract '最近N天' from beginning."""
        date_range, remaining = extract_date_from_query("最近3天的邮件", self.REFERENCE_DATE)
        assert date_range is not None
        assert date_range.date_from == date(2024, 1, 15)
        assert remaining == "邮件"

    def test_extract_from_end_with_specific_date(self) -> None:
        """Extract specific date from end of query."""
        date_range, remaining = extract_date_from_query("会议3月15日", self.REFERENCE_DATE)
        assert date_range is not None
        assert date_range.date_from == date(2024, 3, 15)
        assert remaining == "会议"

    def test_extract_from_end_with_de_connector(self) -> None:
        """Extract date from end with '的' connector before date."""
        # "邮件的上周" -> DateRange(last_week), "邮件"
        date_range, remaining = extract_date_from_query("邮件的上周", self.REFERENCE_DATE)
        assert date_range is not None
        assert date_range.date_from == date(2024, 1, 8)
        assert remaining == "邮件"

    def test_default_reference_date(self) -> None:
        """extract_date_from_query uses today as default reference date."""
        date_range, remaining = extract_date_from_query("今天的邮件")
        assert date_range is not None
        assert date_range.date_from == date.today()
        assert remaining == "邮件"
