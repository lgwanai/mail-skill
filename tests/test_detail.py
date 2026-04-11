"""
Unit tests for email detail formatting functions.

Tests cover Markdown output formatting for email detail views including
headers, classification info, attachments with file paths, and thread context.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from mail_manager.detail import (
    format_attachments_detail,
    format_classification,
    format_email_detail,
    format_headers,
    format_thread_context,
)


class TestFormatEmailDetail:
    """Tests for format_email_detail function."""

    def test_format_email_detail_returns_markdown_string(self) -> None:
        """Test that format_email_detail returns a Markdown string with headers."""
        email = {
            "message_id": "test-123@example.com",
            "subject": "Test Subject",
            "sender": "sender@example.com",
            "recipient": "recipient@example.com",
            "cc": "",
            "date": "2024-01-15 10:30:00",
            "body_text": "This is the email body.",
        }

        result = format_email_detail(email)

        assert isinstance(result, str)
        assert "## Test Subject" in result
        assert "**From:** sender@example.com" in result
        assert "**To:** recipient@example.com" in result
        assert "**Date:** 2024-01-15 10:30:00" in result

    def test_format_email_detail_includes_subject_as_h2_heading(self) -> None:
        """Test that subject is formatted as H2 heading."""
        email = {
            "message_id": "test-123@example.com",
            "subject": "Project Update",
            "sender": "john@example.com",
            "recipient": "me@company.com",
            "cc": "",
            "date": "2024-01-15 10:30:00",
            "body_text": "Body text here.",
        }

        result = format_email_detail(email)

        assert result.startswith("## Project Update")

    def test_format_email_detail_includes_body_text(self) -> None:
        """Test that body text is included with proper formatting."""
        email = {
            "message_id": "test-123@example.com",
            "subject": "Test",
            "sender": "sender@example.com",
            "recipient": "recipient@example.com",
            "cc": "",
            "date": "2024-01-15 10:30:00",
            "body_text": "Line 1\nLine 2\nLine 3",
        }

        result = format_email_detail(email)

        assert "Line 1" in result
        assert "Line 2" in result
        assert "Line 3" in result

    def test_format_email_detail_handles_missing_optional_fields(self) -> None:
        """Test that missing optional fields are handled gracefully."""
        email = {
            "message_id": "test-123@example.com",
            "subject": "Test",
            "sender": "sender@example.com",
            "recipient": "recipient@example.com",
            "cc": None,
            "date": "2024-01-15 10:30:00",
            "body_text": "Body",
        }

        result = format_email_detail(email)

        assert "**Cc:**" not in result
        assert "**From:**" in result
        assert "**To:**" in result

    def test_format_email_detail_includes_classification_when_present(self) -> None:
        """Test that classification info is shown when available."""
        email = {
            "message_id": "test-123@example.com",
            "subject": "Important Meeting",
            "sender": "boss@company.com",
            "recipient": "me@company.com",
            "cc": "",
            "date": "2024-01-15 10:30:00",
            "body_text": "Please attend.",
            "importance": "high",
            "category": "work",
            "classification_confidence": 0.85,
        }

        result = format_email_detail(email)

        assert "### Classification" in result
        assert "**Importance:** high" in result
        assert "**Category:** work" in result

    def test_format_email_detail_includes_attachments_with_paths(self) -> None:
        """Test that attachments are shown with file paths."""
        email = {
            "message_id": "test-123@example.com",
            "subject": "Report",
            "sender": "sender@example.com",
            "recipient": "recipient@example.com",
            "cc": "",
            "date": "2024-01-15 10:30:00",
            "body_text": "See attached.",
            "attachments": [
                {
                    "filename": "report.pdf",
                    "content_type": "application/pdf",
                    "size": 2457600,
                    "local_path": "/path/to/report.pdf",
                }
            ],
        }

        result = format_email_detail(email)

        assert "### Attachments" in result
        assert "report.pdf" in result
        assert "Path:" in result
        assert "/path/to/report.pdf" in result

    def test_format_email_detail_with_thread_timeline(self) -> None:
        """Test that thread timeline is included when provided."""
        email = {
            "message_id": "msg-2@example.com",
            "subject": "Re: Original Subject",
            "sender": "sender@example.com",
            "recipient": "recipient@example.com",
            "date": "2024-01-15 10:30:00",
            "body_text": "Reply content.",
        }
        timeline = [
            {
                "message_id": "msg-1@example.com",
                "subject": "Original Subject",
                "date": "2024-01-14 09:00:00",
            },
            {
                "message_id": "msg-2@example.com",
                "subject": "Re: Original Subject",
                "date": "2024-01-15 10:30:00",
            },
        ]

        result = format_email_detail(email, thread_timeline=timeline)

        assert "### Thread Context" in result


class TestFormatHeaders:
    """Tests for format_headers function."""

    def test_format_headers_includes_all_fields(self) -> None:
        """Test that format_headers includes from, to, cc, date, subject."""
        email = {
            "sender": "John Doe <john@example.com>",
            "recipient": "me@company.com",
            "cc": "team@company.com",
            "date": "2024-01-15 10:30:00",
        }

        result = format_headers(email)

        assert "**From:** John Doe <john@example.com>" in result
        assert "**To:** me@company.com" in result
        assert "**Cc:** team@company.com" in result
        assert "**Date:** 2024-01-15 10:30:00" in result

    def test_format_headers_handles_empty_cc(self) -> None:
        """Test that empty cc field is handled gracefully."""
        email = {
            "sender": "sender@example.com",
            "recipient": "recipient@example.com",
            "cc": "",
            "date": "2024-01-15 10:30:00",
        }

        result = format_headers(email)

        assert "**Cc:**" not in result
        assert "**From:**" in result
        assert "**To:**" in result

    def test_format_headers_preserves_date_format(self) -> None:
        """Test that date format is preserved as-is from database."""
        email = {
            "sender": "sender@example.com",
            "recipient": "recipient@example.com",
            "cc": "",
            "date": "2024-01-15 10:30:00",
        }

        result = format_headers(email)

        assert "**Date:** 2024-01-15 10:30:00" in result

    def test_format_headers_handles_none_values(self) -> None:
        """Test that None values are handled gracefully."""
        email = {
            "sender": "sender@example.com",
            "recipient": "recipient@example.com",
            "cc": None,
            "date": "2024-01-15 10:30:00",
        }

        result = format_headers(email)

        assert "**Cc:**" not in result


class TestFormatClassification:
    """Tests for format_classification function."""

    def test_format_classification_shows_importance_and_category(self) -> None:
        """Test that format_classification shows importance and category."""
        email = {
            "importance": "high",
            "category": "work",
            "classification_confidence": 0.85,
        }

        result = format_classification(email)

        assert "### Classification" in result
        assert "**Importance:** high" in result
        assert "**Category:** work" in result

    def test_format_classification_shows_confidence_score(self) -> None:
        """Test that format_classification shows confidence score."""
        email = {
            "importance": "high",
            "category": "work",
            "classification_confidence": 0.85,
        }

        result = format_classification(email)

        assert "(confidence: 0.85)" in result

    def test_format_classification_returns_empty_for_default(self) -> None:
        """Test that format_classification returns empty string for default classification."""
        email = {
            "importance": "normal",
            "category": "uncategorized",
            "classification_confidence": 0.0,
        }

        result = format_classification(email)

        assert result == ""

    def test_format_classification_handles_uncategorized_gracefully(self) -> None:
        """Test that uncategorized emails with non-default importance are shown."""
        email = {
            "importance": "high",
            "category": "uncategorized",
            "classification_confidence": 0.75,
        }

        result = format_classification(email)

        assert "**Importance:** high" in result
        assert "**Category:** uncategorized" in result

    def test_format_classification_hides_confidence_when_low(self) -> None:
        """Test that confidence is hidden when below 0.5."""
        email = {
            "importance": "high",
            "category": "work",
            "classification_confidence": 0.4,
        }

        result = format_classification(email)

        assert "(confidence:" not in result

    def test_format_classification_hides_confidence_on_manual_override(self) -> None:
        """Test that confidence is hidden when manual_override is True."""
        email = {
            "importance": "high",
            "category": "work",
            "classification_confidence": 1.0,
            "manual_override": True,
        }

        result = format_classification(email)

        assert "(confidence:" not in result


class TestFormatAttachmentsDetail:
    """Tests for format_attachments_detail function."""

    def test_format_attachments_detail_shows_file_paths(self) -> None:
        """Test that format_attachments_detail shows file paths."""
        email = {
            "message_id": "test-123@example.com",
            "attachments": [
                {
                    "filename": "report.pdf",
                    "content_type": "application/pdf",
                    "size": 2457600,
                    "local_path": "/attachments/test-123/report.pdf",
                }
            ],
        }

        result = format_attachments_detail(email)

        assert "### Attachments" in result
        assert "report.pdf" in result
        assert "Path:" in result
        assert "/attachments/test-123/report.pdf" in result

    def test_format_attachments_detail_shows_filename_and_size(self) -> None:
        """Test that format_attachments_detail shows filename and size."""
        email = {
            "message_id": "test-123@example.com",
            "attachments": [
                {
                    "filename": "report.pdf",
                    "content_type": "application/pdf",
                    "size": 2457600,
                    "local_path": "/attachments/test-123/report.pdf",
                },
                {
                    "filename": "image.png",
                    "content_type": "image/png",
                    "size": 159744,
                    "local_path": "/attachments/test-123/image.png",
                },
            ],
        }

        result = format_attachments_detail(email)

        assert "report.pdf" in result
        assert "2.3 MB" in result
        assert "image.png" in result
        assert "156 KB" in result

    def test_format_attachments_detail_returns_empty_if_no_attachments(self) -> None:
        """Test that format_attachments_detail returns empty string if no attachments."""
        email = {
            "message_id": "test-123@example.com",
            "attachments": [],
        }

        result = format_attachments_detail(email)

        assert result == ""

    def test_format_attachments_detail_with_summary(self) -> None:
        """Test that format_attachments_detail shows content summary when db is provided."""
        email = {
            "message_id": "test-123@example.com",
            "attachments": [
                {
                    "filename": "report.pdf",
                    "content_type": "application/pdf",
                    "size": 1024,
                    "local_path": "/attachments/test-123/report.pdf",
                }
            ],
        }

        mock_db = MagicMock()
        mock_db.get_attachment_content.return_value = "This is the content of the PDF document."

        result = format_attachments_detail(email, db=mock_db, include_summary=True)

        assert "Summary:" in result
        assert "This is the content" in result
        mock_db.get_attachment_content.assert_called_once_with("/attachments/test-123/report.pdf")

    def test_format_attachments_detail_summary_unparsed(self) -> None:
        """Test that format_attachments_detail shows unparsed message when no content."""
        email = {
            "message_id": "test-123@example.com",
            "attachments": [
                {
                    "filename": "report.pdf",
                    "content_type": "application/pdf",
                    "size": 1024,
                    "local_path": "/attachments/test-123/report.pdf",
                }
            ],
        }

        mock_db = MagicMock()
        mock_db.get_attachment_content.return_value = None

        result = format_attachments_detail(email, db=mock_db, include_summary=True)

        assert "Summary:" in result
        assert "未解析" in result

    def test_format_attachments_detail_no_local_path(self) -> None:
        """Test that format_attachments_detail handles missing local_path."""
        email = {
            "message_id": "test-123@example.com",
            "attachments": [
                {
                    "filename": "report.pdf",
                    "content_type": "application/pdf",
                    "size": 1024,
                    "local_path": "",
                }
            ],
        }

        result = format_attachments_detail(email)

        assert "report.pdf" in result
        assert "无本地文件" in result


class TestFormatThreadContext:
    """Tests for format_thread_context function."""

    def test_format_thread_context_shows_parent_emails(self) -> None:
        """Test that format_thread_context shows parent emails."""
        email = {
            "message_id": "msg-2@example.com",
            "subject": "Re: Original Subject",
            "date": "2024-01-15 10:30:00",
        }
        timeline = [
            {
                "message_id": "msg-1@example.com",
                "subject": "Original Subject",
                "date": "2024-01-14 09:00:00",
            },
            {
                "message_id": "msg-2@example.com",
                "subject": "Re: Original Subject",
                "date": "2024-01-15 10:30:00",
            },
        ]
        current_message_id = "msg-2@example.com"

        result = format_thread_context(email, timeline, current_message_id)

        assert "### Thread Context" in result
        assert "[Parent]" in result or "Original Subject" in result

    def test_format_thread_context_shows_reply_emails(self) -> None:
        """Test that format_thread_context shows reply emails."""
        email = {
            "message_id": "msg-1@example.com",
            "subject": "Original Subject",
            "date": "2024-01-14 09:00:00",
        }
        timeline = [
            {
                "message_id": "msg-1@example.com",
                "subject": "Original Subject",
                "date": "2024-01-14 09:00:00",
            },
            {
                "message_id": "msg-2@example.com",
                "subject": "Re: Original Subject",
                "date": "2024-01-15 10:30:00",
            },
        ]
        current_message_id = "msg-1@example.com"

        result = format_thread_context(email, timeline, current_message_id)

        assert "[Reply]" in result or "Re: Original Subject" in result

    def test_format_thread_context_highlights_current_email(self) -> None:
        """Test that current email is highlighted in the thread."""
        email = {
            "message_id": "msg-2@example.com",
            "subject": "Re: Original Subject",
            "date": "2024-01-15 10:30:00",
        }
        timeline = [
            {
                "message_id": "msg-1@example.com",
                "subject": "Original Subject",
                "date": "2024-01-14 09:00:00",
            },
            {
                "message_id": "msg-2@example.com",
                "subject": "Re: Original Subject",
                "date": "2024-01-15 10:30:00",
            },
        ]
        current_message_id = "msg-2@example.com"

        result = format_thread_context(email, timeline, current_message_id)

        assert "[Current]" in result
        assert "**" in result

    def test_format_thread_context_returns_empty_if_no_thread(self) -> None:
        """Test that format_thread_context returns empty string if no thread context."""
        email = {
            "message_id": "msg-1@example.com",
            "subject": "Standalone Subject",
            "date": "2024-01-15 10:30:00",
        }
        timeline = [
            {
                "message_id": "msg-1@example.com",
                "subject": "Standalone Subject",
                "date": "2024-01-15 10:30:00",
            },
        ]
        current_message_id = "msg-1@example.com"

        result = format_thread_context(email, timeline, current_message_id)

        assert result == ""

    def test_format_thread_context_truncates_long_subjects(self) -> None:
        """Test that long subjects are truncated to 50 chars."""
        long_subject = "This is a very long subject line that exceeds fifty characters"
        email = {
            "message_id": "msg-2@example.com",
            "subject": f"Re: {long_subject}",
            "date": "2024-01-15 10:30:00",
        }
        timeline = [
            {
                "message_id": "msg-1@example.com",
                "subject": long_subject,
                "date": "2024-01-14 09:00:00",
            },
            {
                "message_id": "msg-2@example.com",
                "subject": f"Re: {long_subject}",
                "date": "2024-01-15 10:30:00",
            },
        ]
        current_message_id = "msg-2@example.com"

        result = format_thread_context(email, timeline, current_message_id)

        assert len(result) < 500
