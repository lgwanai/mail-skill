"""Tests for query_parser module."""
import pytest
from scripts.mail_manager.query_parser import ParsedQuery, parse_natural_query, match_senders


class TestParsedQuery:
    """Tests for ParsedQuery dataclass."""

    def test_parsed_query_is_dataclass(self):
        """ParsedQuery should be a dataclass with expected fields."""
        from dataclasses import fields
        field_names = [f.name for f in fields(ParsedQuery)]
        assert "original_query" in field_names
        assert "date_range" in field_names
        assert "sender" in field_names
        assert "keywords" in field_names


class TestParseNaturalQuery:
    """Tests for parse_natural_query function. To be expanded in Plan 03-02."""

    @pytest.mark.skip(reason="Implementation in Plan 03-02")
    def test_parse_combined_query(self):
        """Test parsing query with date, sender, and keywords."""
        pass


class TestMatchSenders:
    """Tests for match_senders function. To be expanded in Plan 03-02."""

    @pytest.mark.skip(reason="Implementation in Plan 03-02")
    def test_match_by_name(self):
        """Test matching sender by name substring."""
        pass
