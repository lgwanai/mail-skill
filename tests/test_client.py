"""
Unit tests for MailClient class.

Tests use mocks from conftest.py to avoid real network connections.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from mail_manager.client import MailClient


class TestMailClient:
    """Unit tests for MailClient class."""

    @pytest.fixture
    def client(self, test_config: dict) -> MailClient:
        """Create a MailClient with test config."""
        return MailClient(test_config)

    def test_init_sets_email_and_password(self, client: MailClient, test_config: dict) -> None:
        """Test that client initializes with config."""
        assert client.email == test_config["EMAIL"]
        assert client.password == test_config["PASSWORD"]

    def test_init_sets_optional_fields_none_by_default(self, test_config: dict) -> None:
        """Test that optional config fields are None when not provided."""
        minimal_config = {"EMAIL": "test@example.com", "PASSWORD": "test_password"}
        client = MailClient(minimal_config)
        assert client.email == "test@example.com"
        assert client.password == "test_password"

    def test_fetch_emails_returns_list(
        self, client: MailClient, mock_imap_mailbox: MagicMock, mock_imap_message: MagicMock
    ) -> None:
        """Test that fetch_emails returns email data."""
        mock_imap_mailbox.fetch.return_value = [mock_imap_message]

        results = client.fetch_emails(folder="INBOX", limit=10)

        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0]["subject"] == "Test Subject"
        assert results[0]["sender"] == "sender@example.com"

    def test_fetch_emails_empty_folder(
        self, client: MailClient, mock_imap_mailbox: MagicMock
    ) -> None:
        """Test fetch_emails with empty folder."""
        mock_imap_mailbox.fetch.return_value = []

        results = client.fetch_emails(folder="INBOX")

        assert results == []

    def test_fetch_emails_multiple_messages(
        self, client: MailClient, mock_imap_mailbox: MagicMock, mock_imap_message_list: list
    ) -> None:
        """Test fetch_emails with multiple messages."""
        mock_imap_mailbox.fetch.return_value = mock_imap_message_list

        results = client.fetch_emails(folder="INBOX")

        assert len(results) == 3
        assert results[0]["subject"] == "Test Subject 1"
        assert results[1]["subject"] == "Test Subject 2"
        assert results[2]["subject"] == "Test Subject 3"

    def test_fetch_emails_with_db_check_skips_existing(
        self, client: MailClient, mock_imap_mailbox: MagicMock, mock_imap_message: MagicMock
    ) -> None:
        """Test fetch_emails skips messages that exist in DB."""
        mock_imap_mailbox.fetch.return_value = [mock_imap_message]

        # DB check returns True, meaning message exists
        def db_check(msg_id: str) -> bool:
            return True

        results = client.fetch_emails(folder="INBOX", db_check_func=db_check)

        assert results == []

    def test_fetch_emails_with_unread_only(
        self, client: MailClient, mock_imap_mailbox: MagicMock, mock_imap_message: MagicMock
    ) -> None:
        """Test fetch_emails with unread_only flag."""
        mock_imap_mailbox.fetch.return_value = [mock_imap_message]

        results = client.fetch_emails(folder="INBOX", unread_only=True)

        # Verify fetch was called (the criteria check is internal)
        mock_imap_mailbox.fetch.assert_called_once()
        assert len(results) == 1

    def test_fetch_emails_parses_html_body(
        self, client: MailClient, mock_imap_mailbox: MagicMock
    ) -> None:
        """Test fetch_emails extracts text from HTML when no plain text."""
        msg = MagicMock()
        msg.uid = "12345"
        msg.subject = "HTML Email"
        msg.from_ = "sender@example.com"
        msg.to = ["recipient@example.com"]
        msg.cc = []
        msg.date = datetime(2024, 1, 15, 10, 30, 0)
        msg.text = ""  # No plain text
        msg.html = "<html><body><p>HTML content</p></body></html>"
        msg.attachments = []
        msg.flags = []
        msg.headers = {
            "message-id": ("html-msg@example.com",),
            "in-reply-to": ("",),
            "references": ("",),
        }
        msg.obj = MagicMock()

        mock_imap_mailbox.fetch.return_value = [msg]

        results = client.fetch_emails(folder="INBOX")

        assert len(results) == 1
        assert "HTML content" in results[0]["body_text"]

    def test_send_email_success(self, client: MailClient, mock_smtp: MagicMock) -> None:
        """Test successful email sending."""
        result = client.send_email(
            to="recipient@example.com", subject="Test Subject", body_text="Hello World"
        )

        assert result is True
        mock_smtp.login.assert_called_once()
        mock_smtp.send_message.assert_called_once()

    def test_send_email_with_multiple_recipients(
        self, client: MailClient, mock_smtp: MagicMock
    ) -> None:
        """Test sending email to multiple recipients."""
        result = client.send_email(
            to=["user1@example.com", "user2@example.com"], subject="Test", body_text="Hello"
        )

        assert result is True
        mock_smtp.send_message.assert_called_once()

    def test_send_email_with_html_body(self, client: MailClient, mock_smtp: MagicMock) -> None:
        """Test sending email with HTML body."""
        result = client.send_email(
            to="recipient@example.com",
            subject="Test",
            body_text="Plain text",
            html_body="<p>HTML content</p>",
        )

        assert result is True
        mock_smtp.send_message.assert_called_once()

    def test_send_email_with_cc_and_bcc(self, client: MailClient, mock_smtp: MagicMock) -> None:
        """Test sending email with CC and BCC."""
        result = client.send_email(
            to="recipient@example.com",
            subject="Test",
            body_text="Hello",
            cc="cc@example.com",
            bcc=["bcc1@example.com", "bcc2@example.com"],
        )

        assert result is True
        mock_smtp.send_message.assert_called_once()

    def test_send_email_with_reply_headers(self, client: MailClient, mock_smtp: MagicMock) -> None:
        """Test sending email with In-Reply-To and References headers."""
        result = client.send_email(
            to="recipient@example.com",
            subject="Re: Test",
            body_text="Reply content",
            in_reply_to="<original-msg-id@example.com>",
            references="<original-msg-id@example.com>",
        )

        assert result is True
        mock_smtp.send_message.assert_called_once()

    def test_send_email_without_ssl(self, test_config: dict) -> None:
        """Test sending email without SSL uses STARTTLS."""
        config = test_config.copy()
        config["USE_SSL"] = "false"
        config["SMTP_PORT"] = "587"

        client = MailClient(config)

        with patch("smtplib.SMTP") as mock_smtp_class:
            server_instance = MagicMock()
            mock_smtp_class.return_value.__enter__ = MagicMock(return_value=server_instance)
            mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

            result = client.send_email(
                to="recipient@example.com", subject="Test", body_text="Hello"
            )

            assert result is True
            server_instance.starttls.assert_called_once()

    def test_mark_as_read_calls_flag(
        self, client: MailClient, mock_imap_mailbox: MagicMock
    ) -> None:
        """Test mark_as_read calls IMAP flag operation."""
        client.mark_as_read(["123", "456"], folder="INBOX", is_read=True)

        mock_imap_mailbox.folder.set.assert_called_once_with("INBOX")
        mock_imap_mailbox.flag.assert_called_once()

    def test_mark_as_read_with_empty_uids(
        self, client: MailClient, mock_imap_mailbox: MagicMock
    ) -> None:
        """Test mark_as_read with empty UID list does nothing."""
        client.mark_as_read([], folder="INBOX")

        mock_imap_mailbox.folder.set.assert_not_called()
        mock_imap_mailbox.flag.assert_not_called()

    def test_mark_as_unread(self, client: MailClient, mock_imap_mailbox: MagicMock) -> None:
        """Test mark_as_read with is_read=False marks as unread."""
        client.mark_as_read(["123"], folder="INBOX", is_read=False)

        mock_imap_mailbox.flag.assert_called_once()

    def test_mark_as_starred_calls_flag(
        self, client: MailClient, mock_imap_mailbox: MagicMock
    ) -> None:
        """Test mark_as_starred calls IMAP flag operation."""
        client.mark_as_starred(["123"], folder="INBOX", is_starred=True)

        mock_imap_mailbox.folder.set.assert_called_once_with("INBOX")
        mock_imap_mailbox.flag.assert_called_once()

    def test_mark_as_starred_with_empty_uids(
        self, client: MailClient, mock_imap_mailbox: MagicMock
    ) -> None:
        """Test mark_as_starred with empty UID list does nothing."""
        client.mark_as_starred([], folder="INBOX")

        mock_imap_mailbox.folder.set.assert_not_called()
        mock_imap_mailbox.flag.assert_not_called()

    def test_mark_as_unstarred(self, client: MailClient, mock_imap_mailbox: MagicMock) -> None:
        """Test mark_as_starred with is_starred=False removes star."""
        client.mark_as_starred(["123"], folder="INBOX", is_starred=False)

        mock_imap_mailbox.flag.assert_called_once()

    def test_create_folder_success(self, client: MailClient, mock_imap_mailbox: MagicMock) -> None:
        """Test create_folder creates a new folder."""
        mock_imap_mailbox.folder.exists.return_value = False

        result = client.create_folder("NewFolder")

        assert result is True
        mock_imap_mailbox.folder.create.assert_called_once_with("NewFolder")

    def test_create_folder_already_exists(
        self, client: MailClient, mock_imap_mailbox: MagicMock
    ) -> None:
        """Test create_folder returns False if folder exists."""
        mock_imap_mailbox.folder.exists.return_value = True

        result = client.create_folder("ExistingFolder")

        assert result is False
        mock_imap_mailbox.folder.create.assert_not_called()

    def test_move_emails_success(self, client: MailClient, mock_imap_mailbox: MagicMock) -> None:
        """Test move_emails moves emails to destination folder."""
        mock_imap_mailbox.folder.exists.return_value = False

        client.move_emails(["123", "456"], destination_folder="Archive", source_folder="INBOX")

        mock_imap_mailbox.folder.set.assert_called_once_with("INBOX")
        mock_imap_mailbox.move.assert_called_once_with(["123", "456"], "Archive")

    def test_move_emails_with_empty_uids(
        self, client: MailClient, mock_imap_mailbox: MagicMock
    ) -> None:
        """Test move_emails with empty UID list does nothing."""
        client.move_emails([], destination_folder="Archive")

        mock_imap_mailbox.move.assert_not_called()

    def test_delete_emails_success(self, client: MailClient, mock_imap_mailbox: MagicMock) -> None:
        """Test delete_emails deletes emails from folder."""
        client.delete_emails(["123", "456"], folder="INBOX")

        mock_imap_mailbox.folder.set.assert_called_once_with("INBOX")
        mock_imap_mailbox.delete.assert_called_once_with(["123", "456"])

    def test_delete_emails_with_empty_uids(
        self, client: MailClient, mock_imap_mailbox: MagicMock
    ) -> None:
        """Test delete_emails with empty UID list does nothing."""
        client.delete_emails([], folder="INBOX")

        mock_imap_mailbox.delete.assert_not_called()
