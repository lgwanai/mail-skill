"""
Attachment server module for serving email attachments via local HTTP.

.. deprecated::
    This module is deprecated and will be removed in a future version.
    Attachment preview now uses direct file paths instead of HTTP server.
    See Phase 8 in .planning/phases/08-server/ for migration details.

Provides a secure local HTTP server that only accepts localhost connections
and prevents path traversal attacks.
"""

from __future__ import annotations

import json
import logging
import os
import socket
import threading
from dataclasses import dataclass
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote

logger = logging.getLogger(__name__)

# Default port range for the attachment server
DEFAULT_PORT_RANGE = (8080, 8099)


class PortUnavailableError(Exception):
    """Raised when no port is available in the configured range."""

    pass


@dataclass
class ServerState:
    """State of a running attachment server for persistence."""

    port: int
    pid: int
    started_at: str

    def save(self, path: Path) -> None:
        """Save state to a JSON file."""
        with open(path, "w") as f:
            json.dump({"port": self.port, "pid": self.pid, "started_at": self.started_at}, f)

    @classmethod
    def load(cls, path: Path) -> ServerState | None:
        """Load state from a JSON file. Returns None if file doesn't exist."""
        if not path.exists():
            return None
        try:
            with open(path) as f:
                data = json.load(f)
            return cls(
                port=data["port"],
                pid=data["pid"],
                started_at=data["started_at"],
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to load server state: {e}")
            return None

    def is_running(self) -> bool:
        """Check if the process with this PID is still running."""
        try:
            # Send signal 0 to check if process exists
            os.kill(self.pid, 0)
            return True
        except OSError:
            return False


def find_available_port(port_range: tuple[int, int] = DEFAULT_PORT_RANGE) -> int:
    """
    Find an available port in the given range.

    Args:
        port_range: Tuple of (start_port, end_port) inclusive.

    Returns:
        First available port in the range.

    Raises:
        PortUnavailableError: If no port is available.
    """
    start_port, end_port = port_range
    for port in range(start_port, end_port + 1):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    raise PortUnavailableError(f"No available port in range {start_port}-{end_port}")


class AttachmentHandler(SimpleHTTPRequestHandler):
    """
    HTTP request handler with path traversal protection.

    Only serves files from the configured attachments directory.
    Blocks all path traversal attempts including encoded variants.
    """

    # Class attribute set by AttachmentServer
    attachments_dir: Path

    def translate_path(self, path: str) -> str:
        """
        Translate URL path to filesystem path with security validation.

        Overrides parent to add path traversal protection.

        Raises:
            PermissionError: If path escapes attachments directory.
        """
        # Decode URL encoding (handle double-encoding)
        decoded_path = unquote(unquote(path))

        # Get the absolute path of the requested file
        # Remove leading slash
        relative_path = decoded_path.lstrip("/")

        # Construct full path
        full_path = (self.attachments_dir / relative_path).resolve()

        # Security check: ensure path is within attachments directory
        try:
            # This raises ValueError if full_path is not relative to attachments_dir
            full_path.relative_to(self.attachments_dir.resolve())
        except ValueError:
            logger.warning(f"Path traversal blocked: {path} -> {full_path}")
            raise PermissionError("Access denied: path escapes attachments directory") from None

        # Check for symlinks that point outside attachments directory
        if full_path.is_symlink():
            real_path = full_path.resolve()
            try:
                real_path.relative_to(self.attachments_dir.resolve())
            except ValueError:
                logger.warning(f"Symlink escape blocked: {full_path} -> {real_path}")
                raise PermissionError(
                    "Access denied: symlink points outside attachments directory"
                ) from None

        return str(full_path)

    def log_message(self, format: str, *args: Any) -> None:
        """Override to use our logger instead of stderr."""
        logger.info(f"{self.address_string()} - {format % args}")

    def do_GET(self) -> None:
        """Handle GET requests with security checks."""
        try:
            super().do_GET()
        except PermissionError as e:
            self.send_error(403, str(e))


class AttachmentServer:
    """
    Local HTTP server for serving email attachments.

    Security features:
    - Binds to 127.0.0.1 only (no external access)
    - Path traversal protection in AttachmentHandler
    - Runs in daemon thread for clean shutdown
    """

    def __init__(
        self,
        attachments_dir: str | Path,
        port_range: tuple[int, int] = DEFAULT_PORT_RANGE,
    ):
        """
        Initialize the attachment server.

        Args:
            attachments_dir: Directory containing attachments to serve.
            port_range: Range of ports to try (default 8080-8099).
        """
        self.attachments_dir = Path(attachments_dir).resolve()
        self.port_range = port_range
        self.server: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None
        self.port: int | None = None

    def start(self) -> int:
        """
        Start the HTTP server in a daemon thread.

        Returns:
            Port number the server is listening on.
        """
        import threading

        # Find available port
        self.port = find_available_port(self.port_range)

        # Create handler class with attachments_dir
        handler = type(
            "AttachmentHandlerWithDir",
            (AttachmentHandler,),
            {"attachments_dir": self.attachments_dir},
        )

        # Create server bound to localhost only
        self.server = ThreadingHTTPServer(("127.0.0.1", self.port), handler)
        self.server.daemon_threads = True

        # Start in daemon thread
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

        logger.info(f"Attachment server started on http://127.0.0.1:{self.port}")
        return self.port

    def stop(self) -> None:
        """Stop the HTTP server."""
        if self.server:
            self.server.shutdown()
            self.server = None
            self.thread = None
            logger.info(f"Attachment server stopped on port {self.port}")

    @staticmethod
    def get_state_file(account_dir: Path) -> Path:
        """Return the state file path for an account."""
        return account_dir / "attachment_server_state.json"

    def save_state(self, state_file: Path) -> None:
        """Save current server state to file."""
        if self.port is None:
            return
        state = ServerState(
            port=self.port,
            pid=os.getpid(),
            started_at=datetime.now().isoformat(),
        )
        state.save(state_file)

    @classmethod
    def get_running_server(
        cls, account_dir: Path, attachments_dir: Path
    ) -> AttachmentServer | None:
        """
        Check for an existing running server and return it if found.

        Returns None if no server is running or state file doesn't exist.
        """
        state_file = account_dir / "attachment_server_state.json"
        state = ServerState.load(state_file)

        if state is None:
            return None

        if not state.is_running():
            # Clean up stale state file
            state_file.unlink(missing_ok=True)
            return None

        # Return a server object with the running port
        server = cls(attachments_dir=attachments_dir)
        server.port = state.port
        # Note: We don't have the actual server/thread objects for existing server
        # This is just a reference to the running server's port
        return server
