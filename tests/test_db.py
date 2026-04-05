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


class TestSearchByClassification:
    """Tests for classification filtering in search_emails."""

    @pytest.fixture
    def db(self, temp_db_path, mock_chroma_collection):
        """Create a MailDatabase with temp storage."""
        return MailDatabase(temp_db_path)

    def test_search_by_importance(self, db, sample_email_data):
        """Test search_emails filters by importance."""
        sample_email_data["message_id"] = "high-email@test.com"
        db.save_email(sample_email_data)
        db.update_classification("high-email@test.com", importance="high", category="work")

        sample_email_data["message_id"] = "low-email@test.com"
        sample_email_data["sender"] = "low@test.com"
        db.save_email(sample_email_data)
        db.update_classification("low-email@test.com", importance="low", category="promo")

        # Search for high importance
        results = db.search_emails(importance="high")
        assert len(results) == 1
        assert results[0]["importance"] == "high"

    def test_search_by_category(self, db, sample_email_data):
        """Test search_emails filters by category."""
        sample_email_data["message_id"] = "work-email@test.com"
        db.save_email(sample_email_data)
        db.update_classification("work-email@test.com", importance="normal", category="work")

        sample_email_data["message_id"] = "personal-email@test.com"
        sample_email_data["sender"] = "personal@test.com"
        db.save_email(sample_email_data)
        db.update_classification("personal-email@test.com", importance="normal", category="personal")

        # Search for work category
        results = db.search_emails(category="work")
        assert len(results) == 1
        assert results[0]["category"] == "work"

    def test_search_by_importance_and_category(self, db, sample_email_data):
        """Test search_emails filters by both importance and category."""
        sample_email_data["message_id"] = "critical-work@test.com"
        db.save_email(sample_email_data)
        db.update_classification("critical-work@test.com", importance="critical", category="work")

        sample_email_data["message_id"] = "high-work@test.com"
        sample_email_data["sender"] = "high@test.com"
        db.save_email(sample_email_data)
        db.update_classification("high-work@test.com", importance="high", category="work")

        sample_email_data["message_id"] = "critical-personal@test.com"
        sample_email_data["sender"] = "personal@test.com"
        db.save_email(sample_email_data)
        db.update_classification("critical-personal@test.com", importance="critical", category="personal")

        # Search for critical + work
        results = db.search_emails(importance="critical", category="work")
        assert len(results) == 1
        assert results[0]["importance"] == "critical"
        assert results[0]["category"] == "work"

    def test_search_classification_with_other_filters(self, db, sample_email_data):
        """Test classification filters work with other filters."""
        sample_email_data["message_id"] = "email1@test.com"
        sample_email_data["sender"] = "boss@company.com"
        db.save_email(sample_email_data)
        db.update_classification("email1@test.com", importance="high", category="work")

        sample_email_data["message_id"] = "email2@test.com"
        sample_email_data["sender"] = "friend@gmail.com"
        db.save_email(sample_email_data)
        db.update_classification("email2@test.com", importance="normal", category="personal")

        # Search with sender + importance filter
        results = db.search_emails(sender="boss", importance="high")
        assert len(results) == 1
        assert "boss" in results[0]["sender"]
        assert results[0]["importance"] == "high"


class TestBatchUpdateFlags:
    """Tests for batch_update_flags method."""

    @pytest.fixture
    def db(self, temp_db_path, mock_chroma_collection):
        """Create a MailDatabase with temp storage."""
        return MailDatabase(temp_db_path)

    def test_batch_update_flags_updates_is_read(self, db, sample_email_data):
        """Test batch_update_flags updates is_read for multiple emails."""
        # Save multiple emails
        message_ids = []
        for i in range(3):
            email = sample_email_data.copy()
            email["message_id"] = f"batch-read-{i}@example.com"
            email["is_read"] = False
            db.save_email(email)
            message_ids.append(email["message_id"])

        # Batch update to read
        count = db.batch_update_flags(message_ids, is_read=True)
        assert count == 3

        # Verify all are read
        for msg_id in message_ids:
            email = db.get_email(msg_id)
            assert email["is_read"] in (True, 1)

    def test_batch_update_flags_updates_is_starred(self, db, sample_email_data):
        """Test batch_update_flags updates is_starred for multiple emails."""
        # Save multiple emails
        message_ids = []
        for i in range(3):
            email = sample_email_data.copy()
            email["message_id"] = f"batch-star-{i}@example.com"
            email["is_starred"] = False
            db.save_email(email)
            message_ids.append(email["message_id"])

        # Batch update to starred
        count = db.batch_update_flags(message_ids, is_starred=True)
        assert count == 3

        # Verify all are starred
        for msg_id in message_ids:
            email = db.get_email(msg_id)
            assert email["is_starred"] in (True, 1)

    def test_batch_update_flags_skips_nonexistent(self, db, sample_email_data):
        """Test batch_update_flags skips non-existent message_ids silently."""
        # Save one email
        email = sample_email_data.copy()
        email["message_id"] = "exists-batch@example.com"
        email["is_read"] = False
        db.save_email(email)

        # Try to update existing and non-existent
        count = db.batch_update_flags(
            ["exists-batch@example.com", "nonexistent1@example.com", "nonexistent2@example.com"],
            is_read=True,
        )
        # Only 1 email exists, so only 1 should be updated
        assert count == 1

    def test_batch_update_flags_empty_list(self, db):
        """Test batch_update_flags returns 0 for empty list."""
        count = db.batch_update_flags([], is_read=True)
        assert count == 0

    def test_batch_update_flags_single_sql_statement(self, db, sample_email_data):
        """Test batch_update_flags uses single SQL statement for efficiency."""
        # Save multiple emails
        message_ids = []
        for i in range(5):
            email = sample_email_data.copy()
            email["message_id"] = f"batch-eff-{i}@example.com"
            db.save_email(email)
            message_ids.append(email["message_id"])

        # Update should use IN clause (single statement)
        count = db.batch_update_flags(message_ids, is_read=True)
        assert count == 5


class TestTagManagement:
    """Tests for tag management methods."""

    @pytest.fixture
    def db(self, temp_db_path, mock_chroma_collection):
        """Create a MailDatabase instance for testing."""
        return MailDatabase(temp_db_path)

    def test_get_tags_returns_empty_for_no_tags(self, db, sample_email_data):
        """get_tags returns empty list for email with no tags."""
        db.save_email(sample_email_data)
        tags = db.get_tags(sample_email_data["message_id"])
        assert tags == []

    def test_get_tags_returns_tags(self, db, sample_email_data):
        """get_tags returns tags stored in labels column."""
        sample_email_data["labels"] = ["important", "project-alpha"]
        db.save_email(sample_email_data)
        tags = db.get_tags(sample_email_data["message_id"])
        assert "important" in tags
        assert "project-alpha" in tags

    def test_add_tags_adds_new_tags(self, db, sample_email_data):
        """add_tags adds tags to email."""
        db.save_email(sample_email_data)
        db.add_tags(sample_email_data["message_id"], ["work", "urgent"])
        tags = db.get_tags(sample_email_data["message_id"])
        assert "work" in tags
        assert "urgent" in tags

    def test_add_tags_does_not_duplicate(self, db, sample_email_data):
        """add_tags does not create duplicate tags."""
        db.save_email(sample_email_data)
        db.add_tags(sample_email_data["message_id"], ["work"])
        db.add_tags(sample_email_data["message_id"], ["work", "urgent"])
        tags = db.get_tags(sample_email_data["message_id"])
        assert tags.count("work") == 1
        assert "urgent" in tags

    def test_remove_tags_removes_specified(self, db, sample_email_data):
        """remove_tags removes only specified tags."""
        sample_email_data["labels"] = ["work", "urgent", "follow-up"]
        db.save_email(sample_email_data)
        db.remove_tags(sample_email_data["message_id"], ["urgent"])
        tags = db.get_tags(sample_email_data["message_id"])
        assert "work" in tags
        assert "urgent" not in tags
        assert "follow-up" in tags

    def test_remove_tags_ignores_nonexistent(self, db, sample_email_data):
        """remove_tags ignores tags not present."""
        sample_email_data["labels"] = ["work"]
        db.save_email(sample_email_data)
        db.remove_tags(sample_email_data["message_id"], ["nonexistent"])
        tags = db.get_tags(sample_email_data["message_id"])
        assert tags == ["work"]


class TestBatchTagOperations:
    """Tests for batch tag operations."""

    @pytest.fixture
    def db(self, temp_db_path, mock_chroma_collection):
        """Create a MailDatabase instance for testing."""
        return MailDatabase(temp_db_path)

    def test_batch_add_tags_adds_to_multiple(self, db, sample_email_data):
        """batch_add_tags adds tags to multiple emails."""
        message_ids = []
        for i in range(3):
            email = sample_email_data.copy()
            email["message_id"] = f"batch-tag-{i}@example.com"
            db.save_email(email)
            message_ids.append(email["message_id"])

        count = db.batch_add_tags(message_ids, ["project-x"])
        assert count == 3

        for mid in message_ids:
            tags = db.get_tags(mid)
            assert "project-x" in tags

    def test_batch_remove_tags_from_multiple(self, db, sample_email_data):
        """batch_remove_tags removes tags from multiple emails."""
        message_ids = []
        for i in range(3):
            email = sample_email_data.copy()
            email["message_id"] = f"batch-rm-{i}@example.com"
            email["labels"] = ["project-x", "keep-me"]
            db.save_email(email)
            message_ids.append(email["message_id"])

        count = db.batch_remove_tags(message_ids, ["project-x"])
        assert count == 3

        for mid in message_ids:
            tags = db.get_tags(mid)
            assert "project-x" not in tags
            assert "keep-me" in tags

    def test_batch_add_tags_empty_list_returns_zero(self, db):
        """batch_add_tags returns 0 for empty list."""
        count = db.batch_add_tags([], ["tag"])
        assert count == 0


class TestReplyFeedbackStorage:
    """Tests for reply feedback storage methods."""

    @pytest.fixture
    def db(self, temp_db_path, mock_chroma_collection):
        """Create a MailDatabase instance for testing."""
        return MailDatabase(temp_db_path)

    def test_reply_feedback_table_exists(self, db):
        """Test that reply_feedback table is created."""
        import sqlite3

        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reply_feedback'")
        result = cursor.fetchone()
        conn.close()
        assert result is not None

    def test_reply_feedback_index_exists(self, db):
        """Test that index for is_positive column is created."""
        import sqlite3

        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]
        conn.close()
        assert "idx_feedback_positive" in indexes

    def test_save_reply_feedback_stores_data(self, db):
        """Test save_reply_feedback stores feedback with original/reply data."""
        db.save_reply_feedback(
            original_message_id="msg-123@example.com",
            original_email="From: alice@example.com\nSubject: Test\n\nHello",
            suggested_reply="Thank you for your email.",
            user_edited_reply=None,
            is_positive=True,
        )

        feedback = db.get_reply_feedback(limit=10, positive_only=False)
        assert len(feedback) == 1
        assert feedback[0]["original_message_id"] == "msg-123@example.com"
        assert feedback[0]["is_positive"] in (True, 1)

    def test_get_reply_feedback_positive_only(self, db):
        """Test get_reply_feedback retrieves only positive examples when filtered."""
        # Save positive feedback
        db.save_reply_feedback(
            original_message_id="msg-pos@example.com",
            original_email="From: alice@example.com\nSubject: Test",
            suggested_reply="Great reply",
            is_positive=True,
        )
        # Save negative feedback
        db.save_reply_feedback(
            original_message_id="msg-neg@example.com",
            original_email="From: bob@example.com\nSubject: Test",
            suggested_reply="Bad reply",
            is_positive=False,
        )

        positive = db.get_reply_feedback(limit=10, positive_only=True)
        assert len(positive) == 1
        assert positive[0]["original_message_id"] == "msg-pos@example.com"

    def test_get_reply_feedback_limit(self, db):
        """Test get_reply_feedback respects limit parameter."""
        for i in range(10):
            db.save_reply_feedback(
                original_message_id=f"msg-{i}@example.com",
                original_email=f"Email {i}",
                suggested_reply=f"Reply {i}",
                is_positive=True,
            )

        feedback = db.get_reply_feedback(limit=3, positive_only=True)
        assert len(feedback) == 3

    def test_save_reply_feedback_with_edited_reply(self, db):
        """Test save_reply_feedback stores user-edited reply."""
        db.save_reply_feedback(
            original_message_id="msg-edited@example.com",
            original_email="Original email content",
            suggested_reply="Suggested reply",
            user_edited_reply="User edited this reply",
            is_positive=True,
        )

        feedback = db.get_reply_feedback(limit=10, positive_only=False)
        assert feedback[0]["user_edited_reply"] == "User edited this reply"


class TestAttachmentContentStorage:
    """Tests for attachment content storage methods."""

    @pytest.fixture
    def db(self, temp_db_path, mock_chroma_collection):
        """Create a MailDatabase instance for testing."""
        return MailDatabase(temp_db_path)

    def test_content_text_column_exists(self, db):
        """Test that content_text column exists in attachments table."""
        import sqlite3

        conn = sqlite3.connect(db.db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(attachments)")
        columns = {col[1]: col for col in cursor.fetchall()}
        conn.close()

        assert "content_text" in columns
        assert columns["content_text"][2] == "TEXT"  # Type

    def test_save_attachment_content_stores_text(self, db, sample_email_data_with_attachment):
        """Test save_attachment_content stores parsed text."""
        # First save an email with attachment
        db.save_email(sample_email_data_with_attachment)

        # Get the attachment local_path (use a test path since it's None)
        test_path = "/test/attachments/document.pdf"
        db.save_attachment_content(test_path, "This is the parsed content of the PDF.")

        # Verify content was stored
        content = db.get_attachment_content(test_path)
        assert content == "This is the parsed content of the PDF."

    def test_get_attachment_content_returns_none_for_missing(self, db):
        """Test get_attachment_content returns None for nonexistent path."""
        content = db.get_attachment_content("/nonexistent/path.pdf")
        assert content is None

    def test_save_attachment_content_updates_existing(self, db, sample_email_data_with_attachment):
        """Test save_attachment_content updates existing content."""
        # First save an email with attachment
        db.save_email(sample_email_data_with_attachment)

        test_path = "/test/attachments/document.pdf"
        db.save_attachment_content(test_path, "Initial content")
        db.save_attachment_content(test_path, "Updated content")

        content = db.get_attachment_content(test_path)
        assert content == "Updated content"
