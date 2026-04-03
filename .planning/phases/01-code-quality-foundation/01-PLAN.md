---
phase: 01-code-quality-foundation
plan: 01
type: execute
wave: 1
depends_on: []
files_modified: [pyproject.toml, requirements-dev.txt, scripts/mail_manager/errors.py, scripts/mail_manager/models.py]
autonomous: true
requirements: [QUAL-03, QUAL-04]
user_setup: []

must_haves:
  truths:
    - "pyproject.toml exists with pytest, mypy, and ruff configurations"
    - "requirements-dev.txt exists with all dev dependencies"
    - "Error codes are defined with USER_xxx, SERVER_xxx, BIZ_xxx classification"
    - "Dataclasses exist for EmailData, Attachment, CommandResult"
  artifacts:
    - path: "pyproject.toml"
      provides: "Tool configuration for pytest, mypy, ruff"
      min_lines: 50
    - path: "requirements-dev.txt"
      provides: "Development dependencies"
      contains: "pytest"
    - path: "scripts/mail_manager/errors.py"
      provides: "Error code definitions and response helpers"
      exports: ["ErrorCodes", "error_response", "success_response"]
    - path: "scripts/mail_manager/models.py"
      provides: "Dataclasses for type annotations"
      exports: ["EmailData", "Attachment", "CommandResult"]
  key_links:
    - from: "scripts/mail_manager/errors.py"
      to: "CLI commands"
      via: "import and use error_response/success_response"
      pattern: "from mail_manager.errors import"
---

<objective>
Create the foundational configuration files and shared modules that all subsequent plans will depend on.

Purpose: Establish tool configuration (pytest, mypy, ruff) and create shared error handling + data models before adding tests and type annotations.
Output: pyproject.toml, requirements-dev.txt, errors.py, models.py
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
<!-- Key exports from existing codebase that new modules should align with -->

From scripts/mail_manager/client.py:
```python
class MailClient:
    def __init__(self, account_config): ...
    def fetch_emails(self, folder='INBOX', limit=50, ...): ...
    def send_email(self, to, subject, body_text, ...): ...
    def mark_as_read(self, uids, folder='INBOX', is_read=True): ...
    def mark_as_starred(self, uids, folder='INBOX', is_starred=True): ...
```

From scripts/mail_manager/db.py:
```python
class MailDatabase:
    def __init__(self, db_path): ...
    def save_email(self, email_data): ...
    def get_email(self, message_id): ...
    def search_fts(self, query, limit=100, offset=0): ...
    def search_vector(self, query, limit=10): ...
    def search_hybrid(self, query, limit=10): ...
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create pyproject.toml with tool configurations</name>
  <files>pyproject.toml</files>
  <action>
Create pyproject.toml with complete configuration for pytest, mypy, and ruff. Use the configurations from RESEARCH.md as the basis.

Key settings per user decisions:
- pytest: Start with --cov-fail-under=60 (ramp to 80%), exclude mail_cli.py from coverage
- mypy: Relaxed mode (warn_return_any=false, disallow_untyped_defs=false, ignore_missing_imports=true)
- ruff: PEP 8 standard, line-length=100, target-version="py38"

Include [project] metadata section with name="mail-skill" and version="2.0.0".
  </action>
  <verify>
    <automated>test -f pyproject.toml && grep -q "tool.pytest" pyproject.toml && grep -q "tool.mypy" pyproject.toml && grep -q "tool.ruff" pyproject.toml</automated>
  </verify>
  <done>pyproject.toml exists with pytest, mypy, ruff configurations matching user-locked decisions</done>
</task>

<task type="auto">
  <name>Task 2: Create requirements-dev.txt with development dependencies</name>
  <files>requirements-dev.txt</files>
  <action>
Create requirements-dev.txt with all development dependencies from RESEARCH.md Standard Stack:
- pytest>=7.4.0
- pytest-cov>=4.1.0
- pytest-mock>=3.11.0
- mypy>=1.5.0
- ruff>=0.1.0

Add comment header explaining these are dev-only dependencies.
  </action>
  <verify>
    <automated>test -f requirements-dev.txt && grep -q "pytest>=7.4.0" requirements-dev.txt && grep -q "mypy>=1.5.0" requirements-dev.txt</automated>
  </verify>
  <done>requirements-dev.txt exists with all dev dependencies for testing, type checking, and linting</done>
</task>

<task type="auto">
  <name>Task 3: Create errors.py with error code definitions</name>
  <files>scripts/mail_manager/errors.py</files>
  <action>
Create scripts/mail_manager/errors.py with:

1. ErrorCodes class with categorized constants:
   - USER_xxx: USER_EMAIL_NOT_FOUND, USER_INVALID_MESSAGE_ID, USER_MISSING_PARAMETER, USER_INVALID_PARAMETER
   - SERVER_xxx: SERVER_IMAP_CONNECTION_FAILED, SERVER_SMTP_CONNECTION_FAILED, SERVER_SMTP_SEND_FAILED, SERVER_DATABASE_ERROR, SERVER_CHROMADB_ERROR
   - BIZ_xxx: BIZ_EMAIL_ALREADY_SENT, BIZ_PERMISSION_DENIED, BIZ_ACCOUNT_NOT_CONFIGURED

2. Helper functions:
   - error_response(code: str, message: str) -> dict: Returns {"status": "error", "code": ..., "message": ...}
   - success_response(data: Optional[dict] = None, message: str = "Success") -> dict: Returns {"status": "success", ...}

Use dataclasses for ErrorResponse if desired, but keep helper functions simple.

DO NOT import any external dependencies beyond stdlib (json, dataclasses, typing).
  </action>
  <verify>
    <automated>python3 -c "from mail_manager.errors import ErrorCodes, error_response, success_response; print('USER_EMAIL_NOT_FOUND:', ErrorCodes.USER_EMAIL_NOT_FOUND)"</automated>
  </verify>
  <done>errors.py exists with ErrorCodes class and helper functions; all error codes follow UPPERCASE_UNDERSCORE format with proper classification</done>
</task>

<task type="auto">
  <name>Task 4: Create models.py with dataclasses for type annotations</name>
  <files>scripts/mail_manager/models.py</files>
  <action>
Create scripts/mail_manager/models.py with dataclasses for structured data.

1. EmailData dataclass matching existing email_data dict structure:
   - Required: message_id, subject, sender, recipient, date, body_text, account
   - Optional with defaults: imap_uid, thread_id, in_reply_to, references, cc, html_body, has_attachment, is_read, is_starred, folder
   - attachments: List[Attachment] with field(default_factory=list)

2. Attachment dataclass:
   - filename: str, content_type: str, size: int
   - local_path: Optional[str] = None

3. CommandResult dataclass:
   - status: str ('success' or 'error')
   - code: Optional[str] = None
   - message: Optional[str] = None
   - data: Optional[dict] = None
   - to_dict() method for JSON serialization

Use from __future__ import annotations for Python 3.8 compatibility with forward references.
  </action>
  <verify>
    <automated>python3 -c "from mail_manager.models import EmailData, Attachment, CommandResult; e = EmailData(message_id='x', subject='s', sender='a@b.com', recipient='c@d.com', date='2024-01-01', body_text='test', account='test'); print('EmailData created:', e.message_id)"</automated>
  </verify>
  <done>models.py exists with EmailData, Attachment, CommandResult dataclasses; all have proper type annotations</done>
</task>

</tasks>

<verification>
After all tasks complete:
1. pyproject.toml must have [tool.pytest], [tool.mypy], [tool.ruff] sections
2. requirements-dev.txt must install successfully: pip install -r requirements-dev.txt
3. errors.py must import without errors: python3 -c "from mail_manager.errors import ErrorCodes"
4. models.py must import without errors: python3 -c "from mail_manager.models import EmailData"
</verification>

<success_criteria>
- pyproject.toml exists with complete tool configuration
- requirements-dev.txt exists with all dev dependencies
- errors.py defines ErrorCodes with USER/SERVER/BIZ classification
- models.py defines EmailData, Attachment, CommandResult dataclasses
- All files are syntactically valid Python (importable)
</success_criteria>

<output>
After completion, create `.planning/phases/01-code-quality-foundation/01-SUMMARY.md`
</output>
