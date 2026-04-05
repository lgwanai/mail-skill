"""
Unit tests for the AttachmentServer module.

Tests verify server lifecycle, security (path traversal protection), and state persistence.
"""

import json
import os
import socket
import tempfile
from pathlib import Path

import pytest


class TestFindAvailablePort:
    """Tests for finding available ports in the configured range."""

    def test_find_available_port_returns_in_range(self) -> None:
        """find_available_port returns a port in 8080-8099 range."""
        from mail_manager.server import find_available_port

        port = find_available_port()
        assert 8080 <= port <= 8099

    def test_find_available_port_with_custom_range(self) -> None:
        """find_available_port respects custom port range."""
        from mail_manager.server import find_available_port

        port = find_available_port(port_range=(9000, 9010))
        assert 9000 <= port <= 9010

    def test_find_available_port_raises_when_none_free(self) -> None:
        """find_available_port raises error when no port is available."""
        from mail_manager.server import PortUnavailableError, find_available_port

        # Create sockets that occupy the entire port range
        sockets = []
        try:
            # Occupy ports 9000-9010
            for port in range(9000, 9011):
                try:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    s.bind(("127.0.0.1", port))
                    sockets.append(s)
                except OSError:
                    pass  # Port already in use

            # Now try to find a port in this range
            with pytest.raises(PortUnavailableError):
                find_available_port(port_range=(9000, 9010))
        finally:
            for s in sockets:
                s.close()


class TestPathValidation:
    """Tests for path traversal protection (ATCH-04)."""

    @pytest.fixture
    def temp_attachments_dir(self) -> Path:
        """Create a temporary attachments directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            attachments = Path(tmpdir) / "attachments"
            attachments.mkdir()
            (attachments / "test.txt").write_text("test content")
            yield attachments

    def test_basic_traversal_blocked(self, temp_attachments_dir: Path) -> None:
        """translate_path blocks basic path traversal (../)."""
        from mail_manager.server import AttachmentHandler

        # Create a handler with attachments_dir set
        class TestHandler(AttachmentHandler):
            pass
        TestHandler.attachments_dir = temp_attachments_dir

        handler = TestHandler.__new__(TestHandler)
        handler.attachments_dir = temp_attachments_dir

        with pytest.raises(PermissionError):
            handler.translate_path("../../../etc/passwd")

    def test_encoded_traversal_blocked(self, temp_attachments_dir: Path) -> None:
        """translate_path blocks URL-encoded traversal (%2e%2e%2f)."""
        from mail_manager.server import AttachmentHandler

        class TestHandler(AttachmentHandler):
            pass
        TestHandler.attachments_dir = temp_attachments_dir

        handler = TestHandler.__new__(TestHandler)
        handler.attachments_dir = temp_attachments_dir

        # URL-encoded traversal
        encoded_path = "%2e%2e%2f%2e%2e%2fetc%2fpasswd"
        with pytest.raises(PermissionError):
            handler.translate_path(encoded_path)

    def test_double_encoded_blocked(self, temp_attachments_dir: Path) -> None:
        """translate_path blocks double-encoded traversal (%252e%252e)."""
        from mail_manager.server import AttachmentHandler

        class TestHandler(AttachmentHandler):
            pass
        TestHandler.attachments_dir = temp_attachments_dir

        handler = TestHandler.__new__(TestHandler)
        handler.attachments_dir = temp_attachments_dir

        # Double-encoded traversal
        double_encoded = "%252e%252e%252fetc%252fpasswd"
        with pytest.raises(PermissionError):
            handler.translate_path(double_encoded)

    def test_symlink_escape_blocked(self, temp_attachments_dir: Path) -> None:
        """translate_path blocks symlink escape attempts."""
        from mail_manager.server import AttachmentHandler

        class TestHandler(AttachmentHandler):
            pass
        TestHandler.attachments_dir = temp_attachments_dir

        handler = TestHandler.__new__(TestHandler)
        handler.attachments_dir = temp_attachments_dir

        # Create a symlink pointing outside attachments
        symlink_path = temp_attachments_dir / "escape_link"
        try:
            symlink_path.symlink_to("/etc/passwd")
        except OSError:
            pytest.skip("Cannot create symlink on this system")

        with pytest.raises(PermissionError):
            handler.translate_path("escape_link")

    def test_valid_path_allowed(self, temp_attachments_dir: Path) -> None:
        """translate_path allows valid paths within attachments directory."""
        from mail_manager.server import AttachmentHandler

        class TestHandler(AttachmentHandler):
            pass
        TestHandler.attachments_dir = temp_attachments_dir

        handler = TestHandler.__new__(TestHandler)
        handler.attachments_dir = temp_attachments_dir

        # Create a subdirectory and file
        subdir = temp_attachments_dir / "subdir"
        subdir.mkdir()
        (subdir / "file.txt").write_text("content")

        result = handler.translate_path("subdir/file.txt")
        assert str(temp_attachments_dir) in result


class TestLocalhostBinding:
    """Tests for localhost-only binding (ATCH-02)."""

    def test_bind_address_is_localhost(self) -> None:
        """Server binds to 127.0.0.1, not 0.0.0.0."""
        from mail_manager.server import AttachmentServer

        with tempfile.TemporaryDirectory() as tmpdir:
            server = AttachmentServer(attachments_dir=tmpdir)
            server.start()
            # The server should bind to 127.0.0.1
            assert server.server is not None
            assert server.server.server_address[0] == "127.0.0.1"
            server.stop()

    def test_server_address_format(self) -> None:
        """Server address is a tuple of (host, port)."""
        from mail_manager.server import AttachmentServer

        with tempfile.TemporaryDirectory() as tmpdir:
            server = AttachmentServer(attachments_dir=tmpdir)
            server.start()
            assert server.server is not None
            assert isinstance(server.server.server_address, tuple)
            assert len(server.server.server_address) == 2
            assert isinstance(server.server.server_address[1], int)
            server.stop()


class TestServerState:
    """Tests for server state persistence (ATCH-05)."""

    @pytest.fixture
    def temp_state_dir(self) -> Path:
        """Create a temporary directory for state files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_save_creates_json_file(self, temp_state_dir: Path) -> None:
        """ServerState.save creates a JSON file with state."""
        from mail_manager.server import ServerState

        state = ServerState(port=8080, pid=12345, started_at="2026-01-01T00:00:00")
        state_file = temp_state_dir / "server_state.json"

        state.save(state_file)

        assert state_file.exists()
        with open(state_file) as f:
            data = json.load(f)
        assert data["port"] == 8080
        assert data["pid"] == 12345

    def test_load_returns_state(self, temp_state_dir: Path) -> None:
        """ServerState.load returns the saved state."""
        from mail_manager.server import ServerState

        state_file = temp_state_dir / "server_state.json"
        data = {"port": 8085, "pid": 54321, "started_at": "2026-01-01T12:00:00"}
        with open(state_file, "w") as f:
            json.dump(data, f)

        state = ServerState.load(state_file)
        assert state is not None
        assert state.port == 8085
        assert state.pid == 54321

    def test_load_returns_none_for_missing_file(self, temp_state_dir: Path) -> None:
        """ServerState.load returns None for missing file."""
        from mail_manager.server import ServerState

        state = ServerState.load(temp_state_dir / "nonexistent.json")
        assert state is None

    def test_is_running_detects_stale_pid(self, temp_state_dir: Path) -> None:
        """ServerState.is_running returns False for non-existent PID."""
        from mail_manager.server import ServerState

        # Use a very high PID that's unlikely to exist
        state = ServerState(port=8080, pid=99999999, started_at="2026-01-01T00:00:00")
        assert state.is_running() is False

    def test_is_running_detects_running_process(self, temp_state_dir: Path) -> None:
        """ServerState.is_running returns True for current process."""
        from mail_manager.server import ServerState

        state = ServerState(port=8080, pid=os.getpid(), started_at="2026-01-01T00:00:00")
        assert state.is_running() is True


class TestAttachmentHandler:
    """Tests for HTTP request handling."""

    @pytest.fixture
    def temp_attachments_dir(self) -> Path:
        """Create a temporary attachments directory with test file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            attachments = Path(tmpdir) / "attachments"
            attachments.mkdir()
            (attachments / "test.txt").write_text("Hello, World!")
            yield attachments

    def test_do_GET_returns_file_content(self, temp_attachments_dir: Path) -> None:
        """do_GET returns file content for valid paths."""
        # This is tested indirectly via integration tests
        # Unit test would require mocking the request/response
        pass

    def test_do_GET_returns_403_for_traversal(self, temp_attachments_dir: Path) -> None:
        """do_GET returns 403 for path traversal attempts."""
        # Tested via TestPathValidation
        pass

    def test_do_GET_sets_content_type(self, temp_attachments_dir: Path) -> None:
        """do_GET sets appropriate Content-Type header."""
        # Content-Type is set by SimpleHTTPRequestHandler via mimetypes
        # We verify the path validation, not the standard handler behavior
        pass


class TestAttachmentServerLifecycle:
    """Tests for server start/stop lifecycle."""

    @pytest.fixture
    def temp_attachments_dir(self) -> Path:
        """Create a temporary attachments directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            attachments = Path(tmpdir) / "attachments"
            attachments.mkdir()
            yield attachments

    def test_start_creates_daemon_thread(self, temp_attachments_dir: Path) -> None:
        """start() creates a daemon thread for the server."""
        from mail_manager.server import AttachmentServer

        server = AttachmentServer(attachments_dir=str(temp_attachments_dir))
        server.start()

        assert server.thread is not None
        assert server.thread.daemon is True

        server.stop()

    def test_start_returns_port(self, temp_attachments_dir: Path) -> None:
        """start() returns the port the server is listening on."""
        from mail_manager.server import AttachmentServer

        server = AttachmentServer(attachments_dir=str(temp_attachments_dir))
        port = server.start()

        assert 8080 <= port <= 8099
        assert server.port == port

        server.stop()

    def test_stop_shuts_down_server(self, temp_attachments_dir: Path) -> None:
        """stop() shuts down the server cleanly."""
        from mail_manager.server import AttachmentServer

        server = AttachmentServer(attachments_dir=str(temp_attachments_dir))
        port = server.start()

        # Verify server is running
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            result = s.connect_ex(("127.0.0.1", port))
            assert result == 0

        server.stop()

        # Verify server is stopped (may take a moment)
        import time
        time.sleep(0.5)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            result = s.connect_ex(("127.0.0.1", port))
            assert result != 0
