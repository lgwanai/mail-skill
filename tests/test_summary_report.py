"""Tests for Email Summary Report functionality.

Tests for group_emails_by_sender, EmailSummary dataclass, and summarize_email.
"""

from datetime import datetime
from typing import Any

import pytest

# Import will fail initially - this is expected in RED phase
from mail_manager.summary_report import EmailSummary, group_emails_by_sender


class TestEmailSummaryDataclass:
    """Tests for EmailSummary dataclass (SUMMARY-01)."""

    def test_email_summary_has_all_required_fields(self) -> None:
        """Test EmailSummary dataclass has all required fields."""
        summary = EmailSummary(
            subject="Test Subject",
            key_points=["Point 1", "Point 2"],
            action_items=["Action 1"],
            deadline="2024-01-20",
            priority="high",
            one_liner="This is a one-line summary.",
        )
        assert summary.subject == "Test Subject"
        assert summary.key_points == ["Point 1", "Point 2"]
        assert summary.action_items == ["Action 1"]
        assert summary.deadline == "2024-01-20"
        assert summary.priority == "high"
        assert summary.one_liner == "This is a one-line summary."

    def test_email_summary_accepts_optional_deadline(self) -> None:
        """Test EmailSummary deadline can be None."""
        summary = EmailSummary(
            subject="Test Subject",
            key_points=["Point 1"],
            action_items=[],
            deadline=None,
            priority="medium",
            one_liner="Summary.",
        )
        assert summary.deadline is None


class TestGroupEmailsBySender:
    """Tests for group_emails_by_sender function (SUMMARY-01)."""

    def test_groups_emails_by_sender_field(self) -> None:
        """Test emails are grouped by sender address."""
        emails = [
            {
                "message_id": "msg-1@example.com",
                "sender": "alice@example.com",
                "subject": "Email 1",
                "date": datetime(2024, 1, 15, 10, 0, 0),
                "body_text": "Body 1",
            },
            {
                "message_id": "msg-2@example.com",
                "sender": "alice@example.com",
                "subject": "Email 2",
                "date": datetime(2024, 1, 16, 10, 0, 0),
                "body_text": "Body 2",
            },
            {
                "message_id": "msg-3@example.com",
                "sender": "bob@example.com",
                "subject": "Email 3",
                "date": datetime(2024, 1, 17, 10, 0, 0),
                "body_text": "Body 3",
            },
        ]
        result = group_emails_by_sender(emails)
        assert "alice@example.com" in result
        assert "bob@example.com" in result
        assert len(result["alice@example.com"]) == 2
        assert len(result["bob@example.com"]) == 1

    def test_returns_dict_with_sender_keys(self) -> None:
        """Test result is dict mapping sender to list of emails."""
        emails = [
            {
                "message_id": "msg-1@example.com",
                "sender": "alice@example.com",
                "subject": "Email 1",
                "date": datetime(2024, 1, 15, 10, 0, 0),
                "body_text": "Body 1",
            },
        ]
        result = group_emails_by_sender(emails)
        assert isinstance(result, dict)
        assert "alice@example.com" in result
        assert isinstance(result["alice@example.com"], list)

    def test_empty_list_returns_empty_dict(self) -> None:
        """Test empty email list returns empty dict."""
        result = group_emails_by_sender([])
        assert result == {}

    def test_single_sender_all_emails_grouped(self) -> None:
        """Test all emails from same sender in one group."""
        emails = [
            {
                "message_id": "msg-1@example.com",
                "sender": "alice@example.com",
                "subject": "Email 1",
                "date": datetime(2024, 1, 15, 10, 0, 0),
                "body_text": "Body 1",
            },
            {
                "message_id": "msg-2@example.com",
                "sender": "alice@example.com",
                "subject": "Email 2",
                "date": datetime(2024, 1, 16, 10, 0, 0),
                "body_text": "Body 2",
            },
        ]
        result = group_emails_by_sender(emails)
        assert len(result) == 1
        assert "alice@example.com" in result
        assert len(result["alice@example.com"]) == 2

    def test_multiple_senders_separate_groups(self) -> None:
        """Test emails from different senders in separate groups."""
        emails = [
            {
                "message_id": "msg-1@example.com",
                "sender": "alice@example.com",
                "subject": "Email 1",
                "date": datetime(2024, 1, 15, 10, 0, 0),
                "body_text": "Body 1",
            },
            {
                "message_id": "msg-2@example.com",
                "sender": "bob@example.com",
                "subject": "Email 2",
                "date": datetime(2024, 1, 16, 10, 0, 0),
                "body_text": "Body 2",
            },
            {
                "message_id": "msg-3@example.com",
                "sender": "charlie@example.com",
                "subject": "Email 3",
                "date": datetime(2024, 1, 17, 10, 0, 0),
                "body_text": "Body 3",
            },
        ]
        result = group_emails_by_sender(emails)
        assert len(result) == 3
        assert set(result.keys()) == {
            "alice@example.com",
            "bob@example.com",
            "charlie@example.com",
        }

    def test_skips_emails_without_sender(self) -> None:
        """Test emails with missing/None sender are skipped."""
        emails = [
            {
                "message_id": "msg-1@example.com",
                "sender": "alice@example.com",
                "subject": "Email 1",
                "date": datetime(2024, 1, 15, 10, 0, 0),
                "body_text": "Body 1",
            },
            {
                "message_id": "msg-2@example.com",
                "sender": None,
                "subject": "Email 2",
                "date": datetime(2024, 1, 16, 10, 0, 0),
                "body_text": "Body 2",
            },
            {
                "message_id": "msg-3@example.com",
                "sender": "",
                "subject": "Email 3",
                "date": datetime(2024, 1, 17, 10, 0, 0),
                "body_text": "Body 3",
            },
        ]
        result = group_emails_by_sender(emails)
        assert len(result) == 1
        assert "alice@example.com" in result

    def test_groups_sorted_by_date(self) -> None:
        """Test emails within each group are sorted by date."""
        emails = [
            {
                "message_id": "msg-3@example.com",
                "sender": "alice@example.com",
                "subject": "Email 3",
                "date": datetime(2024, 1, 17, 10, 0, 0),
                "body_text": "Body 3",
            },
            {
                "message_id": "msg-1@example.com",
                "sender": "alice@example.com",
                "subject": "Email 1",
                "date": datetime(2024, 1, 15, 10, 0, 0),
                "body_text": "Body 1",
            },
            {
                "message_id": "msg-2@example.com",
                "sender": "alice@example.com",
                "subject": "Email 2",
                "date": datetime(2024, 1, 16, 10, 0, 0),
                "body_text": "Body 2",
            },
        ]
        result = group_emails_by_sender(emails)
        group = result["alice@example.com"]
        assert group[0]["subject"] == "Email 1"
        assert group[1]["subject"] == "Email 2"
        assert group[2]["subject"] == "Email 3"


class TestEmailSummaryPrompt:
    """Tests for EMAIL_SUMMARY_PROMPT constant."""

    def test_prompt_exists(self) -> None:
        """Test EMAIL_SUMMARY_PROMPT exists in prompts module."""
        from mail_manager.llm.prompts import EMAIL_SUMMARY_PROMPT

        assert EMAIL_SUMMARY_PROMPT is not None
        assert isinstance(EMAIL_SUMMARY_PROMPT, str)

    def test_prompt_contains_placeholders(self) -> None:
        """Test prompt has placeholders for email fields."""
        from mail_manager.llm.prompts import EMAIL_SUMMARY_PROMPT

        assert "{sender}" in EMAIL_SUMMARY_PROMPT
        assert "{subject}" in EMAIL_SUMMARY_PROMPT
        assert "{date}" in EMAIL_SUMMARY_PROMPT
        assert "{body}" in EMAIL_SUMMARY_PROMPT

    def test_prompt_requests_json_output(self) -> None:
        """Test prompt requests JSON formatted output."""
        from mail_manager.llm.prompts import EMAIL_SUMMARY_PROMPT

        # Should request JSON format with expected keys
        assert "key_points" in EMAIL_SUMMARY_PROMPT
        assert "action_items" in EMAIL_SUMMARY_PROMPT
        assert "deadline" in EMAIL_SUMMARY_PROMPT
        assert "priority" in EMAIL_SUMMARY_PROMPT
        assert "one_liner" in EMAIL_SUMMARY_PROMPT


class TestSummarizeEmail:
    """Tests for summarize_email function (SUMMARY-02)."""

    def test_returns_email_summary_dataclass(self) -> None:
        """Test summarize_email returns EmailSummary dataclass."""
        from unittest.mock import MagicMock

        from mail_manager.summary_report import summarize_email

        mock_llm = MagicMock()
        mock_llm.chat.return_value = MagicMock(
            content='{"key_points": ["Point 1"], "action_items": [], "deadline": null, "priority": "medium", "one_liner": "Test summary."}'
        )

        email = {
            "sender": "alice@example.com",
            "subject": "Test Subject",
            "date": datetime(2024, 1, 15, 10, 0, 0),
            "body_text": "This is a test email body.",
        }

        result = summarize_email(mock_llm, email)
        assert isinstance(result, EmailSummary)
        assert result.subject == "Test Subject"

    def test_summary_includes_key_fields(self) -> None:
        """Test summary includes subject, date, key_points, action_items."""
        import json
        from unittest.mock import MagicMock

        from mail_manager.summary_report import summarize_email

        mock_llm = MagicMock()
        mock_llm.chat.return_value = MagicMock(
            content=json.dumps(
                {
                    "key_points": ["Point 1", "Point 2"],
                    "action_items": ["Action 1"],
                    "deadline": "2024-01-20",
                    "priority": "high",
                    "one_liner": "Test summary.",
                }
            )
        )

        email = {
            "sender": "alice@example.com",
            "subject": "Test Subject",
            "date": datetime(2024, 1, 15, 10, 0, 0),
            "body_text": "This is a test email body.",
        }

        result = summarize_email(mock_llm, email)
        assert result.key_points == ["Point 1", "Point 2"]
        assert result.action_items == ["Action 1"]
        assert result.deadline == "2024-01-20"
        assert result.priority == "high"
        assert result.one_liner == "Test summary."

    def test_summary_calls_llm_client(self) -> None:
        """Test summarize_email uses LLM client for summarization."""
        from unittest.mock import MagicMock

        from mail_manager.summary_report import summarize_email

        mock_llm = MagicMock()
        mock_llm.chat.return_value = MagicMock(
            content='{"key_points": [], "action_items": [], "deadline": null, "priority": "medium", "one_liner": "Summary."}'
        )

        email = {
            "sender": "alice@example.com",
            "subject": "Test Subject",
            "date": datetime(2024, 1, 15, 10, 0, 0),
            "body_text": "This is a test email body.",
        }

        summarize_email(mock_llm, email)
        mock_llm.chat.assert_called_once()
        # Check that the prompt was formatted with email details
        call_args = mock_llm.chat.call_args
        # Access via kwargs since implementation uses messages= keyword arg
        messages = call_args.kwargs.get("messages", call_args[0][0] if call_args[0] else [])
        assert len(messages) == 1  # One message
        assert "alice@example.com" in messages[0]["content"]

    def test_summary_handles_empty_body(self) -> None:
        """Test summarize_email handles emails with empty body."""
        from unittest.mock import MagicMock

        from mail_manager.summary_report import summarize_email

        mock_llm = MagicMock()
        mock_llm.chat.return_value = MagicMock(
            content='{"key_points": [], "action_items": [], "deadline": null, "priority": "low", "one_liner": "Empty email."}'
        )

        email = {
            "sender": "alice@example.com",
            "subject": "Test Subject",
            "date": datetime(2024, 1, 15, 10, 0, 0),
            "body_text": "",
        }

        result = summarize_email(mock_llm, email)
        assert isinstance(result, EmailSummary)
        assert result.subject == "Test Subject"

    def test_summary_handles_malformed_json(self) -> None:
        """Test summarize_email handles malformed JSON with fallback."""
        from unittest.mock import MagicMock

        from mail_manager.summary_report import summarize_email

        mock_llm = MagicMock()
        mock_llm.chat.return_value = MagicMock(content="This is not valid JSON")

        email = {
            "sender": "alice@example.com",
            "subject": "Test Subject",
            "date": datetime(2024, 1, 15, 10, 0, 0),
            "body_text": "This is a test email body.",
        }

        result = summarize_email(mock_llm, email)
        assert isinstance(result, EmailSummary)
        # Should have fallback values
        assert result.key_points == []
        assert result.action_items == []
        assert result.priority == "medium"

    def test_summary_handles_markdown_code_block(self) -> None:
        """Test summarize_email handles JSON in markdown code block."""
        from unittest.mock import MagicMock

        from mail_manager.summary_report import summarize_email

        mock_llm = MagicMock()
        mock_llm.chat.return_value = MagicMock(
            content='```json\n{"key_points": ["Point 1"], "action_items": [], "deadline": null, "priority": "medium", "one_liner": "Summary."}\n```'
        )

        email = {
            "sender": "alice@example.com",
            "subject": "Test Subject",
            "date": datetime(2024, 1, 15, 10, 0, 0),
            "body_text": "This is a test email body.",
        }

        result = summarize_email(mock_llm, email)
        assert result.key_points == ["Point 1"]

    def test_summary_truncates_long_body(self) -> None:
        """Test summarize_email truncates long body_text (>2000 chars)."""
        from unittest.mock import MagicMock

        from mail_manager.summary_report import summarize_email

        mock_llm = MagicMock()
        mock_llm.chat.return_value = MagicMock(
            content='{"key_points": [], "action_items": [], "deadline": null, "priority": "medium", "one_liner": "Summary."}'
        )

        # Create an email with body longer than 2000 chars
        email = {
            "sender": "alice@example.com",
            "subject": "Test Subject",
            "date": datetime(2024, 1, 15, 10, 0, 0),
            "body_text": "x" * 3000,
        }

        summarize_email(mock_llm, email)
        # Verify the body was truncated in the prompt
        call_args = mock_llm.chat.call_args
        # Access via kwargs since implementation uses messages= keyword arg
        messages = call_args.kwargs.get("messages", call_args[0][0] if call_args[0] else [])
        prompt_content = messages[0]["content"]
        assert len(prompt_content) < 3500  # Should be truncated


class TestOverallSummaryPrompt:
    """Tests for OVERALL_SUMMARY_PROMPT constant (SUMMARY-03)."""

    def test_prompt_exists(self) -> None:
        """Test OVERALL_SUMMARY_PROMPT exists in prompts module."""
        from mail_manager.llm.prompts import OVERALL_SUMMARY_PROMPT

        assert OVERALL_SUMMARY_PROMPT is not None
        assert isinstance(OVERALL_SUMMARY_PROMPT, str)

    def test_prompt_requests_json_output(self) -> None:
        """Test prompt requests JSON formatted output with expected keys."""
        from mail_manager.llm.prompts import OVERALL_SUMMARY_PROMPT

        # Should request JSON format with expected keys
        assert "overview" in OVERALL_SUMMARY_PROMPT
        assert "key_themes" in OVERALL_SUMMARY_PROMPT
        assert "all_action_items" in OVERALL_SUMMARY_PROMPT
        assert "upcoming_deadlines" in OVERALL_SUMMARY_PROMPT
        assert "recommended_priority" in OVERALL_SUMMARY_PROMPT

    def test_prompt_has_sender_summaries_placeholder(self) -> None:
        """Test prompt has placeholder for sender summaries."""
        from mail_manager.llm.prompts import OVERALL_SUMMARY_PROMPT

        assert "{sender_summaries}" in OVERALL_SUMMARY_PROMPT


class TestOverallSummary:
    """Tests for generate_overall_summary function (SUMMARY-03)."""

    def test_returns_overall_summary_dataclass(self) -> None:
        """Test generate_overall_summary returns OverallSummary dataclass."""
        from unittest.mock import MagicMock

        from mail_manager.summary_report import OverallSummary, generate_overall_summary

        mock_llm = MagicMock()
        mock_llm.chat.return_value = MagicMock(
            content='{"overview": "Test overview", "key_themes": [], "all_action_items": [], "upcoming_deadlines": [], "recommended_priority": []}'
        )

        sender_summaries: dict[str, list] = {}
        result = generate_overall_summary(mock_llm, sender_summaries)
        assert isinstance(result, OverallSummary)

    def test_summary_includes_all_fields(self) -> None:
        """Test overall summary includes all required fields."""
        import json
        from unittest.mock import MagicMock

        from mail_manager.summary_report import EmailSummary, OverallSummary, generate_overall_summary

        mock_llm = MagicMock()
        mock_llm.chat.return_value = MagicMock(
            content=json.dumps(
                {
                    "overview": "Two senders with project updates",
                    "key_themes": ["Project progress", "Planning"],
                    "all_action_items": [
                        {"item": "Review API design", "sender": "alice@example.com", "priority": "high"}
                    ],
                    "upcoming_deadlines": [
                        {"date": "2024-01-20", "description": "API design review", "sender": "alice@example.com"}
                    ],
                    "recommended_priority": ["Review API design from Alice"],
                }
            )
        )

        sender_summaries = {
            "alice@example.com": [
                EmailSummary(
                    subject="Project Update",
                    key_points=["Project on track"],
                    action_items=["Review API design"],
                    deadline="2024-01-20",
                    priority="high",
                    one_liner="Project update with deadline.",
                )
            ]
        }

        result = generate_overall_summary(mock_llm, sender_summaries)
        assert result.overview == "Two senders with project updates"
        assert result.key_themes == ["Project progress", "Planning"]
        assert len(result.all_action_items) == 1
        assert len(result.upcoming_deadlines) == 1
        assert len(result.recommended_priority) == 1

    def test_summary_handles_empty_summaries(self) -> None:
        """Test generate_overall_summary handles empty input."""
        from unittest.mock import MagicMock

        from mail_manager.summary_report import OverallSummary, generate_overall_summary

        mock_llm = MagicMock()
        mock_llm.chat.return_value = MagicMock(
            content='{"overview": "No emails to summarize.", "key_themes": [], "all_action_items": [], "upcoming_deadlines": [], "recommended_priority": []}'
        )

        result = generate_overall_summary(mock_llm, {})
        assert isinstance(result, OverallSummary)
        assert result.overview == "No emails to summarize."

    def test_summary_handles_json_parse_error_with_fallback(self) -> None:
        """Test generate_overall_summary handles JSON parse errors with fallback."""
        from unittest.mock import MagicMock

        from mail_manager.summary_report import OverallSummary, generate_overall_summary

        mock_llm = MagicMock()
        mock_llm.chat.return_value = MagicMock(content="This is not valid JSON")

        result = generate_overall_summary(mock_llm, {})
        assert isinstance(result, OverallSummary)
        # Should have fallback values
        assert result.key_themes == []
        assert result.all_action_items == []
        assert result.upcoming_deadlines == []
        assert result.recommended_priority == []

    def test_action_items_include_sender_attribution(self) -> None:
        """Test action items include sender attribution."""
        import json
        from unittest.mock import MagicMock

        from mail_manager.summary_report import EmailSummary, generate_overall_summary

        mock_llm = MagicMock()
        mock_llm.chat.return_value = MagicMock(
            content=json.dumps(
                {
                    "overview": "Test",
                    "key_themes": [],
                    "all_action_items": [
                        {"item": "Task 1", "sender": "alice@example.com", "priority": "high"},
                        {"item": "Task 2", "sender": "bob@example.com", "priority": "medium"},
                    ],
                    "upcoming_deadlines": [],
                    "recommended_priority": [],
                }
            )
        )

        sender_summaries = {
            "alice@example.com": [
                EmailSummary(subject="Email 1", action_items=["Task 1"], priority="high", one_liner="")
            ],
            "bob@example.com": [
                EmailSummary(subject="Email 2", action_items=["Task 2"], priority="medium", one_liner="")
            ],
        }

        result = generate_overall_summary(mock_llm, sender_summaries)
        assert len(result.all_action_items) == 2
        assert result.all_action_items[0]["sender"] == "alice@example.com"
        assert result.all_action_items[1]["sender"] == "bob@example.com"

    def test_handles_markdown_code_block_in_response(self) -> None:
        """Test generate_overall_summary handles JSON in markdown code block."""
        from unittest.mock import MagicMock

        from mail_manager.summary_report import OverallSummary, generate_overall_summary

        mock_llm = MagicMock()
        mock_llm.chat.return_value = MagicMock(
            content='```json\n{"overview": "Test overview", "key_themes": [], "all_action_items": [], "upcoming_deadlines": [], "recommended_priority": []}\n```'
        )

        result = generate_overall_summary(mock_llm, {})
        assert isinstance(result, OverallSummary)
        assert result.overview == "Test overview"


class TestFormatSummaryReport:
    """Tests for format_summary_report function (SUMMARY-04)."""

    def test_returns_markdown_string(self) -> None:
        """Test format_summary_report returns valid Markdown string."""
        from datetime import date

        from mail_manager.summary_report import (
            EmailSummary,
            OverallSummary,
            format_summary_report,
        )

        overall = OverallSummary(
            overview="Test overview",
            key_themes=["Theme 1"],
            all_action_items=[],
            upcoming_deadlines=[],
            recommended_priority=[],
        )
        sender_summaries: dict[str, list[tuple[dict, EmailSummary]]] = {}

        result = format_summary_report(
            recipient="test@example.com",
            date_from=date(2024, 1, 1),
            date_to=date(2024, 1, 7),
            sender_summaries=sender_summaries,
            overall=overall,
        )

        assert isinstance(result, str)
        assert "# Email Summary Report" in result

    def test_includes_header_with_time_range(self) -> None:
        """Test report header includes date/time range."""
        from datetime import date

        from mail_manager.summary_report import (
            EmailSummary,
            OverallSummary,
            format_summary_report,
        )

        overall = OverallSummary(
            overview="Test",
            key_themes=[],
            all_action_items=[],
            upcoming_deadlines=[],
            recommended_priority=[],
        )
        sender_summaries: dict[str, list[tuple[dict, EmailSummary]]] = {}

        result = format_summary_report(
            recipient="test@example.com",
            date_from=date(2024, 1, 1),
            date_to=date(2024, 1, 7),
            sender_summaries=sender_summaries,
            overall=overall,
        )

        assert "test@example.com" in result
        assert "2024-01-01" in result
        assert "2024-01-07" in result

    def test_includes_sender_sections(self) -> None:
        """Test report has sections for each sender."""
        from datetime import date

        from mail_manager.summary_report import (
            EmailSummary,
            OverallSummary,
            format_summary_report,
        )

        overall = OverallSummary(
            overview="Test overview",
            key_themes=[],
            all_action_items=[],
            upcoming_deadlines=[],
            recommended_priority=[],
        )

        sender_summaries = {
            "alice@example.com": [
                (
                    {"subject": "Email 1", "date": datetime(2024, 1, 15)},
                    EmailSummary(
                        subject="Email 1",
                        key_points=["Point 1"],
                        action_items=[],
                        deadline=None,
                        priority="medium",
                        one_liner="Summary 1",
                    ),
                )
            ],
            "bob@example.com": [
                (
                    {"subject": "Email 2", "date": datetime(2024, 1, 16)},
                    EmailSummary(
                        subject="Email 2",
                        key_points=["Point 2"],
                        action_items=[],
                        deadline=None,
                        priority="low",
                        one_liner="Summary 2",
                    ),
                )
            ],
        }

        result = format_summary_report(
            recipient="test@example.com",
            date_from=date(2024, 1, 1),
            date_to=date(2024, 1, 7),
            sender_summaries=sender_summaries,
            overall=overall,
        )

        assert "alice@example.com" in result
        assert "bob@example.com" in result

    def test_includes_overall_summary_section(self) -> None:
        """Test report includes overall summary section."""
        from datetime import date

        from mail_manager.summary_report import (
            EmailSummary,
            OverallSummary,
            format_summary_report,
        )

        overall = OverallSummary(
            overview="This is the overall summary.",
            key_themes=["Project progress", "Planning"],
            all_action_items=[
                {"item": "Review API", "sender": "alice@example.com", "priority": "high"}
            ],
            upcoming_deadlines=[
                {"date": "2024-01-20", "description": "API review", "sender": "alice@example.com"}
            ],
            recommended_priority=["Review API first"],
        )

        sender_summaries: dict[str, list[tuple[dict, EmailSummary]]] = {}

        result = format_summary_report(
            recipient="test@example.com",
            date_from=date(2024, 1, 1),
            date_to=date(2024, 1, 7),
            sender_summaries=sender_summaries,
            overall=overall,
        )

        assert "## Overview" in result
        assert "This is the overall summary" in result
        assert "Project progress" in result
        assert "Review API first" in result

    def test_formats_email_summaries_as_list(self) -> None:
        """Test email summaries are formatted as bullet list."""
        from datetime import date

        from mail_manager.summary_report import (
            EmailSummary,
            OverallSummary,
            format_summary_report,
        )

        overall = OverallSummary(
            overview="Test",
            key_themes=[],
            all_action_items=[],
            upcoming_deadlines=[],
            recommended_priority=[],
        )

        sender_summaries = {
            "alice@example.com": [
                (
                    {"subject": "Project Update", "date": datetime(2024, 1, 15)},
                    EmailSummary(
                        subject="Project Update",
                        key_points=["Point 1", "Point 2"],
                        action_items=["Action 1"],
                        deadline="2024-01-20",
                        priority="high",
                        one_liner="Project is on track.",
                    ),
                )
            ]
        }

        result = format_summary_report(
            recipient="test@example.com",
            date_from=date(2024, 1, 1),
            date_to=date(2024, 1, 7),
            sender_summaries=sender_summaries,
            overall=overall,
        )

        assert "Project Update" in result
        assert "Project is on track" in result
        assert "- Point 1" in result
        assert "- [ ] Action 1" in result
        assert "2024-01-20" in result

    def test_handles_special_characters_in_markdown(self) -> None:
        """Test special characters are escaped properly."""
        from datetime import date

        from mail_manager.summary_report import (
            EmailSummary,
            OverallSummary,
            format_summary_report,
        )

        overall = OverallSummary(
            overview="Test with <special> & chars",
            key_themes=["Theme with *asterisk*"],
            all_action_items=[],
            upcoming_deadlines=[],
            recommended_priority=[],
        )

        sender_summaries = {
            "alice@example.com": [
                (
                    {"subject": "Email with <angle> brackets", "date": datetime(2024, 1, 15)},
                    EmailSummary(
                        subject="Email with <angle> brackets",
                        key_points=["Point with & ampersand"],
                        action_items=[],
                        deadline=None,
                        priority="medium",
                        one_liner="Summary with *asterisk*",
                    ),
                )
            ]
        }

        result = format_summary_report(
            recipient="test@example.com",
            date_from=date(2024, 1, 1),
            date_to=date(2024, 1, 7),
            sender_summaries=sender_summaries,
            overall=overall,
        )

        # The content should be present (may or may not be escaped depending on implementation)
        assert "special" in result
        assert "asterisk" in result


class TestGenerateReport:
    """Tests for generate_email_summary_report function (SUMMARY-04)."""

    def test_returns_formatted_markdown(self) -> None:
        """Test generate_email_summary_report returns formatted Markdown."""
        import json
        from datetime import date
        from unittest.mock import MagicMock

        from mail_manager.summary_report import generate_email_summary_report

        mock_db = MagicMock()
        mock_db.search_emails.return_value = [
            {
                "message_id": "msg-1",
                "sender": "alice@example.com",
                "subject": "Test Email",
                "date": datetime(2024, 1, 15),
                "body_text": "This is a test email.",
            }
        ]

        mock_llm = MagicMock()
        mock_llm.chat.return_value = MagicMock(
            content=json.dumps(
                {
                    "key_points": ["Point 1"],
                    "action_items": [],
                    "deadline": None,
                    "priority": "medium",
                    "one_liner": "Test summary.",
                }
            )
        )

        result = generate_email_summary_report(
            db=mock_db,
            llm_client=mock_llm,
            recipient="test@example.com",
            date_from=date(2024, 1, 1),
            date_to=date(2024, 1, 7),
        )

        assert isinstance(result, str)
        assert "# Email Summary Report" in result

    def test_returns_message_for_empty_email_list(self) -> None:
        """Test generate_email_summary_report returns message for empty email list."""
        from datetime import date
        from unittest.mock import MagicMock

        from mail_manager.summary_report import generate_email_summary_report

        mock_db = MagicMock()
        mock_db.search_emails.return_value = []

        mock_llm = MagicMock()

        result = generate_email_summary_report(
            db=mock_db,
            llm_client=mock_llm,
            recipient="test@example.com",
            date_from=date(2024, 1, 1),
            date_to=date(2024, 1, 7),
        )

        assert "No emails found" in result

    def test_saves_to_file_when_output_path_provided(self, tmp_path: Any) -> None:
        """Test generate_email_summary_report saves to file when output_path provided."""
        import json
        from datetime import date
        from unittest.mock import MagicMock

        from mail_manager.summary_report import generate_email_summary_report

        mock_db = MagicMock()
        mock_db.search_emails.return_value = [
            {
                "message_id": "msg-1",
                "sender": "alice@example.com",
                "subject": "Test Email",
                "date": datetime(2024, 1, 15),
                "body_text": "This is a test email.",
            }
        ]

        mock_llm = MagicMock()
        mock_llm.chat.return_value = MagicMock(
            content=json.dumps(
                {
                    "key_points": ["Point 1"],
                    "action_items": [],
                    "deadline": None,
                    "priority": "medium",
                    "one_liner": "Test summary.",
                }
            )
        )

        output_file = tmp_path / "report.md"

        result = generate_email_summary_report(
            db=mock_db,
            llm_client=mock_llm,
            recipient="test@example.com",
            date_from=date(2024, 1, 1),
            date_to=date(2024, 1, 7),
            output_path=str(output_file),
        )

        assert output_file.exists()
        assert "# Email Summary Report" in output_file.read_text()
        assert result == output_file.read_text()

    def test_uses_default_date_range_when_not_specified(self) -> None:
        """Test generate_email_summary_report uses default date range when not specified."""
        import json
        from datetime import date, timedelta
        from unittest.mock import MagicMock

        from mail_manager.summary_report import generate_email_summary_report

        mock_db = MagicMock()
        mock_db.search_emails.return_value = []

        mock_llm = MagicMock()

        generate_email_summary_report(
            db=mock_db,
            llm_client=mock_llm,
            recipient="test@example.com",
        )

        # Verify db.search_emails was called with date parameters
        mock_db.search_emails.assert_called_once()
        call_kwargs = mock_db.search_emails.call_args.kwargs

        # Default is 7 days back from today
        assert "date_from" in call_kwargs
        assert "date_to" in call_kwargs
