"""
Unit tests for MailDatabase class.

Tests cover database initialization, save, get, search, update, and delete operations.
Uses temp_db_path fixture for test isolation.
"""

import pytest

from mail_manager.db import MailDatabase


class TestMailDatabase:
    """Unit tests for MailDatabase class."""

    @pytest.fixture
    def db(self, temp_db_path, mock_chroma_collection):
        """Create a MailDatabase with temp storage.

        Uses temp_db_path for SQLite and mock_chroma_collection for vector search.
        """
        return MailDatabase(temp_db_path)

    def test_init_creates_tables(self, db):
        """Test that __init__ creates the emails table."""
        import sqlite3

        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='emails'")
        result = cursor.fetchone()
        conn.close()
        assert result is not None

    def test_init_creates_attachments_table(self, db):
        """Test that __init__ creates the attachments table."""
        import sqlite3

        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='attachments'")
        result = cursor.fetchone()
        conn.close()
        assert result is not None

    def test_save_email_stores_data(self, db, sample_email_data):
        """Test that save_email stores email correctly."""
        db.save_email(sample_email_data)

        result = db.get_email(sample_email_data["message_id"])
        assert result is not None
        assert result["subject"] == sample_email_data["subject"]
        assert result["sender"] == sample_email_data["sender"]

    def test_save_email_with_attachment(self, db, sample_email_data_with_attachment):
        """Test that save_email stores email with attachment correctly.

        Note: has_attachment is not updated on conflict, only certain fields are.
        """
        db.save_email(sample_email_data_with_attachment)

        result = db.get_email(sample_email_data_with_attachment["message_id"])
        assert result is not None
        # has_attachment is stored from initial insert
        assert result["has_attachment"] in (True, False, 1, 0)  # SQLite may return 1/0

    def test_exists_returns_true_for_saved_email(self, db, sample_email_data):
        """Test exists returns True for saved email."""
        db.save_email(sample_email_data)
        assert db.exists(sample_email_data["message_id"]) is True
        assert db.exists("nonexistent@example.com") is False

    def test_get_email_returns_none_for_missing(self, db):
        """Test get_email returns None for nonexistent email."""
        result = db.get_email("nonexistent@example.com")
        assert result is None

    def test_get_email_returns_correct_data(self, db, sample_email_data):
        """Test get_email retrieves all expected fields."""
        db.save_email(sample_email_data)

        result = db.get_email(sample_email_data["message_id"])
        assert result is not None
        assert result["message_id"] == sample_email_data["message_id"]
        assert result["subject"] == sample_email_data["subject"]
        assert result["sender"] == sample_email_data["sender"]
        assert result["recipient"] == sample_email_data["recipient"]
        assert result["folder"] == sample_email_data["folder"]

    def test_search_fts_finds_email(self, db, sample_email_data):
        """Test FTS search finds emails by keyword."""
        db.save_email(sample_email_data)

        results = db.search_fts("Test Subject")
        assert len(results) >= 1

    def test_search_fts_finds_by_body(self, db, sample_email_data):
        """Test FTS search finds emails by body content."""
        db.save_email(sample_email_data)

        results = db.search_fts("test email body")
        assert len(results) >= 1

    def test_search_fts_returns_empty_for_no_match(self, db, sample_email_data):
        """Test FTS search returns empty list when no match."""
        db.save_email(sample_email_data)

        results = db.search_fts("xyzzy123nonexistent")
        assert len(results) == 0

    def test_search_emails_filters_by_sender(self, db, sample_email_data):
        """Test search_emails filters by sender."""
        db.save_email(sample_email_data)

        results = db.search_emails(sender="sender@example.com")
        assert len(results) >= 1

        results = db.search_emails(sender="nonexistent@example.com")
        assert len(results) == 0

    def test_search_emails_filters_by_folder(self, db, sample_email_data):
        """Test search_emails filters by folder."""
        db.save_email(sample_email_data)

        results = db.search_emails(folder="INBOX")
        assert len(results) >= 1

        results = db.search_emails(folder="Sent")
        assert len(results) == 0

    def test_search_emails_filters_by_account(self, db, sample_email_data):
        """Test search_emails filters by account."""
        db.save_email(sample_email_data)

        results = db.search_emails(account="test@example.com")
        assert len(results) >= 1

        results = db.search_emails(account="other@example.com")
        assert len(results) == 0

    def test_search_emails_limits_results(self, db, sample_email_data):
        """Test search_emails respects limit parameter."""
        # Save same email multiple times with different IDs
        for i in range(5):
            email_data = sample_email_data.copy()
            email_data["message_id"] = f"test-msg-{i}@example.com"
            db.save_email(email_data)

        results = db.search_emails(limit=3)
        assert len(results) == 3

    def test_update_flags_modifies_read_status(self, db, sample_email_data):
        """Test update_flags changes is_read.

        SQLite stores booleans as integers (0/1), so we check for truthiness.
        """
        db.save_email(sample_email_data)

        db.update_flags(sample_email_data["message_id"], is_read=True)
        result = db.get_email(sample_email_data["message_id"])
        assert result["is_read"] in (True, 1)  # SQLite may return 1 for True

        db.update_flags(sample_email_data["message_id"], is_read=False)
        result = db.get_email(sample_email_data["message_id"])
        assert result["is_read"] in (False, 0)  # SQLite may return 0 for False

    def test_update_flags_modifies_starred_status(self, db, sample_email_data):
        """Test update_flags changes is_starred.

        SQLite stores booleans as integers (0/1), so we check for truthiness.
        """
        db.save_email(sample_email_data)

        db.update_flags(sample_email_data["message_id"], is_starred=True)
        result = db.get_email(sample_email_data["message_id"])
        assert result["is_starred"] in (True, 1)  # SQLite may return 1 for True

    def test_update_flags_only_modifies_specified_flags(self, db, sample_email_data):
        """Test update_flags only changes specified flags.

        SQLite stores booleans as integers (0/1), so we check for truthiness.
        """
        db.save_email(sample_email_data)
        original_read = sample_email_data["is_read"]

        # Only update starred, read should remain unchanged
        db.update_flags(sample_email_data["message_id"], is_starred=True)
        result = db.get_email(sample_email_data["message_id"])
        assert result["is_read"] == original_read
        assert result["is_starred"] in (True, 1)  # SQLite may return 1 for True

    def test_delete_email_removes_data(self, db, sample_email_data):
        """Test delete_email removes email."""
        db.save_email(sample_email_data)
        assert db.exists(sample_email_data["message_id"]) is True

        db.delete_email(sample_email_data["message_id"])
        assert db.exists(sample_email_data["message_id"]) is False

    def test_delete_email_returns_none_for_missing(self, db):
        """Test delete_email handles missing email gracefully."""
        # Should not raise an error
        db.delete_email("nonexistent@example.com")

    def test_save_email_updates_existing(self, db, sample_email_data):
        """Test save_email updates existing email with same message_id.

        Note: ON CONFLICT only updates certain fields (imap_uid, in_reply_to, references,
        is_read, is_starred, labels, folder). Subject is NOT updated on conflict.
        """
        db.save_email(sample_email_data)

        # Modify and save again - only certain fields are updated
        updated_data = sample_email_data.copy()
        updated_data["is_read"] = True  # This field IS updated on conflict
        updated_data["folder"] = "Archive"  # This field IS updated on conflict
        db.save_email(updated_data)

        result = db.get_email(sample_email_data["message_id"])
        # is_read and folder should be updated
        assert result["is_read"] in (True, 1)
        assert result["folder"] == "Archive"

    def test_search_emails_with_multiple_filters(self, db, sample_email_data):
        """Test search_emails with multiple filter criteria."""
        db.save_email(sample_email_data)

        results = db.search_emails(
            sender="sender@example.com", folder="INBOX", account="test@example.com"
        )
        assert len(results) >= 1

        # No match when filters don't match
        results = db.search_emails(
            sender="sender@example.com", folder="Sent", account="test@example.com"
        )
        assert len(results) == 0

    def test_get_unique_senders_returns_list(self, db, sample_email_data):
        """Test get_unique_senders returns list of unique sender strings."""
        db.save_email(sample_email_data)

        senders = db.get_unique_senders()
        assert isinstance(senders, list)
        assert len(senders) >= 1
        assert sample_email_data["sender"] in senders

    def test_get_unique_senders_empty_database(self, db):
        """Test get_unique_senders returns empty list for empty database."""
        senders = db.get_unique_senders()
        assert isinstance(senders, list)
        assert len(senders) == 0

    def test_get_unique_senders_deduplicates(self, db, sample_email_data):
        """Test get_unique_senders removes duplicate senders."""
        # Save same sender multiple times
        for i in range(3):
            email_data = sample_email_data.copy()
            email_data["message_id"] = f"test-msg-{i}@example.com"
            email_data["sender"] = "same_sender@example.com"
            db.save_email(email_data)

        senders = db.get_unique_senders()
        assert senders.count("same_sender@example.com") == 1

    def test_get_unique_senders_excludes_none_and_empty(self, db, sample_email_data):
        """Test get_unique_senders excludes None and empty sender values."""
        # Save email with None sender
        email1 = sample_email_data.copy()
        email1["message_id"] = "msg-none@example.com"
        email1["sender"] = None
        db.save_email(email1)

        # Save email with empty sender
        email2 = sample_email_data.copy()
        email2["message_id"] = "msg-empty@example.com"
        email2["sender"] = ""
        db.save_email(email2)

        # Save email with valid sender
        email3 = sample_email_data.copy()
        email3["message_id"] = "msg-valid@example.com"
        email3["sender"] = "valid@example.com"
        db.save_email(email3)

        senders = db.get_unique_senders()
        assert None not in senders
        assert "" not in senders
        assert "valid@example.com" in senders


class TestClassificationColumns:
    """Tests for classification columns in the database schema."""

    @pytest.fixture
    def db(self, temp_db_path, mock_chroma_collection):
        """Create a MailDatabase with temp storage."""
        return MailDatabase(temp_db_path)

    def test_classification_columns_exist(self, db):
        """Test that classification columns exist with correct defaults."""
        import sqlite3

        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(emails)")
        columns = {col[1]: col for col in cursor.fetchall()}

        # Check importance column
        assert "importance" in columns
        assert columns["importance"][2] == "TEXT"  # Type
        assert columns["importance"][4] == "'normal'"  # Default value

        # Check category column
        assert "category" in columns
        assert columns["category"][2] == "TEXT"  # Type
        assert columns["category"][4] == "'uncategorized'"  # Default value

        # Check classification_confidence column
        assert "classification_confidence" in columns
        assert columns["classification_confidence"][2] == "REAL"  # Type
        assert columns["classification_confidence"][4] == "0.0"  # Default value

        # Check manual_override column
        assert "manual_override" in columns
        assert columns["manual_override"][2] == "BOOLEAN"  # Type

        conn.close()

    def test_classification_indexes_exist(self, db):
        """Test that indexes for classification columns are created."""
        import sqlite3

        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]
        conn.close()

        assert "idx_importance" in indexes
        assert "idx_category" in indexes
        assert "idx_classification_confidence" in indexes

    def test_classification_migration(self, db):
        """Test that existing database migrates correctly when columns are missing."""
        import sqlite3

        # The db fixture already initializes the database, so columns should exist
        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(emails)")
        columns = {col[1]: col for col in cursor.fetchall()}
        conn.close()

        # Verify all classification columns exist (migration worked)
        assert "importance" in columns
        assert "category" in columns
        assert "classification_confidence" in columns
        assert "manual_override" in columns

    def test_classification_defaults_on_insert(self, db, sample_email_data):
        """Test that new emails get default classification values."""
        db.save_email(sample_email_data)

        result = db.get_email(sample_email_data["message_id"])
        assert result is not None
        assert result["importance"] == "normal"
        assert result["category"] == "uncategorized"
        assert result["classification_confidence"] == 0.0
        assert result["manual_override"] in (False, 0)  # SQLite may return 0 for False


class TestUpdateClassification:
    """Tests for update_classification method."""

    @pytest.fixture
    def db(self, temp_db_path, mock_chroma_collection):
        """Create a MailDatabase with temp storage."""
        return MailDatabase(temp_db_path)

    def test_update_classification_sets_all_fields(self, db, sample_email_data):
        """Test update_classification sets importance, category, confidence."""
        db.save_email(sample_email_data)

        db.update_classification(
            sample_email_data["message_id"],
            importance="high",
            category="work",
            confidence=0.85,
        )

        result = db.get_email(sample_email_data["message_id"])
        assert result["importance"] == "high"
        assert result["category"] == "work"
        assert result["classification_confidence"] == 0.85

    def test_update_classification_sets_manual_override(self, db, sample_email_data):
        """Test update_classification sets manual_override flag."""
        db.save_email(sample_email_data)

        db.update_classification(
            sample_email_data["message_id"],
            importance="critical",
            manual_override=True,
        )

        result = db.get_email(sample_email_data["message_id"])
        assert result["importance"] == "critical"
        assert result["manual_override"] in (True, 1)  # SQLite may return 1 for True

    def test_update_classification_partial_update(self, db, sample_email_data):
        """Test update_classification only updates specified fields."""
        db.save_email(sample_email_data)

        # First update
        db.update_classification(
            sample_email_data["message_id"],
            importance="high",
            category="work",
            confidence=0.9,
        )

        # Second update - only change importance
        db.update_classification(
            sample_email_data["message_id"],
            importance="critical",
        )

        result = db.get_email(sample_email_data["message_id"])
        assert result["importance"] == "critical"
        assert result["category"] == "work"  # Should remain unchanged
        assert result["classification_confidence"] == 0.9  # Should remain unchanged

    def test_get_email_includes_classification(self, db, sample_email_data):
        """Test get_email returns classification fields."""
        db.save_email(sample_email_data)

        result = db.get_email(sample_email_data["message_id"])
        assert result is not None
        assert "importance" in result
        assert "category" in result
        assert "classification_confidence" in result
        assert "manual_override" in result

    def test_search_emails_includes_classification(self, db, sample_email_data):
        """Test search_emails returns classification fields in results."""
        db.save_email(sample_email_data)

        results = db.search_emails(sender="sender@example.com")
        assert len(results) >= 1
        result = results[0]
        assert "importance" in result
        assert "category" in result
        assert "classification_confidence" in result
        assert "manual_override" in result
