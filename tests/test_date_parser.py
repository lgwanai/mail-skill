"""Tests for date_parser module."""
import pytest
from scripts.mail_manager.date_parser import DateRange, parse_date_expression, extract_date_from_query


class TestDateRange:
    """Tests for DateRange dataclass."""

    def test_date_range_is_dataclass(self):
        """DateRange should be a dataclass with date_from and date_to."""
        from dataclasses import fields
        field_names = [f.name for f in fields(DateRange)]
        assert "date_from" in field_names
        assert "date_to" in field_names


class TestParseDateExpression:
    """Tests for parse_date_expression function. To be expanded in Plan 03-01."""

    @pytest.mark.skip(reason="Implementation in Plan 03-01")
    def test_parse_yesterday(self):
        """Test parsing '昨天'."""
        pass

    @pytest.mark.skip(reason="Implementation in Plan 03-01")
    def test_parse_last_week(self):
        """Test parsing '上周'."""
        pass


class TestExtractDateFromQuery:
    """Tests for extract_date_from_query function. To be expanded in Plan 03-01."""

    @pytest.mark.skip(reason="Implementation in Plan 03-01")
    def test_extract_from_beginning(self):
        """Test extracting date from beginning of query."""
        pass
