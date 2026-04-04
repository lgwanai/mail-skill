"""
Unit tests for CLI commands.

Tests verify CLI command handling, error responses, and helper functions.
Uses mocking to avoid real network/database operations.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from mail_manager.errors import ErrorCodes


class TestCLIHelpers:
    """Tests for CLI helper functions."""

    def test_process_attachments_returns_none_for_empty(self) -> None:
        """_process_attachments returns None for no attachments."""
        from mail_cli import _process_attachments

        result = _process_attachments(None)
        assert result is None

        result = _process_attachments([])
        assert result is None

    def test_get_account_paths_returns_dict(self) -> None:
        """_get_account_paths returns path dictionary."""
        from mail_cli import _get_account_paths

        config = {"STORAGE_ROOT": "/tmp/test"}
        result = _get_account_paths(config, "test@example.com")

        assert "root" in result
        assert "db_path" in result
        assert "attach_path" in result
        assert "signature_path" in result

    def test_get_account_paths_sanitizes_email(self) -> None:
        """_get_account_paths sanitizes email address for directory name."""
        from mail_cli import _get_account_paths

        config = {"STORAGE_ROOT": "/tmp/test"}
        result = _get_account_paths(config, "user.name@example.com")

        assert "_at_" in result["root"]


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_config_returns_dict(self) -> None:
        """load_config returns a configuration dictionary."""
        from mail_cli import load_config

        with patch.dict("os.environ", {}, clear=True):
            config = load_config()

        assert "STORAGE_ROOT" in config
        assert "DB_PATH" in config
        assert "ACCOUNTS" in config
        assert isinstance(config["ACCOUNTS"], dict)


class TestCmdRead:
    """Tests for cmd_read command."""

    @pytest.fixture
    def mock_config(self, test_config: dict) -> dict:
        """Create mock config with accounts."""
        return {
            "ACCOUNTS": {"test@example.com": test_config},
            "STORAGE_ROOT": "/tmp/test",
            "DB_PATH": "/tmp/test.db",
            "ATTACHMENT_PATH": "/tmp/attachments",
        }

    def test_cmd_read_returns_error_for_missing_email(
        self, mock_config: dict, capsys: pytest.CaptureFixture
    ) -> None:
        """cmd_read returns error when email not found."""
        from mail_cli import cmd_read

        mock_db = MagicMock()
        mock_db.get_email.return_value = None

        args = MagicMock()
        args.message_id = "nonexistent@example.com"
        args.account = None

        with patch("mail_cli.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.email = "test@example.com"
            mock_get_client.return_value = mock_client
            with patch("mail_cli.MailDatabase") as mock_db_class:
                mock_db_class.return_value.get_email.return_value = None
                cmd_read(args, mock_config, mock_db)

        captured = capsys.readouterr()
        result = json.loads(captured.out)

        assert result["status"] == "error"
        assert result["code"] == ErrorCodes.USER_EMAIL_NOT_FOUND

    def test_cmd_read_displays_email(
        self, mock_config: dict, sample_email_data: dict, capsys: pytest.CaptureFixture
    ) -> None:
        """cmd_read displays email when found."""
        from mail_cli import cmd_read

        mock_db = MagicMock()
        mock_db.get_email.return_value = sample_email_data

        args = MagicMock()
        args.message_id = sample_email_data["message_id"]
        args.account = None

        with patch("mail_cli.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.email = "test@example.com"
            mock_get_client.return_value = mock_client
            with patch("mail_cli.MailDatabase") as mock_db_class:
                mock_db_class.return_value.get_email.return_value = sample_email_data
                with patch("mail_cli._render_table") as mock_render:
                    mock_render.return_value = "Email content"
                    cmd_read(args, mock_config, mock_db)

        captured = capsys.readouterr()
        # Should output table markdown
        assert "Email content" in captured.out


class TestCmdSend:
    """Tests for cmd_send command."""

    @pytest.fixture
    def mock_config(self, test_config: dict) -> dict:
        """Create mock config with accounts."""
        return {
            "ACCOUNTS": {"test@example.com": test_config},
            "STORAGE_ROOT": "/tmp/test",
            "DB_PATH": "/tmp/test.db",
            "ATTACHMENT_PATH": "/tmp/attachments",
        }

    def test_cmd_send_returns_success(
        self, mock_config: dict, capsys: pytest.CaptureFixture
    ) -> None:
        """cmd_send returns success on valid send."""
        from mail_cli import cmd_send

        args = MagicMock()
        args.to = "recipient@example.com"
        args.subject = "Test"
        args.body = "Hello"
        args.attach = None
        args.zip_as = None
        args.cc = None
        args.bcc = None
        args.account = None
        args.html_body = None

        with patch("mail_cli.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.send_email.return_value = True
            mock_client.email = "test@example.com"
            mock_get_client.return_value = mock_client
            with patch("mail_cli._get_account_paths") as mock_paths:
                mock_paths.return_value = {"signature_path": "/tmp/sig.md"}
                with patch("mail_cli._append_signature") as mock_sig:
                    mock_sig.return_value = ("Hello", None)
                    cmd_send(args, mock_config, MagicMock())

        captured = capsys.readouterr()
        result = json.loads(captured.out)

        assert result["status"] == "success"
        assert result["message"] == "Email sent"

    def test_cmd_send_returns_error_on_exception(
        self, mock_config: dict, capsys: pytest.CaptureFixture
    ) -> None:
        """cmd_send returns error on SMTP exception."""
        from mail_cli import cmd_send

        args = MagicMock()
        args.to = "recipient@example.com"
        args.subject = "Test"
        args.body = "Hello"
        args.attach = None
        args.zip_as = None
        args.cc = None
        args.bcc = None
        args.account = None
        args.html_body = None

        with patch("mail_cli.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.send_email.side_effect = Exception("SMTP error")
            mock_client.email = "test@example.com"
            mock_get_client.return_value = mock_client
            with patch("mail_cli._get_account_paths") as mock_paths:
                mock_paths.return_value = {"signature_path": "/tmp/sig.md"}
                with patch("mail_cli._append_signature") as mock_sig:
                    mock_sig.return_value = ("Hello", None)
                    cmd_send(args, mock_config, MagicMock())

        captured = capsys.readouterr()
        result = json.loads(captured.out)

        assert result["status"] == "error"
        assert result["code"] == ErrorCodes.SERVER_SMTP_SEND_FAILED


class TestCmdReply:
    """Tests for cmd_reply command."""

    @pytest.fixture
    def mock_config(self, test_config: dict) -> dict:
        """Create mock config with accounts."""
        return {
            "ACCOUNTS": {"test@example.com": test_config},
            "STORAGE_ROOT": "/tmp/test",
            "DB_PATH": "/tmp/test.db",
            "ATTACHMENT_PATH": "/tmp/attachments",
        }

    def test_cmd_reply_returns_error_for_missing_email(
        self, mock_config: dict, capsys: pytest.CaptureFixture
    ) -> None:
        """cmd_reply returns error when original email not found."""
        from mail_cli import cmd_reply

        args = MagicMock()
        args.message_id = "nonexistent@example.com"
        args.body = "Reply text"
        args.all = False
        args.attach = None
        args.zip_as = None
        args.account = None

        with patch("mail_cli.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.email = "test@example.com"
            mock_get_client.return_value = mock_client
            with patch("mail_cli.MailDatabase") as mock_db_class:
                mock_db_class.return_value.get_email.return_value = None
                cmd_reply(args, mock_config, MagicMock())

        captured = capsys.readouterr()
        result = json.loads(captured.out)

        assert result["status"] == "error"
        assert result["code"] == ErrorCodes.USER_EMAIL_NOT_FOUND


class TestCmdMark:
    """Tests for cmd_mark command."""

    @pytest.fixture
    def mock_config(self, test_config: dict) -> dict:
        """Create mock config with accounts."""
        return {
            "ACCOUNTS": {"test@example.com": test_config},
            "STORAGE_ROOT": "/tmp/test",
            "DB_PATH": "/tmp/test.db",
            "ATTACHMENT_PATH": "/tmp/attachments",
        }

    def test_cmd_mark_returns_error_for_missing_email(
        self, mock_config: dict, capsys: pytest.CaptureFixture
    ) -> None:
        """cmd_mark returns error when email not found."""
        from mail_cli import cmd_mark

        args = MagicMock()
        args.message_id = "nonexistent@example.com"
        args.read = True
        args.starred = None
        args.account = None

        with patch("mail_cli.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.email = "test@example.com"
            mock_get_client.return_value = mock_client
            with patch("mail_cli.MailDatabase") as mock_db_class:
                mock_db_class.return_value.get_email.return_value = None
                cmd_mark(args, mock_config, MagicMock())

        captured = capsys.readouterr()
        result = json.loads(captured.out)

        assert result["status"] == "error"
        assert result["code"] == ErrorCodes.USER_EMAIL_NOT_FOUND


class TestCmdDelete:
    """Tests for cmd_delete command."""

    @pytest.fixture
    def mock_config(self, test_config: dict) -> dict:
        """Create mock config with accounts."""
        return {
            "ACCOUNTS": {"test@example.com": test_config},
            "STORAGE_ROOT": "/tmp/test",
            "DB_PATH": "/tmp/test.db",
            "ATTACHMENT_PATH": "/tmp/attachments",
        }

    def test_cmd_delete_returns_error_for_missing_email(
        self, mock_config: dict, capsys: pytest.CaptureFixture
    ) -> None:
        """cmd_delete returns error when email not found."""
        from mail_cli import cmd_delete

        args = MagicMock()
        args.message_id = "nonexistent@example.com"
        args.account = None

        with patch("mail_cli.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.email = "test@example.com"
            mock_get_client.return_value = mock_client
            with patch("mail_cli.MailDatabase") as mock_db_class:
                mock_db_class.return_value.get_email.return_value = None
                cmd_delete(args, mock_config, MagicMock())

        captured = capsys.readouterr()
        result = json.loads(captured.out)

        assert result["status"] == "error"
        assert result["code"] == ErrorCodes.USER_EMAIL_NOT_FOUND


class TestErrorResponseFormat:
    """Tests for consistent error response format across commands."""

    @pytest.fixture
    def mock_config(self, test_config: dict) -> dict:
        """Create mock config with accounts."""
        return {
            "ACCOUNTS": {"test@example.com": test_config},
            "STORAGE_ROOT": "/tmp/test",
            "DB_PATH": "/tmp/test.db",
            "ATTACHMENT_PATH": "/tmp/attachments",
        }

    def test_all_errors_have_code_field(
        self, mock_config: dict, capsys: pytest.CaptureFixture
    ) -> None:
        """All error responses should have a code field."""
        from mail_cli import cmd_read

        args = MagicMock()
        args.message_id = "nonexistent@example.com"
        args.account = None

        with patch("mail_cli.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.email = "test@example.com"
            mock_get_client.return_value = mock_client
            with patch("mail_cli.MailDatabase") as mock_db_class:
                mock_db_class.return_value.get_email.return_value = None
                cmd_read(args, mock_config, MagicMock())

        captured = capsys.readouterr()
        result = json.loads(captured.out)

        assert "code" in result
        assert isinstance(result["code"], str)

    def test_all_errors_have_message_field(
        self, mock_config: dict, capsys: pytest.CaptureFixture
    ) -> None:
        """All error responses should have a message field."""
        from mail_cli import cmd_read

        args = MagicMock()
        args.message_id = "nonexistent@example.com"
        args.account = None

        with patch("mail_cli.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.email = "test@example.com"
            mock_get_client.return_value = mock_client
            with patch("mail_cli.MailDatabase") as mock_db_class:
                mock_db_class.return_value.get_email.return_value = None
                cmd_read(args, mock_config, MagicMock())

        captured = capsys.readouterr()
        result = json.loads(captured.out)

        assert "message" in result
        assert isinstance(result["message"], str)


class TestCmdAttachments:
    """Tests for cmd_attachments command."""

    @pytest.fixture
    def mock_config(self, test_config: dict) -> dict:
        """Create mock config with accounts."""
        return {
            "ACCOUNTS": {"test@example.com": test_config},
            "STORAGE_ROOT": "/tmp/test",
            "DB_PATH": "/tmp/test.db",
            "ATTACHMENT_PATH": "/tmp/attachments",
        }

    def test_cmd_attachments_empty_list(
        self, mock_config: dict, capsys: pytest.CaptureFixture
    ) -> None:
        """cmd_attachments returns empty list when no attachments."""
        from mail_cli import cmd_attachments

        args = MagicMock()
        args.account = None
        args.limit = 100

        mock_db = MagicMock()
        mock_db.search_emails.return_value = []

        with patch("mail_cli.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.email = "test@example.com"
            mock_get_client.return_value = mock_client
            with patch("mail_cli.MailDatabase") as mock_db_class:
                mock_db_class.return_value = mock_db
                with patch("mail_cli.AttachmentServer") as mock_server_class:
                    mock_server = MagicMock()
                    mock_server.start.return_value = 8080
                    mock_server_class.return_value = mock_server
                    with patch("mail_cli.ServerState") as mock_state_class:
                        mock_state_class.load.return_value = None
                        cmd_attachments(args, mock_config, MagicMock())

        captured = capsys.readouterr()
        result = json.loads(captured.out)

        assert result["status"] == "success"
        assert result["count"] == 0

    def test_cmd_attachments_shows_attachments(
        self, mock_config: dict, capsys: pytest.CaptureFixture
    ) -> None:
        """cmd_attachments lists attachments with preview URLs."""
        from mail_cli import cmd_attachments

        args = MagicMock()
        args.account = None
        args.limit = 100

        mock_db = MagicMock()
        mock_db.search_emails.return_value = [
            {
                "message_id": "msg123",
                "subject": "Test Email",
                "attachments": [
                    {
                        "filename": "document.pdf",
                        "size": 1024,
                        "content_type": "application/pdf",
                        "local_path": "/tmp/attachments/msg123/document.pdf",
                    }
                ],
            }
        ]

        with patch("mail_cli.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.email = "test@example.com"
            mock_get_client.return_value = mock_client
            with patch("mail_cli.MailDatabase") as mock_db_class:
                mock_db_class.return_value = mock_db
                with patch("mail_cli.AttachmentServer") as mock_server_class:
                    mock_server = MagicMock()
                    mock_server.start.return_value = 8080
                    mock_server_class.return_value = mock_server
                    with patch("mail_cli.ServerState") as mock_state_class:
                        mock_state_class.load.return_value = None
                        cmd_attachments(args, mock_config, MagicMock())

        captured = capsys.readouterr()
        result = json.loads(captured.out)

        assert result["status"] == "success"
        assert result["count"] == 1
        assert len(result["attachments"]) == 1
        assert "preview_url" in result["attachments"][0]
        assert "http://127.0.0.1:" in result["attachments"][0]["preview_url"]

    def test_cmd_attachments_reuses_server(
        self, mock_config: dict, capsys: pytest.CaptureFixture
    ) -> None:
        """cmd_attachments reuses existing server from state file."""
        from mail_cli import cmd_attachments

        args = MagicMock()
        args.account = None
        args.limit = 100

        mock_db = MagicMock()
        mock_db.search_emails.return_value = []

        mock_state = MagicMock()
        mock_state.is_running.return_value = True
        mock_state.port = 8085

        with patch("mail_cli.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.email = "test@example.com"
            mock_get_client.return_value = mock_client
            with patch("mail_cli.MailDatabase") as mock_db_class:
                mock_db_class.return_value = mock_db
                with patch("mail_cli.AttachmentServer") as mock_server_class:
                    mock_server = MagicMock()
                    mock_server_class.return_value = mock_server
                    with patch("mail_cli.ServerState") as mock_state_class:
                        mock_state_class.load.return_value = mock_state
                        cmd_attachments(args, mock_config, MagicMock())

        captured = capsys.readouterr()
        result = json.loads(captured.out)

        assert result["port"] == 8085
        # Server.start should not be called since we reused existing
        mock_server.start.assert_not_called()

    def test_cmd_attachments_url_format(
        self, mock_config: dict, capsys: pytest.CaptureFixture
    ) -> None:
        """cmd_attachments generates correct URL format."""
        from mail_cli import cmd_attachments

        args = MagicMock()
        args.account = None
        args.limit = 100

        mock_db = MagicMock()
        mock_db.search_emails.return_value = [
            {
                "message_id": "test@example.com",
                "subject": "Test",
                "attachments": [
                    {
                        "filename": "file.pdf",
                        "size": 100,
                        "content_type": "application/pdf",
                        "local_path": "/tmp/attach/test@example.com/file.pdf",
                    }
                ],
            }
        ]

        with patch("mail_cli.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.email = "test@example.com"
            mock_get_client.return_value = mock_client
            with patch("mail_cli.MailDatabase") as mock_db_class:
                mock_db_class.return_value = mock_db
                with patch("mail_cli._get_account_paths") as mock_paths:
                    mock_paths.return_value = {
                        "attach_path": "/tmp/attach",
                        "root": "/tmp/root",
                        "db_path": "/tmp/test.db",
                    }
                    with patch("mail_cli.AttachmentServer") as mock_server_class:
                        mock_server = MagicMock()
                        mock_server.start.return_value = 8080
                        mock_server_class.return_value = mock_server
                        with patch("mail_cli.ServerState") as mock_state_class:
                            mock_state_class.load.return_value = None
                            cmd_attachments(args, mock_config, MagicMock())

        captured = capsys.readouterr()
        result = json.loads(captured.out)

        url = result["attachments"][0]["preview_url"]
        assert url.startswith("http://127.0.0.1:8080/")


class TestCmdSmartSearch:
    """Tests for cmd_smart_search command."""

    @pytest.fixture
    def mock_config(self, test_config: dict) -> dict:
        """Create mock config with accounts."""
        return {
            "ACCOUNTS": {"test@example.com": test_config},
            "STORAGE_ROOT": "/tmp/test",
            "DB_PATH": "/tmp/test.db",
            "ATTACHMENT_PATH": "/tmp/attachments",
        }

    def test_smart_search_returns_parsed_query(
        self, mock_config: dict, capsys: pytest.CaptureFixture
    ) -> None:
        """smart-search returns parsed_query in response."""
        from mail_cli import cmd_smart_search

        args = MagicMock()
        args.query = "预算讨论"
        args.account = None
        args.limit = 20

        mock_db = MagicMock()
        mock_db.get_unique_senders.return_value = []
        mock_db.search_hybrid.return_value = []

        with patch("mail_cli.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.email = "test@example.com"
            mock_get_client.return_value = mock_client
            with patch("mail_cli.MailDatabase") as mock_db_class:
                mock_db_class.return_value = mock_db
                with patch("mail_cli._get_account_paths") as mock_paths:
                    mock_paths.return_value = {
                        "db_path": "/tmp/test.db",
                        "root": "/tmp/test",
                    }
                    cmd_smart_search(args, mock_config, MagicMock())

        captured = capsys.readouterr()
        result = json.loads(captured.out)

        assert result["status"] == "success"
        assert "parsed_query" in result
        assert result["parsed_query"]["original"] == "预算讨论"
        assert result["parsed_query"]["keywords"] == "预算讨论"

    def test_smart_search_with_date_extraction(
        self, mock_config: dict, capsys: pytest.CaptureFixture
    ) -> None:
        """smart-search extracts date from query."""
        from datetime import date

        from mail_cli import cmd_smart_search

        args = MagicMock()
        args.query = "上周邮件"
        args.account = None
        args.limit = 20

        mock_db = MagicMock()
        mock_db.get_unique_senders.return_value = []
        mock_db.search_emails.return_value = []

        # Use a fixed reference date for predictable results
        ref_date = date(2024, 1, 15)  # Monday

        with patch("mail_cli.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.email = "test@example.com"
            mock_get_client.return_value = mock_client
            with patch("mail_cli.MailDatabase") as mock_db_class:
                mock_db_class.return_value = mock_db
                with patch("mail_cli._get_account_paths") as mock_paths:
                    mock_paths.return_value = {
                        "db_path": "/tmp/test.db",
                        "root": "/tmp/test",
                    }
                    with patch("mail_manager.query_parser.date") as mock_date:
                        mock_date.today.return_value = ref_date
                        cmd_smart_search(args, mock_config, MagicMock())

        captured = capsys.readouterr()
        result = json.loads(captured.out)

        assert result["status"] == "success"
        assert result["parsed_query"]["date_range"] is not None

    def test_smart_search_with_sender_matching(
        self, mock_config: dict, capsys: pytest.CaptureFixture
    ) -> None:
        """smart-search matches sender from query to database senders."""
        import mail_cli

        # Clear sender cache to ensure test isolation
        mail_cli._sender_cache.clear()

        from mail_cli import cmd_smart_search

        args = MagicMock()
        args.query = "王总发的邮件"
        args.account = None
        args.limit = 20

        mock_db = MagicMock()
        mock_db.get_unique_senders.return_value = [
            "王总 <wang@example.com>",
            "其他 <other@example.com>",
        ]
        mock_db.search_emails.return_value = []

        with patch("mail_cli.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.email = "test@example.com"
            mock_get_client.return_value = mock_client
            with patch("mail_cli.MailDatabase") as mock_db_class:
                mock_db_class.return_value = mock_db
                with patch("mail_cli._get_account_paths") as mock_paths:
                    mock_paths.return_value = {
                        "db_path": "/tmp/test.db",
                        "root": "/tmp/test",
                    }
                    cmd_smart_search(args, mock_config, MagicMock())

        captured = capsys.readouterr()
        result = json.loads(captured.out)

        assert result["status"] == "success"
        # Should have matched sender
        assert result["parsed_query"]["sender"] is not None
        assert len(result["parsed_query"]["sender"]) >= 1

    def test_smart_search_returns_results(
        self, mock_config: dict, capsys: pytest.CaptureFixture
    ) -> None:
        """smart-search returns matching email results."""
        from mail_cli import cmd_smart_search

        args = MagicMock()
        args.query = "test"
        args.account = None
        args.limit = 20

        mock_db = MagicMock()
        mock_db.get_unique_senders.return_value = []
        mock_db.search_hybrid.return_value = [
            {
                "message_id": "msg1@example.com",
                "subject": "Test Subject",
                "sender": "sender@example.com",
                "date": "2024-01-15",
                "body_text": "Test body",
                "folder": "INBOX",
                "is_read": 0,
            }
        ]

        with patch("mail_cli.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.email = "test@example.com"
            mock_get_client.return_value = mock_client
            with patch("mail_cli.MailDatabase") as mock_db_class:
                mock_db_class.return_value = mock_db
                with patch("mail_cli._get_account_paths") as mock_paths:
                    mock_paths.return_value = {
                        "db_path": "/tmp/test.db",
                        "root": "/tmp/test",
                    }
                    cmd_smart_search(args, mock_config, MagicMock())

        captured = capsys.readouterr()
        result = json.loads(captured.out)

        assert result["status"] == "success"
        assert result["count"] >= 1
        assert len(result["results"]) >= 1

    def test_original_search_command_unchanged(
        self, mock_config: dict, capsys: pytest.CaptureFixture
    ) -> None:
        """Original search command behavior is unchanged (backward compatibility)."""
        from mail_cli import cmd_search

        args = MagicMock()
        args.query = "test"
        args.account = None
        args.folder = None
        args.sender = None
        args.subject = None
        args.is_read = None
        args.has_attachment = None
        args.limit = 10
        args.vector = False
        args.hybrid = False

        mock_db = MagicMock()
        mock_db.search_fts.return_value = []

        with patch("mail_cli.get_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.email = "test@example.com"
            mock_get_client.return_value = mock_client
            with patch("mail_cli.MailDatabase") as mock_db_class:
                mock_db_class.return_value = mock_db
                with patch("mail_cli._get_account_paths") as mock_paths:
                    mock_paths.return_value = {
                        "db_path": "/tmp/test.db",
                        "root": "/tmp/test",
                    }
                    cmd_search(args, mock_config, MagicMock())

        captured = capsys.readouterr()
        result = json.loads(captured.out)

        # Original search does NOT include parsed_query
        assert "parsed_query" not in result
        assert result["status"] == "success"

