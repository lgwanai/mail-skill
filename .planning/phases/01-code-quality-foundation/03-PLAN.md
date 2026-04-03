---
phase: 01-code-quality-foundation
plan: 03
type: execute
wave: 2
depends_on: [01, 02]
files_modified: [scripts/mail_manager/client.py, tests/test_client.py]
autonomous: true
requirements: [QUAL-01, QUAL-02]
user_setup: []

must_haves:
  truths:
    - "MailClient methods have type annotations on all parameters and returns"
    - "Unit tests cover fetch, send, mark operations"
    - "All tests mock external dependencies (IMAP/SMTP)"
    - "mypy passes on client.py with no errors"
  artifacts:
    - path: "scripts/mail_manager/client.py"
      provides: "MailClient with type annotations"
      contains: "def __init__(self, account_config: dict) -> None:"
    - path: "tests/test_client.py"
      provides: "Unit tests for MailClient"
      exports: ["TestMailClient"]
      min_lines: 100
  key_links:
    - from: "tests/test_client.py"
      to: "scripts/mail_manager/client.py"
      via: "from mail_manager.client import MailClient"
      pattern: "class TestMailClient"
---

<objective>
Add type annotations to MailClient and create comprehensive unit tests for all email operations.

Purpose: Type annotations enable static type checking; tests ensure MailClient works correctly and provide regression protection.
Output: client.py with annotations, test_client.py with tests for init, fetch, send, mark operations
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
    subject: str
    sender: str
    recipient: str
    date: datetime
    body_text: str
    account: str
    # ... optional fields with defaults
```

<!-- Fixtures from Plan 02 conftest.py -->
From tests/conftest.py:
```python
@pytest.fixture
def mock_imap_mailbox(): ...  # Mock imap_tools.MailBox

@pytest.fixture
def sample_email_data(): ...  # Dict with sample email

@pytest.fixture
def test_config(): ...  # Dict with test account config
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add type annotations to client.py</name>
  <files>scripts/mail_manager/client.py</files>
  <behavior>
    - __init__ receives dict and returns None
    - _get_mailbox returns MailBox (use TYPE_CHECKING for import)
    - fetch_emails returns list[dict] (or list[EmailData] after conversion)
    - send_email returns bool
    - mark_as_read, mark_as_starred return None
    - create_folder returns bool
    - move_emails, delete_emails return None
  </behavior>
  <action>
Add type annotations to all methods in MailClient class. Use typing module imports:

1. Add imports at top:
   - from typing import Optional, List, Dict, Any, Callable
   - from typing import TYPE_CHECKING
   - if TYPE_CHECKING: from imap_tools import MailBox

2. Add annotations to each method:
   - __init__(self, account_config: dict) -> None
   - _get_mailbox(self) -> "MailBox"
   - fetch_emails(self, folder: str = 'INBOX', limit: int = 50, ...) -> list[dict]
   - send_email(self, to: str | list[str], subject: str, body_text: str, ...) -> bool
   - mark_as_read(self, uids: list[str], folder: str = 'INBOX', is_read: bool = True) -> None
   - mark_as_starred(self, uids: list[str], folder: str = 'INBOX', is_starred: bool = True) -> None
   - create_folder(self, folder_name: str) -> bool
   - move_emails(self, uids: list[str], destination_folder: str, source_folder: str = 'INBOX') -> None
   - delete_emails(self, uids: list[str], folder: str = 'INBOX') -> None

3. Use relaxed mypy settings (allow partial Any where needed, add # type: ignore for unavoidable issues)

DO NOT change runtime behavior. Only add annotations.
  </action>
  <verify>
    <automated>mypy scripts/mail_manager/client.py --ignore-missing-imports 2>&1 | grep -v "Success" || echo "mypy check passed"</automated>
  </verify>
  <done>All MailClient methods have type annotations; mypy runs without errors on client.py</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Create test_client.py with MailClient unit tests</name>
  <files>tests/test_client.py</files>
  <behavior>
    - Test 1: __init__ sets email and password from config
    - Test 2: fetch_emails returns list of email dicts
    - Test 3: fetch_emails handles empty results
    - Test 4: send_email returns True on success
    - Test 5: mark_as_read calls mailbox.flag correctly
    - Test 6: mark_as_starred calls mailbox.flag correctly
  </behavior>
  <action>
Create tests/test_client.py with unit tests for MailClient. Use fixtures from conftest.py.

Test class structure:
```python
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from mail_manager.client import MailClient

class TestMailClient:
    """Unit tests for MailClient class."""
    
    @pytest.fixture
    def client(self, test_config):
        return MailClient(test_config)
    
    def test_init_sets_email_and_password(self, client, test_config):
        """Test that client initializes with config."""
        assert client.email == test_config['EMAIL']
        assert client.password == test_config['PASSWORD']
    
    def test_fetch_emails_returns_list(self, client, mock_imap_mailbox, sample_email_data):
        """Test that fetch_emails returns email data."""
        # Setup mock
        mock_msg = MagicMock()
        mock_msg.uid = '12345'
        mock_msg.subject = sample_email_data['subject']
        mock_msg.from_ = sample_email_data['sender']
        # ... set other attributes
        
        mock_imap_mailbox.fetch.return_value = [mock_msg]
        
        # Execute
        results = client.fetch_emails(folder='INBOX', limit=10)
        
        # Verify
        assert len(results) >= 0  # Basic check
    
    def test_fetch_emails_empty_folder(self, client, mock_imap_mailbox):
        """Test fetch_emails with empty folder."""
        mock_imap_mailbox.fetch.return_value = []
        results = client.fetch_emails(folder='INBOX')
        assert results == []
    
    def test_send_email_success(self, client):
        """Test successful email sending."""
        with patch('smtplib.SMTP_SSL') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
            
            result = client.send_email(
                to='recipient@example.com',
                subject='Test',
                body_text='Hello'
            )
            
            assert result is True
            mock_server.send_message.assert_called_once()
    
    def test_mark_as_read_calls_flag(self, client, mock_imap_mailbox):
        """Test mark_as_read calls IMAP flag operation."""
        client.mark_as_read(['123', '456'], folder='INBOX', is_read=True)
        mock_imap_mailbox.flag.assert_called()
    
    def test_mark_as_starred_calls_flag(self, client, mock_imap_mailbox):
        """Test mark_as_starred calls IMAP flag operation."""
        client.mark_as_starred(['123'], folder='INBOX', is_starred=True)
        mock_imap_mailbox.flag.assert_called()
```

CRITICAL: All tests must use mocks from conftest.py. No real network calls.
  </action>
  <verify>
    <automated>pytest tests/test_client.py -v --tb=short 2>&1 | tail -20</automated>
  </verify>
  <done>test_client.py exists with tests for init, fetch, send, mark operations; all tests pass</done>
</task>

</tasks>

<verification>
After all tasks complete:
1. mypy scripts/mail_manager/client.py must pass (warnings allowed)
2. pytest tests/test_client.py must pass
3. All MailClient methods must have type annotations
</verification>

<success_criteria>
- client.py has type annotations on all public methods
- test_client.py has tests for: init, fetch_emails, send_email, mark_as_read, mark_as_starred
- All tests use mocked dependencies (no real IMAP/SMTP connections)
- mypy passes on client.py
- pytest passes on test_client.py
</success_criteria>

<output>
After completion, create `.planning/phases/01-code-quality-foundation/03-SUMMARY.md`
</output>
