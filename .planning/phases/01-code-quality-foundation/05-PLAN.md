---
phase: 01-code-quality-foundation
plan: 05
type: execute
wave: 3
depends_on: [03, 04]
files_modified: [scripts/mail_cli.py, tests/test_cli.py, tests/test_errors.py]
autonomous: true
requirements: [QUAL-01, QUAL-02, QUAL-03]
user_setup: []

must_haves:
  truths:
    - "All CLI commands return standardized JSON with status field"
    - "Error codes use USER_xxx, SERVER_xxx, BIZ_xxx classification"
    - "CLI functions have type annotations"
    - "Tests cover reply command (critical path)"
    - "mypy and ruff pass on all files"
  artifacts:
    - path: "scripts/mail_cli.py"
      provides: "CLI with type annotations and unified error handling"
      contains: "from mail_manager.errors import error_response, success_response"
    - path: "tests/test_cli.py"
      provides: "Unit tests for CLI commands"
      min_lines: 100
    - path: "tests/test_errors.py"
      provides: "Tests for error format consistency"
      min_lines: 30
  key_links:
    - from: "scripts/mail_cli.py"
      to: "scripts/mail_manager/errors.py"
      via: "import error_response, success_response"
      pattern: "error_response\\(ErrorCodes\\."
---

<objective>
Migrate CLI to use unified error handling, add type annotations, and create comprehensive CLI tests.

Purpose: Complete the error handling migration for all commands, add type safety to CLI, and test the critical reply command path.
Output: mail_cli.py with error codes and type annotations, test_cli.py, test_errors.py
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

<interfaces>
<!-- Error codes from Plan 01 errors.py -->
From scripts/mail_manager/errors.py:
```python
class ErrorCodes:
    USER_EMAIL_NOT_FOUND = 'USER_EMAIL_NOT_FOUND'
    SERVER_IMAP_CONNECTION_FAILED = 'SERVER_IMAP_CONNECTION_FAILED'
    # ... more codes

def error_response(code: str, message: str) -> dict:
    return {'status': 'error', 'code': code, 'message': message}

def success_response(data: Optional[dict] = None, message: str = 'Success') -> dict:
    return {'status': 'success', ...}
```

<!-- Tested client and db from Plans 03, 04 -->
From scripts/mail_manager/client.py:
```python
class MailClient:
    def fetch_emails(...) -> list[dict]: ...
    def send_email(...) -> bool: ...
```

From scripts/mail_manager/db.py:
```python
class MailDatabase:
    def get_email(self, message_id: str) -> Optional[dict]: ...
    def save_email(self, email_data: dict) -> None: ...
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add type annotations to CLI functions</name>
  <files>scripts/mail_cli.py</files>
  <behavior>
    - load_config returns dict
    - get_client returns MailClient
    - cmd_fetch, cmd_search, cmd_read, cmd_send, cmd_reply return None (print JSON)
    - _process_attachments returns Optional[list[str]]
    - _get_account_paths returns dict
    - _append_signature returns tuple[str, Optional[str]]
  </behavior>
  <action>
Add type annotations to CLI helper functions and command handlers.

1. Add imports:
   - from typing import Optional, List, Dict, Any

2. Annotate helper functions:
   - load_config() -> dict
   - get_client(config: dict, email_account: Optional[str] = None) -> MailClient
   - _process_attachments(attach_paths: Optional[list[str]], zip_as: Optional[str] = None) -> Optional[list[str]]
   - _get_account_paths(config: dict, email_address: str) -> dict
   - _get_template_env() -> Environment
   - _render_table(template_name: str, context: dict) -> str
   - _append_signature(body_text: str, html_body: Optional[str], signature_path: str) -> tuple[str, Optional[str]]
   - _markdown_to_html(md_text: str) -> str

3. Command handlers return None (they print JSON):
   - cmd_fetch(args, config: dict, db: MailDatabase) -> None
   - cmd_fetch_status(args, config: dict, db: MailDatabase) -> None
   - cmd_search(args, config: dict, db: MailDatabase) -> None
   - cmd_read(args, config: dict, db: MailDatabase) -> None
   - cmd_send(args, config: dict, db: MailDatabase) -> None
   - cmd_reply(args, config: dict, db: MailDatabase) -> None

DO NOT change runtime behavior. Only add annotations.
  </action>
  <verify>
    <automated>mypy scripts/mail_cli.py --ignore-missing-imports 2>&1 | grep -v "Success" || echo "mypy check passed"</automated>
  </verify>
  <done>CLI functions have type annotations; mypy passes on mail_cli.py</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Migrate CLI error handling to use error codes</name>
  <files>scripts/mail_cli.py</files>
  <behavior>
    - cmd_read returns error_response with USER_EMAIL_NOT_FOUND when email not found
    - cmd_reply returns error_response with USER_EMAIL_NOT_FOUND when email not found
    - cmd_send returns error_response with SERVER_SMTP_SEND_FAILED on exception
    - All success cases use success_response
  </behavior>
  <action>
Migrate all CLI command error responses to use error_response() and success_response() from errors.py.

1. Add import at top:
   - from mail_manager.errors import error_response, success_response, ErrorCodes

2. Replace existing error JSON patterns:

   Before:
   ```python
   print(json.dumps({"status": "error", "message": "Email not found locally"}))
   ```

   After:
   ```python
   print(json.dumps(error_response(ErrorCodes.USER_EMAIL_NOT_FOUND, "Email not found locally")))
   ```

3. Replace existing success patterns:

   Before:
   ```python
   print(json.dumps({"status": "success", "message": "Email sent"}))
   ```

   After:
   ```python
   print(json.dumps(success_response(message="Email sent")))
   ```

4. Commands to migrate:
   - cmd_fetch: Already uses status field, ensure consistent format
   - cmd_fetch_status: Use error_response for "Task not found"
   - cmd_search: Already uses status: success
   - cmd_read: Use error_response for "Email not found"
   - cmd_send: Use error_response on exception, success_response on success
   - cmd_reply: Use error_response for "Email not found"

CRITICAL: Full migration per user decision - one-time change for all commands.
  </action>
  <verify>
    <automated>grep -c "error_response\\|success_response" scripts/mail_cli.py</automated>
  </verify>
  <done>All CLI commands use error_response/success_response; no inline JSON error objects remain</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Create test_errors.py for error format tests</name>
  <files>tests/test_errors.py</files>
  <behavior>
    - Test 1: error_response returns correct structure
    - Test 2: success_response returns correct structure
    - Test 3: ErrorCodes are properly classified (USER/SERVER/BIZ)
    - Test 4: error_response message is included in output
  </behavior>
  <action>
Create tests/test_errors.py to verify error handling module works correctly.

```python
import pytest
from mail_manager.errors import ErrorCodes, error_response, success_response

class TestErrorCodes:
    """Tests for error code definitions."""
    
    def test_user_codes_start_with_user(self):
        """USER codes have USER_ prefix."""
        assert ErrorCodes.USER_EMAIL_NOT_FOUND.startswith('USER_')
        assert ErrorCodes.USER_INVALID_MESSAGE_ID.startswith('USER_')
    
    def test_server_codes_start_with_server(self):
        """SERVER codes have SERVER_ prefix."""
        assert ErrorCodes.SERVER_IMAP_CONNECTION_FAILED.startswith('SERVER_')
        assert ErrorCodes.SERVER_SMTP_SEND_FAILED.startswith('SERVER_')
    
    def test_biz_codes_start_with_biz(self):
        """BIZ codes have BIZ_ prefix."""
        assert ErrorCodes.BIZ_PERMISSION_DENIED.startswith('BIZ_')

class TestErrorResponse:
    """Tests for error_response function."""
    
    def test_error_response_has_status_error(self):
        """error_response returns status: error."""
        result = error_response(ErrorCodes.USER_EMAIL_NOT_FOUND, "Not found")
        assert result['status'] == 'error'
    
    def test_error_response_includes_code(self):
        """error_response includes error code."""
        result = error_response(ErrorCodes.USER_EMAIL_NOT_FOUND, "Not found")
        assert result['code'] == ErrorCodes.USER_EMAIL_NOT_FOUND
    
    def test_error_response_includes_message(self):
        """error_response includes message."""
        result = error_response(ErrorCodes.USER_EMAIL_NOT_FOUND, "Email not found")
        assert result['message'] == "Email not found"

class TestSuccessResponse:
    """Tests for success_response function."""
    
    def test_success_response_has_status_success(self):
        """success_response returns status: success."""
        result = success_response()
        assert result['status'] == 'success'
    
    def test_success_response_includes_message(self):
        """success_response includes default message."""
        result = success_response()
        assert result['message'] == 'Success'
    
    def test_success_response_includes_data(self):
        """success_response merges data into response."""
        result = success_response(data={'count': 5})
        assert result['count'] == 5
```
  </action>
  <verify>
    <automated>pytest tests/test_errors.py -v --tb=short 2>&1 | tail -15</automated>
  </verify>
  <done>test_errors.py exists with tests for error codes and response functions; all tests pass</done>
</task>

<task type="auto" tdd="true">
  <name>Task 4: Create test_cli.py for CLI command tests</name>
  <files>tests/test_cli.py</files>
  <behavior>
    - Test 1: cmd_read returns error for nonexistent email
    - Test 2: cmd_send returns success on valid send
    - Test 3: cmd_reply returns error for nonexistent email
    - Test 4: Error responses have consistent format
  </behavior>
  <action>
Create tests/test_cli.py with tests for CLI command handlers. Focus on critical path (reply) and error handling.

```python
import pytest
from unittest.mock import MagicMock, patch
import json
from mail_cli import (
    load_config, get_client, cmd_read, cmd_send, cmd_reply,
    _process_attachments, _get_account_paths
)
from mail_manager.errors import ErrorCodes

class TestCLIHelpers:
    """Tests for CLI helper functions."""
    
    def test_process_attachments_returns_none_for_empty(self):
        """_process_attachments returns None for no attachments."""
        result = _process_attachments(None)
        assert result is None
        
        result = _process_attachments([])
        assert result is None or len(result) == 0
    
    def test_get_account_paths_returns_dict(self):
        """_get_account_paths returns path dictionary."""
        config = {'STORAGE_ROOT': '/tmp/test'}
        result = _get_account_paths(config, 'test@example.com')
        
        assert 'root' in result
        assert 'db_path' in result
        assert 'attach_path' in result

class TestCLICommands:
    """Tests for CLI command handlers."""
    
    @pytest.fixture
    def mock_db(self):
        return MagicMock()
    
    @pytest.fixture
    def mock_config(self, test_config):
        return {
            'ACCOUNTS': {'test@example.com': test_config},
            'STORAGE_ROOT': '/tmp/test',
            'DB_PATH': '/tmp/test.db',
            'ATTACHMENT_PATH': '/tmp/attachments'
        }
    
    def test_cmd_read_returns_error_for_missing_email(self, mock_db, mock_config, capsys):
        """cmd_read returns error when email not found."""
        mock_db.get_email.return_value = None
        
        args = MagicMock()
        args.message_id = 'nonexistent@example.com'
        args.account = None
        
        with patch('mail_cli.get_client') as mock_get_client:
            mock_get_client.return_value.email = 'test@example.com'
            with patch('mail_cli.MailDatabase') as mock_db_class:
                mock_db_class.return_value.get_email.return_value = None
                cmd_read(args, mock_config, mock_db)
        
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        
        assert result['status'] == 'error'
        assert 'code' in result
    
    def test_cmd_send_returns_success(self, mock_db, mock_config, capsys):
        """cmd_send returns success on valid send."""
        args = MagicMock()
        args.to = 'recipient@example.com'
        args.subject = 'Test'
        args.body = 'Hello'
        args.attach = None
        args.zip_as = None
        args.cc = None
        args.bcc = None
        args.account = None
        args.html_body = None
        
        with patch('mail_cli.get_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.send_email.return_value = True
            mock_client.email = 'test@example.com'
            mock_get_client.return_value = mock_client
            with patch('mail_cli._get_account_paths') as mock_paths:
                mock_paths.return_value = {'signature_path': '/tmp/sig.md'}
                with patch('mail_cli._append_signature') as mock_sig:
                    mock_sig.return_value = ('Hello', None)
                    cmd_send(args, mock_config, mock_db)
        
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        
        assert result['status'] == 'success'
    
    def test_cmd_reply_returns_error_for_missing_email(self, mock_db, mock_config, capsys):
        """cmd_reply returns error when original email not found."""
        args = MagicMock()
        args.message_id = 'nonexistent@example.com'
        args.body = 'Reply text'
        args.all = False
        args.attach = None
        args.zip_as = None
        args.account = None
        
        with patch('mail_cli.get_client') as mock_get_client:
            mock_client = MagicMock()
            mock_client.email = 'test@example.com'
            mock_get_client.return_value = mock_client
            with patch('mail_cli.MailDatabase') as mock_db_class:
                mock_db_class.return_value.get_email.return_value = None
                cmd_reply(args, mock_config, mock_db)
        
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        
        assert result['status'] == 'error'
        assert result['code'] == ErrorCodes.USER_EMAIL_NOT_FOUND
```

Use capsys fixture to capture print output. Mock external dependencies.
  </action>
  <verify>
    <automated>pytest tests/test_cli.py -v --tb=short 2>&1 | tail -15</automated>
  </verify>
  <done>test_cli.py exists with tests for read, send, reply commands; all tests pass</done>
</task>

</tasks>

<verification>
After all tasks complete:
1. mypy scripts/mail_cli.py must pass
2. pytest tests/test_cli.py tests/test_errors.py must pass
3. All CLI commands must use error_response/success_response
4. No inline JSON error objects in CLI
</verification>

<success_criteria>
- mail_cli.py has type annotations on all public functions
- mail_cli.py uses error_response/success_response for all command outputs
- test_cli.py has tests for read, send, reply commands
- test_errors.py has tests for error format
- mypy passes on mail_cli.py
- pytest passes on all test files
- Error codes follow USER_xxx/SERVER_xxx/BIZ_xxx classification
</success_criteria>

<output>
After completion, create `.planning/phases/01-code-quality-foundation/05-SUMMARY.md`
</output>
