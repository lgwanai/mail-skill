---
phase: 01-code-quality-foundation
plan: 04
type: execute
wave: 2
depends_on: [01, 02]
files_modified: [scripts/mail_manager/db.py, tests/test_db.py]
autonomous: true
requirements: [QUAL-01, QUAL-02]
user_setup: []

must_haves:
  truths:
    - "MailDatabase methods have type annotations on all parameters and returns"
    - "Unit tests cover save, get, search (FTS, vector, hybrid) operations"
    - "All tests mock ChromaDB and use temporary databases"
    - "mypy passes on db.py with no errors"
  artifacts:
    - path: "scripts/mail_manager/db.py"
      provides: "MailDatabase with type annotations"
      contains: "def save_email(self, email_data: dict) -> None:"
    - path: "tests/test_db.py"
      provides: "Unit tests for MailDatabase"
      exports: ["TestMailDatabase"]
      min_lines: 150
  key_links:
    - from: "tests/test_db.py"
      to: "scripts/mail_manager/db.py"
      via: "from mail_manager.db import MailDatabase"
      pattern: "class TestMailDatabase"
---

<objective>
Add type annotations to MailDatabase and create comprehensive unit tests for all database operations.

Purpose: Type annotations enable static type checking; tests ensure database operations work correctly and provide regression protection.
Output: db.py with annotations, test_db.py with tests for save, get, search operations
</objective>

<execution_context>
@/Users/wuliang/.claude/get-shit-done/workflows/execute-plan.md
@/Users/wuliang/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/01-code-quality-foundation/01-CONTEXT.md
@.planning/phases/01-code-quality-foundation/01-RESEARCH.md
@.planning/phases/01-code-quality-foundation/01-VALIDATION.md
@.planning/phases/01-code-quality-foundation/01-PLAN.md
@.planning/phases/01-code-quality-foundation/02-PLAN.md

<interfaces>
<!-- Types from Plan 01 models.py -->
From scripts/mail_manager/models.py:
```python
@dataclass
class EmailData:
    message_id: str
    # ... other fields
```

<!-- Fixtures from Plan 02 conftest.py -->
From tests/conftest.py:
```python
@pytest.fixture
def temp_db_path(): ...  # Temporary SQLite file path

@pytest.fixture
def mock_chroma_collection(): ...  # Mock ChromaDB collection

@pytest.fixture
def sample_email_data(): ...  # Dict with sample email
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add type annotations to db.py</name>
  <files>scripts/mail_manager/db.py</files>
  <behavior>
    - __init__ receives str and returns None
    - exists returns bool
    - save_email receives dict and returns None
    - get_email returns Optional[dict]
    - search_fts returns list[dict]
    - search_vector returns list[dict]
    - search_hybrid returns list[dict]
    - update_flags returns None
    - delete_email returns None
  </behavior>
  <action>
Add type annotations to all methods in MailDatabase class.

1. Add imports at top:
   - from typing import Optional, List, Dict, Any

2. Add annotations to each method:
   - __init__(self, db_path: str) -> None
   - _get_chroma_collection(self) -> Any  # ChromaDB types are complex
   - _get_connection(self) -> sqlite3.Connection
   - _init_db(self) -> None
   - exists(self, message_id: str) -> bool
   - save_email(self, email_data: dict) -> None
   - search_fts(self, query: str, limit: int = 100, offset: int = 0) -> list[dict]
   - search_vector(self, query: str, limit: int = 10) -> list[dict]
   - _get_reranker(self) -> Any  # CrossEncoder type
   - search_hybrid(self, query: str, limit: int = 10) -> list[dict]
   - get_thread_timeline(self, seed_message_id: str, limit: int = 100) -> list[dict]
   - search_emails(self, query: Optional[str] = None, ...) -> list[dict]
   - get_email(self, message_id: str) -> Optional[dict]
   - update_flags(self, message_id: str, is_read: Optional[bool] = None, ...) -> None
   - delete_email(self, message_id: str) -> None

3. For ChromaDB and CrossEncoder, use Any or add # type: ignore for imports

DO NOT change runtime behavior. Only add annotations.
  </action>
  <verify>
    <automated>mypy scripts/mail_manager/db.py --ignore-missing-imports 2>&1 | grep -v "Success" || echo "mypy check passed"</automated>
  </verify>
  <done>All MailDatabase methods have type annotations; mypy runs without errors on db.py</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Create test_db.py with MailDatabase unit tests</name>
  <files>tests/test_db.py</files>
  <behavior>
    - Test 1: __init__ creates database file and tables
    - Test 2: save_email stores email correctly
    - Test 3: exists returns True for saved email
    - Test 4: get_email retrieves saved email
    - Test 5: search_fts finds emails by keyword
    - Test 6: search_emails filters by criteria
    - Test 7: update_flags modifies email flags
    - Test 8: delete_email removes email
  </behavior>
  <action>
Create tests/test_db.py with unit tests for MailDatabase. Use temp_db_path and mock_chroma_collection fixtures.

Test class structure:
```python
import pytest
import os
from mail_manager.db import MailDatabase

class TestMailDatabase:
    """Unit tests for MailDatabase class."""
    
    @pytest.fixture
    def db(self, temp_db_path, mock_chroma_collection):
        """Create a MailDatabase with temp storage."""
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
    
    def test_save_email_stores_data(self, db, sample_email_data):
        """Test that save_email stores email correctly."""
        db.save_email(sample_email_data)
        
        result = db.get_email(sample_email_data['message_id'])
        assert result is not None
        assert result['subject'] == sample_email_data['subject']
        assert result['sender'] == sample_email_data['sender']
    
    def test_exists_returns_true_for_saved_email(self, db, sample_email_data):
        """Test exists returns True for saved email."""
        db.save_email(sample_email_data)
        assert db.exists(sample_email_data['message_id']) is True
        assert db.exists('nonexistent@example.com') is False
    
    def test_get_email_returns_none_for_missing(self, db):
        """Test get_email returns None for nonexistent email."""
        result = db.get_email('nonexistent@example.com')
        assert result is None
    
    def test_search_fts_finds_email(self, db, sample_email_data):
        """Test FTS search finds emails by keyword."""
        db.save_email(sample_email_data)
        
        results = db.search_fts('Test Subject')
        assert len(results) >= 1
    
    def test_search_emails_filters_by_sender(self, db, sample_email_data):
        """Test search_emails filters by sender."""
        db.save_email(sample_email_data)
        
        results = db.search_emails(sender='sender@example.com')
        assert len(results) >= 1
        
        results = db.search_emails(sender='nonexistent@example.com')
        assert len(results) == 0
    
    def test_update_flags_modifies_read_status(self, db, sample_email_data):
        """Test update_flags changes is_read."""
        db.save_email(sample_email_data)
        
        db.update_flags(sample_email_data['message_id'], is_read=True)
        result = db.get_email(sample_email_data['message_id'])
        assert result['is_read'] is True
        
        db.update_flags(sample_email_data['message_id'], is_read=False)
        result = db.get_email(sample_email_data['message_id'])
        assert result['is_read'] is False
    
    def test_update_flags_modifies_starred_status(self, db, sample_email_data):
        """Test update_flags changes is_starred."""
        db.save_email(sample_email_data)
        
        db.update_flags(sample_email_data['message_id'], is_starred=True)
        result = db.get_email(sample_email_data['message_id'])
        assert result['is_starred'] is True
    
    def test_delete_email_removes_data(self, db, sample_email_data):
        """Test delete_email removes email."""
        db.save_email(sample_email_data)
        assert db.exists(sample_email_data['message_id']) is True
        
        db.delete_email(sample_email_data['message_id'])
        assert db.exists(sample_email_data['message_id']) is False
```

CRITICAL: Use temp_db_path fixture for isolation. Mock ChromaDB for vector search tests.
  </action>
  <verify>
    <automated>pytest tests/test_db.py -v --tb=short 2>&1 | tail -20</automated>
  </verify>
  <done>test_db.py exists with tests for init, save, get, search, update, delete; all tests pass</done>
</task>

</tasks>

<verification>
After all tasks complete:
1. mypy scripts/mail_manager/db.py must pass (warnings allowed)
2. pytest tests/test_db.py must pass
3. All MailDatabase methods must have type annotations
</verification>

<success_criteria>
- db.py has type annotations on all public methods
- test_db.py has tests for: init, save_email, exists, get_email, search_fts, search_emails, update_flags, delete_email
- All tests use temporary database (temp_db_path fixture)
- mypy passes on db.py
- pytest passes on test_db.py
</success_criteria>

<output>
After completion, create `.planning/phases/01-code-quality-foundation/04-SUMMARY.md`
</output>
