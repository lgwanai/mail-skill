"""Tests for query_parser module."""
import pytest
from scripts.mail_manager.query_parser import (
    ParsedQuery,
    parse_natural_query,
    match_senders,
    extract_sender_from_query,
    clean_keywords,
)


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


class TestExtractSenderFromQuery:
    """Tests for extract_sender_from_query function."""

    def test_extract_sender_x发的(self):
        """Test extracting sender from 'X发的' pattern."""
        sender, remaining = extract_sender_from_query("王总发的邮件")
        assert sender == "王总"
        assert remaining == "邮件"

    def test_extract_sender_来自(self):
        """Test extracting sender from '来自X' pattern."""
        sender, remaining = extract_sender_from_query("来自gmail.com的邮件")
        assert sender == "gmail.com"
        assert remaining == "邮件"

    def test_extract_sender_no_match(self):
        """Test query with no sender pattern returns None."""
        sender, remaining = extract_sender_from_query("预算讨论")
        assert sender is None
        assert remaining == "预算讨论"

    def test_extract_sender_empty_query(self):
        """Test empty query returns None."""
        sender, remaining = extract_sender_from_query("")
        assert sender is None
        assert remaining == ""

    def test_extract_sender_x发来的(self):
        """Test extracting sender from 'X发来的' pattern."""
        sender, remaining = extract_sender_from_query("张三发来的报告")
        assert sender == "张三"
        assert remaining == "报告"

    def test_extract_sender_from_english(self):
        """Test extracting sender from 'from X' English pattern."""
        sender, remaining = extract_sender_from_query("from john@example.com")
        assert sender == "john@example.com"
        assert remaining == ""

    def test_extract_sender_case_insensitive_english(self):
        """Test English 'from' pattern is case insensitive."""
        sender, remaining = extract_sender_from_query("From boss about project")
        assert sender == "boss"
        assert remaining == "about project"


class TestCleanKeywords:
    """Tests for clean_keywords function."""

    def test_clean_stop_words(self):
        """Test removing common stop words."""
        result = clean_keywords("的邮件")
        assert result == ""

    def test_clean_preserves_content(self):
        """Test that actual content is preserved."""
        result = clean_keywords("预算讨论")
        assert result == "预算讨论"

    def test_clean_strips_whitespace(self):
        """Test that whitespace is stripped."""
        result = clean_keywords("  预算  ")
        assert result == "预算"

    def test_clean_all_stop_words(self):
        """Test query with only stop words returns empty."""
        result = clean_keywords("所有邮件")
        assert result == ""


class TestParseNaturalQuery:
    """Tests for parse_natural_query function."""

    def test_parse_combined_query(self):
        """Test parsing query with date, sender, and keywords."""
        from datetime import date
        from scripts.mail_manager.date_parser import DateRange

        parsed = parse_natural_query("上周王总发的预算邮件")
        assert parsed.original_query == "上周王总发的预算邮件"
        assert parsed.date_range is not None
        assert parsed.sender == "王总"
        assert "预算" in parsed.keywords

    def test_parse_date_only(self):
        """Test parsing query with only date expression."""
        parsed = parse_natural_query("昨天收到的邮件")
        assert parsed.date_range is not None
        assert parsed.sender is None
        assert parsed.keywords == ""

    def test_parse_keywords_only(self):
        """Test parsing query with only keywords."""
        parsed = parse_natural_query("预算讨论")
        assert parsed.date_range is None
        assert parsed.sender is None
        assert parsed.keywords == "预算讨论"

    def test_parse_sender_only(self):
        """Test parsing query with only sender."""
        parsed = parse_natural_query("王总发的")
        assert parsed.date_range is None
        assert parsed.sender == "王总"
        assert parsed.keywords == ""

    def test_parse_empty_query(self):
        """Test parsing empty query."""
        parsed = parse_natural_query("")
        assert parsed.date_range is None
        assert parsed.sender is None
        assert parsed.keywords == ""

    def test_parse_performance(self):
        """Test parsing completes quickly."""
        import time

        start = time.time()
        for _ in range(100):
            parse_natural_query("上周王总发的预算邮件")
        elapsed = time.time() - start
        # 100 iterations should complete in under 10 seconds (100ms each)
        assert elapsed < 10.0


class TestMatchSenders:
    """Tests for match_senders function."""

    def test_match_by_name(self):
        """Test matching sender by name substring."""
        sender_list = ["王总 <wangzong@example.com>", "张三 <zhang@example.com>"]
        matches = match_senders("王总", sender_list)
        assert matches == ["王总 <wangzong@example.com>"]

    def test_match_by_email(self):
        """Test matching sender by email substring."""
        sender_list = ["王某某 <wang@example.com>"]
        matches = match_senders("wang", sender_list)
        assert matches == ["王某某 <wang@example.com>"]

    def test_match_no_match(self):
        """Test that no match returns empty list."""
        sender_list = ["王某某 <wang@example.com>", "张三 <zhang@example.com>"]
        matches = match_senders("unknown", sender_list)
        assert matches == []

    def test_match_empty_params(self):
        """Test that empty parameters return empty list."""
        assert match_senders("", ["test@example.com"]) == []
        assert match_senders("test", []) == []
        assert match_senders("", []) == []

    def test_match_multiple(self):
        """Test matching multiple senders."""
        sender_list = [
            "王小明 <xiaoming@example.com>",
            "王小红 <xiaohong@example.com>",
            "张三 <zhang@example.com>",
        ]
        matches = match_senders("王", sender_list)
        assert len(matches) == 2

    def test_match_case_insensitive(self):
        """Test that matching is case insensitive."""
        sender_list = ["Test User <test@example.com>"]
        matches = match_senders("TEST", sender_list)
        assert matches == ["Test User <test@example.com>"]

    def test_match_only_email_format(self):
        """Test matching when sender is only email."""
        sender_list = ["test@example.com"]
        matches = match_senders("test", sender_list)
        assert matches == ["test@example.com"]

    def test_match_only_name_format(self):
        """Test matching when sender is only name."""
        sender_list = ["张三"]
        matches = match_senders("张", sender_list)
        assert matches == ["张三"]

    def test_match_fallback_no_structure(self):
        """Test fallback match when sender has no name/email structure."""
        sender_list = ["just-a-string"]
        matches = match_senders("just", sender_list)
        assert matches == ["just-a-string"]
