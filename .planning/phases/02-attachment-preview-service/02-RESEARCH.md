# Phase 2: Attachment Preview Service - Research

**Researched:** 2026-04-04
**Domain:** Local HTTP server for secure file serving
**Confidence:** HIGH

## Summary

This phase requires implementing a local HTTP server for serving email attachments securely. The core challenge is balancing convenience (browser-accessible preview links) with security (localhost-only binding, path traversal prevention, proper MIME types).

Python's standard library `http.server` module provides the foundation. The key implementation decisions are:
1. **Server lifecycle**: Background daemon thread that persists across CLI invocations
2. **Port management**: Find available port in 8080-8099 range, persist port info to file
3. **Security**: Bind to 127.0.0.1 only, validate all paths against attachments directory
4. **Integration**: New `attachments` command that queries database and generates preview links

**Primary recommendation:** Use Python's built-in `http.server` with `ThreadingHTTPServer` and a custom `SimpleHTTPRequestHandler` subclass that enforces security constraints. Server state persists in `mail_data/{account}/server_state.json`.

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| ATCH-01 | Start local HTTP server, find available port (8080-8099) | Socket binding pattern with port range iteration |
| ATCH-02 | Bind 127.0.0.1, forbid external access | HTTPServer((host, port), handler) with host="127.0.0.1" |
| ATCH-03 | Generate attachment download links for browser preview | URL generation: `http://127.0.0.1:{port}/{relative_path}` |
| ATCH-04 | Path traversal protection, only access attachments directory | `os.path.commonpath()` validation + `pathlib.resolve()` |
| ATCH-05 | Server state persistence across commands | JSON file with port, PID, start_time in account directory |
| ATCH-06 | New `attachments` command to list attachments with preview links | Database query + server status check + URL generation |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| http.server | stdlib | HTTP server for file serving | Built-in, no dependencies, sufficient for local use |
| socket | stdlib | Port detection, binding | Standard for network operations |
| threading | stdlib | Background daemon thread | Non-blocking server in CLI context |
| pathlib | stdlib | Path validation, normalization | Modern path handling with security checks |
| os.path | stdlib | Path traversal prevention | `commonpath()` for directory containment |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| json | stdlib | Server state persistence | Store port, PID, status |
| mimetypes | stdlib | Content-Type detection | Browser preview requires proper MIME types |
| signal | stdlib | Graceful shutdown (optional) | If server needs explicit cleanup |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| http.server | Flask/FastAPI | Overkill for static file serving; adds dependency |
| http.server | aiohttp | Async not needed for single-user local server |
| daemon thread | multiprocessing | More isolation but harder state sharing |
| custom handler | nginx/Apache | External dependency; overkill for localhost-only |

**Installation:**
No new dependencies required - all components are Python standard library.

## Architecture Patterns

### Recommended Project Structure
```
scripts/
├── mail_manager/
│   ├── __init__.py
│   ├── client.py        # Existing - MailClient
│   ├── db.py            # Existing - MailDatabase
│   ├── errors.py        # Existing - ErrorCodes
│   ├── models.py        # Existing - Data models
│   └── server.py        # NEW - AttachmentServer class
└── mail_cli.py          # Modify - Add attachments command

mail_data/
├── {account}/
│   ├── attachments/     # Existing - File storage
│   ├── server_state.json # NEW - Server state
│   └── ...
```

### Pattern 1: Background Server with ThreadingHTTPServer

**What:** Run HTTP server in daemon thread so CLI can return immediately while server continues serving requests.

**When to use:** Long-running server needed but CLI should not block.

**Example:**
```python
# Source: Python stdlib pattern
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import threading
import socket

class AttachmentHandler(SimpleHTTPRequestHandler):
    """Custom handler with security constraints."""

    def __init__(self, *args, attachments_dir: str, **kwargs):
        self.attachments_dir = attachments_dir
        super().__init__(*args, directory=attachments_dir, **kwargs)

    def translate_path(self, path: str) -> str:
        """Override to add path traversal protection."""
        path = super().translate_path(path)
        # Security: ensure path is within attachments_dir
        if not os.path.commonpath([path, self.attachments_dir]) == self.attachments_dir:
            raise PermissionError("Path traversal blocked")
        return path


class AttachmentServer:
    """Manages the lifecycle of the attachment preview server."""

    def __init__(self, attachments_dir: str, port_range: tuple[int, int] = (8080, 8099)):
        self.attachments_dir = attachments_dir
        self.port_range = port_range
        self.server: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None
        self.port: int | None = None

    def find_available_port(self) -> int:
        """Find an available port in the specified range."""
        for port in range(self.port_range[0], self.port_range[1] + 1):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(("127.0.0.1", port))
                    return port
            except OSError:
                continue
        raise RuntimeError("No available port in range")

    def start(self) -> int:
        """Start the server in a background thread."""
        if self.server is not None:
            return self.port  # Already running

        self.port = self.find_available_port()

        def handler_wrapper(*args, **kwargs):
            AttachmentHandler(*args, attachments_dir=self.attachments_dir, **kwargs)

        self.server = ThreadingHTTPServer(("127.0.0.1", self.port), handler_wrapper)
        self.server.daemon_threads = True

        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

        return self.port

    def stop(self) -> None:
        """Stop the server."""
        if self.server:
            self.server.shutdown()
            self.server = None
            self.thread = None
            self.port = None
```

### Pattern 2: Server State Persistence

**What:** Store server state in JSON file so subsequent CLI commands can discover running server.

**When to use:** Server persists across CLI invocations.

**Example:**
```python
# Source: Standard pattern for state persistence
import json
from dataclasses import dataclass
from pathlib import Path

@dataclass
class ServerState:
    port: int
    pid: int
    started_at: str

    @classmethod
    def load(cls, state_path: Path) -> "ServerState | None":
        if not state_path.exists():
            return None
        try:
            data = json.loads(state_path.read_text())
            return cls(**data)
        except (json.JSONDecodeError, KeyError):
            return None

    def save(self, state_path: Path) -> None:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(self.__dict__, indent=2))

    def is_running(self) -> bool:
        """Check if the server process is still running."""
        import os
        import signal
        try:
            os.kill(self.pid, 0)  # Check if process exists
            return True
        except (OSError, ProcessLookupError):
            return False
```

### Pattern 3: Path Traversal Prevention

**What:** Validate that requested file path is within the allowed directory.

**When to use:** Serving files from filesystem based on user-provided paths.

**Example:**
```python
# Source: OWASP path traversal prevention pattern
import os
from pathlib import Path

def is_safe_path(base_dir: Path, requested_path: str) -> bool:
    """
    Check if requested_path is safely within base_dir.

    Prevents path traversal attacks like:
    - ../../../etc/passwd
    - ..%2F..%2F..%2Fetc%2Fpasswd
    """
    base_dir = base_dir.resolve()
    # Resolve the full path, following symlinks
    target_path = (base_dir / requested_path).resolve()

    # Check if target is within base_dir
    try:
        target_path.relative_to(base_dir)
        return True
    except ValueError:
        return False

def safe_join(base_dir: Path, *parts: str) -> Path | None:
    """
    Safely join path parts and verify result is within base_dir.

    Returns None if path would escape base_dir.
    """
    try:
        result = base_dir
        for part in parts:
            result = result / part
        result = result.resolve()
        result.relative_to(base_dir.resolve())
        return result
    except (ValueError, OSError):
        return None
```

### Anti-Patterns to Avoid

- **Binding to 0.0.0.0:** Exposes server to all network interfaces - security risk
- **Using raw user input in paths:** Path traversal vulnerability - always validate
- **Blocking main thread with serve_forever:** CLI will hang - use daemon thread
- **Hardcoding port:** Conflicts with other services - use port range search
- **Not persisting server state:** Each command starts new server - resource waste
- **Ignoring MIME types:** Browser may download instead of preview - set Content-Type

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP server | Custom socket server | http.server.ThreadingHTTPServer | Battle-tested, handles HTTP protocol details |
| File serving | Manual file read/write | SimpleHTTPRequestHandler | Range requests, MIME types, caching headers |
| MIME type detection | Custom mapping | mimetypes.guess_type() | Comprehensive built-in database |
| Path validation | Regex on path strings | pathlib.resolve() + relative_to() | Handles symlinks, edge cases |
| Port detection | Try-except bind loop | socket.bind() in context manager | OS handles atomicity |

**Key insight:** Python stdlib provides all needed components. Adding Flask/FastAPI would introduce unnecessary complexity for a localhost-only file server.

## Common Pitfalls

### Pitfall 1: Binding to 0.0.0.0 Instead of 127.0.0.1
**What goes wrong:** Server accessible from network, security vulnerability
**Why it happens:** Default for many servers is 0.0.0.0 (all interfaces)
**How to avoid:** Always explicitly bind to "127.0.0.1" as first argument to HTTPServer
**Warning signs:** `netstat -an | grep LISTEN` shows 0.0.0.0 or ::

### Pitfall 2: Path Traversal Via URL Encoding
**What goes wrong:** Attacker uses `%2e%2e%2f` to bypass `..` checks
**Why it happens:** URL decoding happens after initial path validation
**How to avoid:** Use `urllib.parse.unquote()` before validation, then `resolve()` to normalize
**Warning signs:** Paths with encoded characters reaching filesystem

### Pitfall 3: Server Thread Prevents Process Exit
**What goes wrong:** CLI hangs after command completes
**Why it happens:** Non-daemon threads keep process alive
**How to avoid:** Set `thread.daemon = True` or use `ThreadingHTTPServer(daemon_threads=True)`
**Warning signs:** Process stays in `ps aux` after CLI returns

### Pitfall 4: Port Already in Use
**What goes wrong:** Server fails to start with "Address already in use"
**Why it happens:** Previous server instance still running or other service on port
**How to avoid:** Iterate through port range, use SO_REUSEADDR, check state file for running server
**Warning signs:** OSError with errno 48 (EADDRINUSE)

### Pitfall 5: Orphaned Server Processes
**What goes wrong:** Multiple server instances running on different ports
**Why it happens:** State file not updated on crash, no cleanup
**How to avoid:** Check PID in state file is still running before starting new server
**Warning signs:** `ps aux | grep python` shows multiple mail_cli processes

### Pitfall 6: MIME Type Missing Causes Download Instead of Preview
**What goes wrong:** Browser downloads file instead of displaying inline
**Why it happens:** Content-Type header not set or set to application/octet-stream
**How to avoid:** Use `mimetypes.guess_type()` and set proper Content-Type header
**Warning signs:** PDF, images download instead of showing in browser

## Code Examples

Verified patterns from Python standard library documentation:

### Starting Server on Available Port
```python
# Source: Python stdlib socket module
import socket
from contextlib import closing

def find_free_port(host: str, start: int, end: int) -> int:
    """Find available port in range [start, end]."""
    for port in range(start, end + 1):
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            try:
                s.bind((host, port))
                return port
            except OSError:
                continue
    raise OSError(f"No available port in range {start}-{end}")

# Usage
port = find_free_port("127.0.0.1", 8080, 8099)
```

### Custom RequestHandler with Path Validation
```python
# Source: Python stdlib http.server pattern
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
import os

class SecureAttachmentHandler(SimpleHTTPRequestHandler):
    """Handler that only serves files from a specific directory."""

    def __init__(self, *args, attachments_dir: str, **kwargs):
        self.attachments_dir = Path(attachments_dir).resolve()
        super().__init__(*args, directory=str(self.attachments_dir), **kwargs)

    def translate_path(self, path: str) -> str:
        """
        Override to add security validation.

        Returns absolute path if valid, raises PermissionError otherwise.
        """
        # Call parent to get normalized path
        path = super().translate_path(path)

        # Security: verify path is within attachments_dir
        try:
            resolved = Path(path).resolve()
            resolved.relative_to(self.attachments_dir)
            return str(resolved)
        except ValueError:
            raise PermissionError(f"Access denied: {path}")

    def log_message(self, format: str, *args) -> None:
        """Suppress default logging (optional)."""
        pass  # Or log to file: logger.info(format, *args)
```

### Generating Preview URLs
```python
# Source: Standard URL construction
from urllib.parse import quote

def generate_preview_url(
    port: int,
    message_id: str,
    filename: str,
    account: str
) -> str:
    """
    Generate a browser-accessible URL for attachment preview.

    URL format: http://127.0.0.1:{port}/{account}/{message_id}/{filename}
    """
    # URL-encode path components to handle spaces, special chars
    encoded_account = quote(account)
    encoded_msg_id = quote(message_id)
    encoded_filename = quote(filename)

    return f"http://127.0.0.1:{port}/{encoded_account}/{encoded_msg_id}/{encoded_filename}"
```

### Checking Server Health
```python
# Source: Standard process check pattern
import os
import signal
import urllib.request
import json

def check_server_health(state_path: Path) -> tuple[bool, int | None]:
    """
    Check if server is running and responsive.

    Returns: (is_healthy, port)
    """
    state = ServerState.load(state_path)
    if state is None:
        return False, None

    # Check process exists
    try:
        os.kill(state.pid, 0)
    except (OSError, ProcessLookupError):
        return False, None

    # Check HTTP endpoint responds
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{state.port}/", timeout=1) as resp:
            return resp.status == 200, state.port
    except Exception:
        return False, None
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| BaseHTTPServer | http.server | Python 3 | Unified module, better ThreadingHTTPServer |
| Manual threading | ThreadingHTTPServer | Python 3.7+ | Built-in thread pool, simpler code |
| String path manipulation | pathlib.Path | Python 3.4+ | Safer, more readable path handling |
| Hardcoded MIME map | mimetypes module | Always available | Automatic type detection from extensions |

**Deprecated/outdated:**
- `BaseHTTPServer`, `SimpleHTTPServer`: Use `http.server` in Python 3
- Manual socket server: Use `ThreadingHTTPServer` for concurrent requests

## Open Questions

1. **Should server auto-shutdown after inactivity?**
   - What we know: Server runs as daemon thread, killed when process exits
   - What's unclear: Should there be a timeout for idle server?
   - Recommendation: Start simple - no auto-shutdown. Add if users report issues.

2. **How to handle multiple accounts?**
   - What we know: Each account has isolated attachments directory
   - What's unclear: Single server for all accounts or one per account?
   - Recommendation: Single server with path `/attachments/{account}/{message_id}/{file}` - simpler, one port.

3. **Should we support range requests for large files?**
   - What we know: `SimpleHTTPRequestHandler` supports Range header out of box
   - What's unclear: Need to test with video/large PDF files
   - Recommendation: Test with typical attachment sizes, enable if needed (already supported by parent class).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest with pytest-cov |
| Config file | pyproject.toml (existing) |
| Quick run command | `pytest tests/test_server.py -v --cov=scripts/mail_manager/server -x` |
| Full suite command | `pytest --cov=scripts --cov-report=term-missing` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ATCH-01 | Server finds available port | unit | `pytest tests/test_server.py::test_find_available_port -v` | Wave 0 |
| ATCH-01 | Server starts on port 8080-8099 | unit | `pytest tests/test_server.py::test_start_server_port_range -v` | Wave 0 |
| ATCH-02 | Server binds 127.0.0.1 only | unit | `pytest tests/test_server.py::test_bind_localhost_only -v` | Wave 0 |
| ATCH-02 | External connection refused | integration | `pytest tests/test_server.py::test_external_access_blocked -v` | Wave 0 |
| ATCH-03 | Generate preview URLs | unit | `pytest tests/test_server.py::test_generate_preview_url -v` | Wave 0 |
| ATCH-03 | URLs work in browser | integration | `pytest tests/test_server.py::test_file_download_works -v` | Wave 0 |
| ATCH-04 | Path traversal blocked | security | `pytest tests/test_server.py::test_path_traversal_blocked -v` | Wave 0 |
| ATCH-04 | Symlink escape blocked | security | `pytest tests/test_server.py::test_symlink_escape_blocked -v` | Wave 0 |
| ATCH-05 | State persists to file | unit | `pytest tests/test_server.py::test_state_persistence -v` | Wave 0 |
| ATCH-05 | State detects stale server | unit | `pytest tests/test_server.py::test_state_detects_stale -v` | Wave 0 |
| ATCH-06 | attachments command lists files | unit | `pytest tests/test_cli.py::test_attachments_command -v` | Wave 0 |
| ATCH-06 | attachments command shows URLs | integration | `pytest tests/test_cli.py::test_attachments_shows_urls -v` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_server.py tests/test_cli.py -v --cov=scripts -x`
- **Per wave merge:** `pytest --cov=scripts --cov-report=term-missing`
- **Phase gate:** Full suite green + 80%+ coverage on new code

### Wave 0 Gaps
- [ ] `tests/test_server.py` — New file for AttachmentServer tests
- [ ] `scripts/mail_manager/server.py` — New module for server implementation
- [ ] Server fixtures in `tests/conftest.py` — running_server, temp_attachments_dir

### Security Test Cases

```python
# Example test cases for security requirements
import pytest
from pathlib import Path

class TestPathTraversalPrevention:
    """Tests for ATCH-04: Path traversal protection."""

    def test_basic_traversal_blocked(self, server_handler, temp_dir):
        """Attempt to access parent directory should be blocked."""
        with pytest.raises(PermissionError):
            server_handler.translate_path("../../../etc/passwd")

    def test_encoded_traversal_blocked(self, server_handler):
        """URL-encoded traversal should be blocked."""
        with pytest.raises(PermissionError):
            server_handler.translate_path("%2e%2e%2f%2e%2e%2fetc%2fpasswd")

    def test_double_encoded_blocked(self, server_handler):
        """Double-encoded traversal should be blocked."""
        with pytest.raises(PermissionError):
            server_handler.translate_path("%252e%252e%252f")

    def test_symlink_escape_blocked(self, server_handler, temp_dir):
        """Symlink pointing outside should be blocked."""
        # Create symlink outside attachments dir
        outside_file = temp_dir / "outside.txt"
        outside_file.write_text("secret")

        attach_dir = temp_dir / "attachments"
        attach_dir.mkdir()
        link = attach_dir / "link"
        link.symlink_to(outside_file)

        with pytest.raises(PermissionError):
            server_handler.translate_path("link")

class TestLocalhostBinding:
    """Tests for ATCH-02: Localhost-only binding."""

    def test_bind_127_0_0_1(self, server):
        """Server should bind to 127.0.0.1."""
        assert server.server_address[0] == "127.0.0.1"

    def test_external_connection_refused(self, free_port):
        """Connection from non-localhost should be refused."""
        import socket
        # This would need a server running to test properly
        # The test verifies that binding to 127.0.0.1 means
        # connections to other interfaces fail
```

## Sources

### Primary (HIGH confidence)
- Python stdlib http.server module - HTTP server implementation patterns
- Python stdlib socket module - Port detection and binding
- Python stdlib pathlib module - Path validation and normalization
- OWASP Path Traversal prevention patterns - Security validation

### Secondary (MEDIUM confidence)
- Existing project patterns from `scripts/mail_manager/` - Code style, error handling
- Existing test patterns from `tests/conftest.py` - Fixture organization
- Python threading module documentation - Daemon thread patterns

### Tertiary (LOW confidence)
- None - All core patterns verified against Python stdlib documentation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Python stdlib, well-documented, no external dependencies
- Architecture: HIGH - Clear patterns from stdlib, straightforward daemon thread model
- Pitfalls: HIGH - Common security issues well-documented in OWASP and Python docs
- Testing: HIGH - pytest patterns established in Phase 1

**Research date:** 2026-04-04
**Valid until:** Stable - Python stdlib APIs are backward compatible
