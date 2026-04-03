# Phase 1: Code Quality Foundation - Research

**Researched:** 2026-04-04
**Domain:** Python testing (pytest), type annotations (mypy), linting (ruff), error handling patterns
**Confidence:** HIGH

## Summary

This phase establishes the engineering foundation for safe iteration on the Mail Skill project. The codebase currently lacks tests, type annotations, consistent error handling, and linting configuration. Research covers pytest for testing with mocking strategies for IMAP/SMTP/ChromaDB dependencies, mypy for gradual type annotation, ruff for linting and formatting, and a standardized error response format for CLI commands.

**Primary recommendation:** Use pytest with pytest-mock for unit tests, mypy in relaxed mode for gradual typing, ruff as the unified linter/formatter, and a simple JSON error format with classified error codes.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Testing Strategy
- **Coverage order**: Critical paths first - fetch, search, send, reply
- **Test type**: Unit tests primarily, integration tests later
- **Mock strategy**: Mock external dependencies (IMAP/SMTP/Database) for test speed
- **Coverage target**: Core modules 80%+, other modules 60%+

#### Type Annotation Strategy
- **Add order**: Core modules first - client.py, db.py, then CLI
- **Data structures**: Use `dataclass + typing`, Python native solution, no extra dependencies
- **mypy strictness**: Relaxed mode, allow partial `Any` and `# type: ignore`, gradual improvement

#### Error Code Design
- **Format**: UPPERCASE_UNDERSCORE - `EMAIL_NOT_FOUND`, `IMAP_CONNECTION_FAILED`
- **Classification**: By source
  - `USER_xxx` - Client errors (parameter errors, resource not found)
  - `SERVER_xxx` - Server errors (IMAP/SMTP connection failures)
  - `BIZ_xxx` - Business errors (permission denied, state conflicts)
- **Response structure**: Simple unified format
  ```json
  {
    "status": "error",
    "code": "EMAIL_NOT_FOUND",
    "message": "Email with message_id 'xxx' not found"
  }
  ```
- **Migration strategy**: Full migration, one-time change for all commands

#### Linter Configuration
- **Rule set**: PEP 8 standard, no controversial rules
- **Trigger**: Auto-format on save
- **Config location**: `pyproject.toml`

### Claude's Discretion

- Specific test case design
- Type annotation style (Optional vs Union)
- Specific error code naming (within classification framework)

### Deferred Ideas (OUT OF SCOPE)

None - discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| QUAL-01 | Project test coverage 80%+, critical paths (fetch, search, send, reply) have complete tests | pytest + pytest-mock for mocking IMAP/SMTP/ChromaDB; coverage.py for measurement |
| QUAL-02 | All Python files add type annotations, pass mypy type check | mypy in relaxed mode with pyproject.toml config; dataclasses for data structures |
| QUAL-03 | Unified error handling format, all commands return standard JSON structure | Error code classification system; simple response envelope pattern |
| QUAL-04 | Use ruff for code formatting and lint, follow PEP 8 spec | ruff as unified linter/formatter in pyproject.toml |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | >=7.4.0 | Testing framework | Industry standard, rich plugin ecosystem, fixture support |
| pytest-cov | >=4.1.0 | Coverage measurement | Integrated with pytest, produces XML/HTML reports |
| pytest-mock | >=3.11.0 | Mocking utilities | Simple wrapper around unittest.mock, pytest-friendly |
| mypy | >=1.5.0 | Static type checking | Most mature Python type checker |
| ruff | >=0.1.0 | Linting + formatting | 10-100x faster than flake8/black, unified tool |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-asyncio | >=0.21.0 | Async test support | If async code is added later |
| freezegun | >=1.2.0 | Date/time mocking | For date-related tests |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pytest | unittest | unittest is stdlib but lacks fixtures, parametrize, rich plugins |
| mypy | pyright | pyright is faster but mypy has better Python ecosystem integration |
| ruff | black + flake8 + isort | ruff is unified and 10-100x faster, single tool to configure |

**Installation:**
```bash
pip install pytest pytest-cov pytest-mock mypy ruff
```

**Dev dependencies (add to requirements.txt or create requirements-dev.txt):**
```
# requirements-dev.txt
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-mock>=3.11.0
mypy>=1.5.0
ruff>=0.1.0
```

## Architecture Patterns

### Recommended Project Structure
```
mail-skill/
├── scripts/
│   ├── mail_cli.py           # CLI entry point (999 lines - needs refactoring)
│   └── mail_manager/
│       ├── __init__.py
│       ├── client.py         # MailClient - IMAP/SMTP operations
│       └── db.py             # MailDatabase - SQLite + ChromaDB
├── tests/
│   ├── __init__.py
│   ├── conftest.py           # Shared fixtures
│   ├── test_client.py        # MailClient unit tests
│   ├── test_db.py            # MailDatabase unit tests
│   └── test_cli.py           # CLI command tests
├── pyproject.toml            # Tool configuration (NEW)
├── requirements.txt          # Production dependencies
└── requirements-dev.txt      # Development dependencies (NEW)
```

### Pattern 1: Pytest Fixture for Mocking
**What:** Create reusable fixtures for external dependencies
**When to use:** All tests that touch IMAP, SMTP, SQLite, or ChromaDB
**Example:**
```python
# tests/conftest.py
import pytest
from unittest.mock import MagicMock, patch
import tempfile
import os

@pytest.fixture
def mock_imap_mailbox():
    """Mock imap_tools.MailBox for unit testing."""
    with patch('mail_manager.client.MailBox') as mock:
        mailbox_instance = MagicMock()
        mock.return_value.__enter__ = MagicMock(return_value=mailbox_instance)
        mock.return_value.__exit__ = MagicMock(return_value=False)
        yield mailbox_instance

@pytest.fixture
def temp_db_path():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        path = f.name
    yield path
    os.unlink(path)

@pytest.fixture
def mock_chroma_collection():
    """Mock ChromaDB collection for vector search tests."""
    with patch('chromadb.PersistentClient') as mock_client:
        mock_collection = MagicMock()
        mock_client.return_value.get_or_create_collection.return_value = mock_collection
        yield mock_collection

@pytest.fixture
def sample_email_data():
    """Sample email data for tests."""
    return {
        'message_id': 'test-msg-123@example.com',
        'imap_uid': '12345',
        'account': 'test@example.com',
        'subject': 'Test Subject',
        'sender': 'sender@example.com',
        'recipient': 'recipient@example.com',
        'date': '2024-01-15T10:30:00',
        'body_text': 'Test email body',
        'is_read': False,
        'is_starred': False,
        'folder': 'INBOX',
        'attachments': []
    }
```

### Pattern 2: Dataclass for Type Annotations
**What:** Use Python dataclasses for structured data with type hints
**When to use:** Email data, configuration objects, API responses
**Example:**
```python
# scripts/mail_manager/models.py (NEW FILE)
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime

@dataclass
class EmailData:
    """Represents an email with all its metadata."""
    message_id: str
    subject: str
    sender: str
    recipient: str
    date: datetime
    body_text: str
    account: str
    imap_uid: Optional[str] = None
    thread_id: Optional[str] = None
    in_reply_to: Optional[str] = None
    references: Optional[str] = None
    cc: Optional[str] = None
    html_body: Optional[str] = None
    has_attachment: bool = False
    is_read: bool = False
    is_starred: bool = False
    folder: str = 'INBOX'
    attachments: List['Attachment'] = field(default_factory=list)

@dataclass
class Attachment:
    """Represents an email attachment."""
    filename: str
    content_type: str
    size: int
    local_path: Optional[str] = None

@dataclass
class CommandResult:
    """Standard response format for CLI commands."""
    status: str  # 'success' or 'error'
    code: Optional[str] = None
    message: Optional[str] = None
    data: Optional[dict] = None
    
    def to_dict(self) -> dict:
        result = {'status': self.status}
        if self.code:
            result['code'] = self.code
        if self.message:
            result['message'] = self.message
        if self.data:
            result.update(self.data)
        return result
```

### Pattern 3: Error Code Classification
**What:** Centralized error code definitions with clear categorization
**When to use:** All CLI commands that can fail
**Example:**
```python
# scripts/mail_manager/errors.py (NEW FILE)
from dataclasses import dataclass
from typing import Optional

class ErrorCodes:
    """Centralized error code definitions."""
    
    # USER_xxx - Client errors (4xx equivalent)
    EMAIL_NOT_FOUND = 'USER_EMAIL_NOT_FOUND'
    INVALID_MESSAGE_ID = 'USER_INVALID_MESSAGE_ID'
    MISSING_PARAMETER = 'USER_MISSING_PARAMETER'
    INVALID_PARAMETER = 'USER_INVALID_PARAMETER'
    
    # SERVER_xxx - Server errors (5xx equivalent)
    IMAP_CONNECTION_FAILED = 'SERVER_IMAP_CONNECTION_FAILED'
    SMTP_CONNECTION_FAILED = 'SERVER_SMTP_CONNECTION_FAILED'
    SMTP_SEND_FAILED = 'SERVER_SMTP_SEND_FAILED'
    DATABASE_ERROR = 'SERVER_DATABASE_ERROR'
    CHROMADB_ERROR = 'SERVER_CHROMADB_ERROR'
    
    # BIZ_xxx - Business logic errors
    EMAIL_ALREADY_SENT = 'BIZ_EMAIL_ALREADY_SENT'
    PERMISSION_DENIED = 'BIZ_PERMISSION_DENIED'
    ACCOUNT_NOT_CONFIGURED = 'BIZ_ACCOUNT_NOT_CONFIGURED'

@dataclass
class ErrorResponse:
    """Standard error response structure."""
    status: str = 'error'
    code: str
    message: str
    
    def to_json(self) -> str:
        import json
        return json.dumps({
            'status': self.status,
            'code': self.code,
            'message': self.message
        }, ensure_ascii=False)

def error_response(code: str, message: str) -> dict:
    """Helper function to create error responses."""
    return {
        'status': 'error',
        'code': code,
        'message': message
    }

def success_response(data: Optional[dict] = None, message: str = 'Success') -> dict:
    """Helper function to create success responses."""
    result = {'status': 'success'}
    if data:
        result.update(data)
    if message:
        result['message'] = message
    return result
```

### Anti-Patterns to Avoid
- **Testing with real network calls:** Tests become slow, flaky, and require credentials
- **Partial error migration:** Mixing old and new error formats confuses agents
- **Over-typing too early:** Strict mypy settings block progress; start relaxed
- **Testing implementation details:** Test behavior, not internal structure

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Mock IMAP server | Custom mock classes | pytest-mock + unittest.mock.patch | imap-tools already testable with mocks |
| Error JSON serialization | Custom to_json methods | dataclass + json.dumps | Standard library handles edge cases |
| Database fixtures | Manual setup/teardown | pytest fixtures with yield | Automatic cleanup, test isolation |
| Coverage reporting | Custom script | pytest-cov --cov-fail-under=80 | Industry standard, CI integration |

**Key insight:** The Python testing ecosystem is mature. Don't reinvent mocking, fixtures, or coverage - pytest plugins handle this well.

## Common Pitfalls

### Pitfall 1: Mocking at Wrong Level
**What goes wrong:** Mocking `imaplib` directly instead of `imap_tools.MailBox`
**Why it happens:** Developers think deeper mocking is better
**How to avoid:** Mock at the library boundary (imap_tools), not the stdlib
**Warning signs:** Tests pass but production fails; complex mock setup

### Pitfall 2: Type Annotations Break Runtime
**What goes wrong:** Using `list[Email]` instead of `List[Email]` for Python 3.8 compatibility
**Why it happens:** Python 3.9+ allows lowercase generics
**How to avoid:** Use `from __future__ import annotations` or stick to `typing.List`
**Warning signs:** SyntaxError on older Python versions

### Pitfall 3: Inconsistent Error Format
**What goes wrong:** Some commands return `{"error": "..."}` others return `{"status": "error"}`
**Why it happens:** Gradual changes without migration plan
**How to avoid:** Use helper functions (`error_response()`, `success_response()`) consistently
**Warning signs:** Different CLI commands have different JSON shapes

### Pitfall 4: Coverage Gaps in Mocked Tests
**What goes wrong:** High coverage number but untested branches
**Why it happens:** Mocks don't exercise all code paths
**How to avoid:** Review coverage report for uncovered branches; add edge case tests
**Warning signs:** 80% coverage but bugs in production

## Code Examples

### Pytest Configuration (pyproject.toml)
```toml
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "-v",
    "--tb=short",
    "--cov=scripts",
    "--cov-report=term-missing",
    "--cov-fail-under=60",  # Start at 60%, work up to 80%
]
filterwarnings = [
    "ignore::DeprecationWarning",
]

[tool.coverage.run]
source = ["scripts"]
omit = [
    "scripts/mail_cli.py",  # CLI entry, tested via integration tests
    "*/__pycache__/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if __name__ == .__main__.:",
    "raise NotImplementedError",
]
```

### Mypy Configuration (pyproject.toml)
```toml
[tool.mypy]
python_version = "3.8"
warn_return_any = false  # Relaxed: allow Any returns
warn_unused_configs = true
disallow_untyped_defs = false  # Relaxed: gradual typing
disallow_incomplete_defs = false
check_untyped_defs = true
ignore_missing_imports = true  # For libraries without stubs

[[tool.mypy.overrides]]
module = [
    "imap_tools.*",
    "chromadb.*",
    "sentence_transformers.*",
]
ignore_errors = true
```

### Ruff Configuration (pyproject.toml)
```toml
[tool.ruff]
line-length = 100
target-version = "py38"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "UP",  # pyupgrade
]
ignore = [
    "E501",  # line too long (handled by formatter)
    "B008",  # function call in default argument
    "C901",  # too complex (we have legacy code)
]

[tool.ruff.lint.isort]
known-first-party = ["mail_manager"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

### Sample Unit Test for MailClient
```python
# tests/test_client.py
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from mail_manager.client import MailClient

class TestMailClient:
    """Unit tests for MailClient class."""
    
    @pytest.fixture
    def client(self):
        """Create a MailClient with test config."""
        config = {
            'EMAIL': 'test@example.com',
            'PASSWORD': 'test_password',
            'IMAP_SERVER': 'imap.example.com',
            'IMAP_PORT': '993',
            'SMTP_SERVER': 'smtp.example.com',
            'SMTP_PORT': '465',
            'USE_SSL': 'true'
        }
        return MailClient(config)
    
    @pytest.fixture
    def mock_mailbox(self):
        """Mock imap_tools.MailBox."""
        with patch('mail_manager.client.MailBox') as mock:
            instance = MagicMock()
            mock.return_value.__enter__ = MagicMock(return_value=instance)
            mock.return_value.__exit__ = MagicMock(return_value=False)
            yield instance
    
    def test_init_sets_email_and_password(self, client):
        """Test that client initializes with config."""
        assert client.email == 'test@example.com'
        assert client.password == 'test_password'
    
    def test_fetch_emails_returns_list(self, client, mock_mailbox, sample_email_data):
        """Test that fetch_emails returns email data."""
        # Setup mock message
        mock_msg = MagicMock()
        mock_msg.uid = '12345'
        mock_msg.subject = 'Test Subject'
        mock_msg.from_ = 'sender@example.com'
        mock_msg.to = ['recipient@example.com']
        mock_msg.cc = []
        mock_msg.date = datetime(2024, 1, 15, 10, 30)
        mock_msg.text = 'Test body'
        mock_msg.html = None
        mock_msg.attachments = []
        mock_msg.flags = []
        mock_msg.headers = {'message-id': ('test-msg-id',)}
        
        mock_mailbox.fetch.return_value = [mock_msg]
        
        # Execute
        results = client.fetch_emails(folder='INBOX', limit=10)
        
        # Verify
        assert len(results) == 1
        assert results[0]['subject'] == 'Test Subject'
    
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
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| flake8 + black + isort | ruff (unified) | 2023+ | 10-100x faster, single config file |
| unittest + nose | pytest | 2015+ | Fixtures, parametrize, better assertions |
| runtime type checking | mypy static analysis | 2018+ | Catch bugs before runtime |
| ad-hoc error messages | structured error codes | Industry standard | Better debugging, agent-friendly |

**Deprecated/outdated:**
- `nose` test runner: Use pytest instead
- `pyflakes` standalone: Integrated into ruff
- `pylint` for style: Ruff covers most PEP 8 rules faster

## Open Questions

1. **Should we create a `models.py` file for dataclasses?**
   - What we know: Dataclasses provide type safety and clarity
   - What's unclear: Whether to put them in existing files or new file
   - Recommendation: Create `scripts/mail_manager/models.py` for cleaner organization

2. **How to handle ChromaDB embedding model in tests?**
   - What we know: ChromaDB loads models on first search
   - What's unclear: Whether to mock entirely or use tiny test model
   - Recommendation: Mock ChromaDB entirely for unit tests; integration tests can use real DB

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 7.4+ |
| Config file | pyproject.toml (to be created) |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ --cov=scripts --cov-report=term-missing` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| QUAL-01 | Test coverage 80%+ | unit+coverage | `pytest --cov-fail-under=80` | Wave 0 |
| QUAL-01 | fetch has tests | unit | `pytest tests/test_client.py::TestMailClient::test_fetch_emails -v` | Wave 0 |
| QUAL-01 | search has tests | unit | `pytest tests/test_db.py::TestMailDatabase::test_search_fts -v` | Wave 0 |
| QUAL-01 | send has tests | unit | `pytest tests/test_client.py::TestMailClient::test_send_email -v` | Wave 0 |
| QUAL-01 | reply has tests | unit | `pytest tests/test_cli.py::TestCLI::test_cmd_reply -v` | Wave 0 |
| QUAL-02 | mypy passes | static | `mypy scripts/` | N/A (tool) |
| QUAL-03 | error format consistent | unit | `pytest tests/test_errors.py -v` | Wave 0 |
| QUAL-04 | ruff passes | static | `ruff check scripts/` | N/A (tool) |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q` (quick, fail-fast)
- **Per wave merge:** `pytest tests/ --cov=scripts --cov-report=term-missing`
- **Phase gate:** `pytest --cov-fail-under=80 && mypy scripts/ && ruff check scripts/`

### Wave 0 Gaps
- [ ] `tests/conftest.py` - shared fixtures (mock_mailbox, temp_db_path, sample_email_data)
- [ ] `tests/test_client.py` - MailClient unit tests
- [ ] `tests/test_db.py` - MailDatabase unit tests
- [ ] `tests/test_cli.py` - CLI command tests
- [ ] `tests/test_errors.py` - Error format tests
- [ ] `pyproject.toml` - pytest, mypy, ruff configuration
- [ ] `requirements-dev.txt` - development dependencies

## Sources

### Primary (HIGH confidence)
- Python documentation - dataclasses, typing module
- pytest documentation patterns - fixtures, mocking best practices
- mypy configuration options - gradual typing settings
- ruff documentation - pyproject.toml configuration

### Secondary (MEDIUM confidence)
- Real Python pytest guides - fixture patterns, test organization
- Python testing community practices - coverage targets, mocking strategies

### Tertiary (LOW confidence)
- None - all core recommendations based on official documentation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - pytest, mypy, ruff are industry standards with mature ecosystems
- Architecture: HIGH - patterns derived from official documentation and community best practices
- Pitfalls: HIGH - based on common issues seen in Python testing projects

**Research date:** 2026-04-04
**Valid until:** 2026-10-04 (6 months - stable tooling)
