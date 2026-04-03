---
phase: 01-code-quality-foundation
plan: 02
type: execute
wave: 1
depends_on: []
files_modified: [tests/__init__.py, tests/conftest.py]
autonomous: true
requirements: [QUAL-01]
user_setup: []

must_haves:
  truths:
    - "tests/conftest.py exists with reusable fixtures"
    - "Fixtures mock IMAP, SMTP, and database dependencies"
    - "sample_email_data fixture provides consistent test data"
  artifacts:
    - path: "tests/conftest.py"
      provides: "Shared pytest fixtures for all test files"
      exports: ["mock_imap_mailbox", "temp_db_path", "mock_chroma_collection", "sample_email_data", "test_config"]
      min_lines: 50
    - path: "tests/__init__.py"
      provides: "Python package marker"
  key_links:
    - from: "tests/conftest.py"
      to: "tests/test_*.py"
      via: "pytest fixture injection"
      pattern: "def test_xxx(mock_imap_mailbox, sample_email_data)"
---

<objective>
Create the test infrastructure with shared fixtures that all test files will use.

Purpose: Establish reusable pytest fixtures for mocking external dependencies (IMAP/SMTP/ChromaDB) so tests run fast and isolated.
Output: tests/__init__.py, tests/conftest.py
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

<interfaces>
<!-- Existing code patterns to mock -->

From scripts/mail_manager/client.py:
```python
# MailBox from imap_tools is the boundary to mock
from imap_tools import MailBox, A

class MailClient:
    def _get_mailbox(self) -> MailBox: ...  # Mock this
    def fetch_emails(self, ...) -> list[dict]: ...  # Uses MailBox internally
    def send_email(self, ...) -> bool: ...  # Uses smtplib.SMTP_SSL internally
```

From scripts/mail_manager/db.py:
```python
import chromadb

class MailDatabase:
    def _get_chroma_collection(self): ...  # Mock chromadb.PersistentClient
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create tests directory and __init__.py</name>
  <files>tests/__init__.py</files>
  <action>
Create tests/ directory at project root and an empty tests/__init__.py file to make it a Python package.
  </action>
  <verify>
    <automated>test -d tests && test -f tests/__init__.py</automated>
  </verify>
  <done>tests/ directory exists with __init__.py</done>
</task>

<task type="auto">
  <name>Task 2: Create conftest.py with shared fixtures</name>
  <files>tests/conftest.py</files>
  <action>
Create tests/conftest.py with the following pytest fixtures based on RESEARCH.md Pattern 1:

1. mock_imap_mailbox fixture:
   - Mock imap_tools.MailBox using unittest.mock.patch
   - Return MagicMock that behaves like MailBox context manager
   - Yield the mailbox instance for test customization

2. mock_smtp fixture:
   - Mock smtplib.SMTP_SSL and smtplib.SMTP
   - Return MagicMock for server instance

3. temp_db_path fixture:
   - Create temporary SQLite database file
   - Yield the path for MailDatabase initialization
   - Cleanup after test (os.unlink)

4. mock_chroma_collection fixture:
   - Mock chromadb.PersistentClient
   - Return MagicMock for collection

5. sample_email_data fixture:
   - Return dict with sample email data matching EmailData fields
   - Include message_id, subject, sender, recipient, date, body_text, etc.

6. test_config fixture:
   - Return dict with test email configuration (EMAIL, PASSWORD, IMAP_SERVER, etc.)

Use pytest.fixture decorator. Import from unittest.mock and tempfile.
  </action>
  <verify>
    <automated>python3 -c "import tests.conftest; print('Fixtures:', [f for f in dir(tests.conftest) if not f.startswith('_')])"</automated>
  </verify>
  <done>conftest.py exists with all required fixtures; fixtures are importable and usable by pytest</done>
</task>

</tasks>

<verification>
After all tasks complete:
1. tests/ directory must exist at project root (same level as scripts/)
2. tests/conftest.py must define all fixtures listed above
3. pytest must be able to discover the fixtures: pytest --fixtures tests/conftest.py
</verification>

<success_criteria>
- tests/__init__.py exists
- tests/conftest.py exists with fixtures for: mock_imap_mailbox, mock_smtp, temp_db_path, mock_chroma_collection, sample_email_data, test_config
- All fixtures use proper pytest.fixture decorator
- Fixtures mock at library boundaries (imap_tools, smtplib, chromadb), not internal implementation
</success_criteria>

<output>
After completion, create `.planning/phases/01-code-quality-foundation/02-SUMMARY.md`
</output>
