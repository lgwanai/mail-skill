"""Configuration web server for mail-skill.

Provides a local HTTP server for web-based configuration management.
- Binds to 127.0.0.1 only (no external access)
- Dynamic port selection from a configurable range
- No authentication required (local only)
"""

from __future__ import annotations

import json
import logging
import os
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from mail_manager.config_manager import ConfigManager, get_config_manager
from mail_manager.config_db import Account

logger = logging.getLogger(__name__)

# Default port range for the config server
DEFAULT_PORT_RANGE = (8100, 8119)

# Global reference to config manager
_config_manager: ConfigManager | None = None


def get_html_template() -> str:
    """Return the HTML template for the configuration UI."""
    return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mail Skill 配置</title>
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
            color: #333;
        }
        h1 { color: #2c3e50; margin-bottom: 30px; }
        h2 { color: #34495e; border-bottom: 2px solid #3498db; padding-bottom: 10px; }

        .section {
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: 500;
            color: #555;
        }
        input[type="text"],
        input[type="password"],
        input[type="number"],
        select {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
        }
        input:focus {
            outline: none;
            border-color: #3498db;
            box-shadow: 0 0 0 2px rgba(52,152,219,0.2);
        }

        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            transition: background 0.2s;
        }
        .btn-primary {
            background: #3498db;
            color: white;
        }
        .btn-primary:hover { background: #2980b9; }
        .btn-success {
            background: #27ae60;
            color: white;
        }
        .btn-success:hover { background: #219a52; }
        .btn-danger {
            background: #e74c3c;
            color: white;
        }
        .btn-danger:hover { background: #c0392b; }
        .btn-secondary {
            background: #95a5a6;
            color: white;
        }
        .btn-secondary:hover { background: #7f8c8d; }

        .account-item {
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 6px;
            padding: 15px;
            margin-bottom: 15px;
        }
        .account-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .account-email {
            font-weight: 600;
            color: #2c3e50;
        }

        .grid-2 {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }

        .toast {
            position: fixed;
            bottom: 20px;
            right: 20px;
            padding: 15px 25px;
            border-radius: 4px;
            color: white;
            opacity: 0;
            transition: opacity 0.3s;
            z-index: 1000;
        }
        .toast.show { opacity: 1; }
        .toast.success { background: #27ae60; }
        .toast.error { background: #e74c3c; }

        .help-text {
            font-size: 12px;
            color: #7f8c8d;
            margin-top: 5px;
        }

        .password-toggle {
            position: relative;
        }
        .password-toggle input {
            padding-right: 40px;
        }
        .password-toggle button {
            position: absolute;
            right: 8px;
            top: 50%;
            transform: translateY(-50%);
            background: none;
            border: none;
            cursor: pointer;
            color: #7f8c8d;
        }
    </style>
</head>
<body>
    <h1>📧 Mail Skill 配置</h1>

    <div id="toast" class="toast"></div>

    <!-- AI Settings -->
    <div class="section">
        <h2>🤖 AI 功能配置</h2>
        <div class="form-group">
            <label for="openai_api_key">OpenAI API Key *</label>
            <input type="password" id="openai_api_key" placeholder="sk-...">
            <p class="help-text">用于 AI 回复、邮件摘要、语义搜索等功能。必填。</p>
        </div>
        <div class="grid-2">
            <div class="form-group">
                <label for="openai_api_base">API Base URL</label>
                <input type="text" id="openai_api_base" placeholder="https://api.openai.com/v1">
                <p class="help-text">可选，用于自定义 API 地址</p>
            </div>
            <div class="form-group">
                <label for="llm_model_name">LLM 模型</label>
                <input type="text" id="llm_model_name" placeholder="gpt-4o-mini">
                <p class="help-text">默认 gpt-4o-mini</p>
            </div>
        </div>
        <div class="grid-2">
            <div class="form-group">
                <label for="embedding_model_name">Embedding 模型</label>
                <input type="text" id="embedding_model_name" placeholder="text-embedding-3-small">
                <p class="help-text">用于语义搜索，默认 text-embedding-3-small</p>
            </div>
            <div class="form-group">
                <label for="reranker_model_name">Rerank 模型</label>
                <input type="text" id="reranker_model_name" placeholder="BAAI/bge-reranker-base">
                <p class="help-text">混合检索重排模型</p>
            </div>
        </div>
        <button class="btn btn-primary" onclick="saveAISettings()">保存 AI 配置</button>
    </div>

    <!-- Storage Settings -->
    <div class="section">
        <h2>💾 存储配置</h2>
        <div class="form-group">
            <label for="storage_root">存储根目录</label>
            <input type="text" id="storage_root" placeholder="./mail_data">
        </div>
        <div class="grid-2">
            <div class="form-group">
                <label for="db_path">数据库路径</label>
                <input type="text" id="db_path" placeholder="./mail_data/mail_index.db">
            </div>
            <div class="form-group">
                <label for="attachment_path">附件存储路径</label>
                <input type="text" id="attachment_path" placeholder="./mail_data/attachments">
            </div>
        </div>
        <button class="btn btn-primary" onclick="saveStorageSettings()">保存存储配置</button>
    </div>

    <!-- Email Accounts -->
    <div class="section">
        <h2>📬 邮箱账户</h2>
        <div id="accounts-list"></div>
        <button class="btn btn-success" onclick="showAddAccount()">+ 添加账户</button>
    </div>

    <!-- Add/Edit Account Modal -->
    <div id="account-modal" style="display:none; position:fixed; top:0; left:0; right:0; bottom:0; background:rgba(0,0,0,0.5); z-index:100;">
        <div style="background:white; max-width:600px; margin:50px auto; border-radius:8px; padding:20px; max-height:80vh; overflow-y:auto;">
            <h3 id="modal-title">添加邮箱账户</h3>
            <input type="hidden" id="edit_account_id">

            <div class="form-group">
                <label for="account_email">邮箱地址 *</label>
                <input type="text" id="account_email" placeholder="your@email.com">
            </div>
            <div class="form-group password-toggle">
                <label for="account_password">密码/授权码 *</label>
                <input type="password" id="account_password" placeholder="应用专用密码">
                <button type="button" onclick="togglePassword('account_password')">👁️</button>
            </div>

            <h4 style="margin-top:20px; color:#555;">IMAP 配置（收信）</h4>
            <div class="grid-2">
                <div class="form-group">
                    <label for="account_imap_server">IMAP 服务器</label>
                    <input type="text" id="account_imap_server" placeholder="imap.gmail.com">
                </div>
                <div class="form-group">
                    <label for="account_imap_port">IMAP 端口</label>
                    <input type="number" id="account_imap_port" placeholder="993" value="993">
                </div>
            </div>

            <h4 style="margin-top:20px; color:#555;">SMTP 配置（发信）</h4>
            <div class="grid-2">
                <div class="form-group">
                    <label for="account_smtp_server">SMTP 服务器</label>
                    <input type="text" id="account_smtp_server" placeholder="smtp.gmail.com">
                </div>
                <div class="form-group">
                    <label for="account_smtp_port">SMTP 端口</label>
                    <input type="number" id="account_smtp_port" placeholder="465" value="465">
                </div>
            </div>

            <div class="form-group">
                <label>
                    <input type="checkbox" id="account_use_ssl" checked> 使用 SSL
                </label>
            </div>

            <div style="margin-top:20px; display:flex; gap:10px;">
                <button class="btn btn-success" onclick="saveAccount()">保存</button>
                <button class="btn btn-secondary" onclick="closeModal()">取消</button>
            </div>
        </div>
    </div>

    <script>
        // Load settings on page load
        document.addEventListener('DOMContentLoaded', loadAllSettings);

        function showToast(message, type = 'success') {
            const toast = document.getElementById('toast');
            toast.textContent = message;
            toast.className = 'toast ' + type + ' show';
            setTimeout(() => toast.classList.remove('show'), 3000);
        }

        async function apiGet(path) {
            const res = await fetch(path);
            return res.json();
        }

        async function apiPost(path, data) {
            const res = await fetch(path, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
            return res.json();
        }

        async function apiDelete(path) {
            const res = await fetch(path, {method: 'DELETE'});
            return res.json();
        }

        async function loadAllSettings() {
            // Load AI settings
            const aiSettings = await apiGet('/api/settings');
            if (aiSettings.success) {
                const s = aiSettings.data;
                document.getElementById('openai_api_key').value = s.OPENAI_API_KEY || '';
                document.getElementById('openai_api_base').value = s.OPENAI_API_BASE || '';
                document.getElementById('llm_model_name').value = s.LLM_MODEL_NAME || '';
                document.getElementById('embedding_model_name').value = s.EMBEDDING_MODEL_NAME || '';
                document.getElementById('reranker_model_name').value = s.RERANKER_MODEL_NAME || '';
            }

            // Load storage settings
            const storageSettings = await apiGet('/api/settings');
            if (storageSettings.success) {
                const s = storageSettings.data;
                document.getElementById('storage_root').value = s.STORAGE_ROOT || './mail_data';
                document.getElementById('db_path').value = s.DB_PATH || './mail_data/mail_index.db';
                document.getElementById('attachment_path').value = s.ATTACHMENT_PATH || './mail_data/attachments';
            }

            // Load accounts
            loadAccounts();
        }

        async function saveAISettings() {
            const data = {
                OPENAI_API_KEY: document.getElementById('openai_api_key').value,
                OPENAI_API_BASE: document.getElementById('openai_api_base').value,
                LLM_MODEL_NAME: document.getElementById('llm_model_name').value,
                EMBEDDING_MODEL_NAME: document.getElementById('embedding_model_name').value,
                RERANKER_MODEL_NAME: document.getElementById('reranker_model_name').value,
            };
            const res = await apiPost('/api/settings', data);
            if (res.success) {
                showToast('AI 配置已保存');
            } else {
                showToast('保存失败: ' + res.error, 'error');
            }
        }

        async function saveStorageSettings() {
            const data = {
                STORAGE_ROOT: document.getElementById('storage_root').value,
                DB_PATH: document.getElementById('db_path').value,
                ATTACHMENT_PATH: document.getElementById('attachment_path').value,
            };
            const res = await apiPost('/api/settings', data);
            if (res.success) {
                showToast('存储配置已保存');
            } else {
                showToast('保存失败: ' + res.error, 'error');
            }
        }

        async function loadAccounts() {
            const res = await apiGet('/api/accounts');
            const container = document.getElementById('accounts-list');

            if (!res.success || !res.data.length) {
                container.innerHTML = '<p style="color:#7f8c8d;">暂无邮箱账户，请添加。</p>';
                return;
            }

            container.innerHTML = res.data.map(acc => `
                <div class="account-item">
                    <div class="account-header">
                        <span class="account-email">${acc.email}</span>
                        <div>
                            <button class="btn btn-secondary" onclick="editAccount(${acc.id})">编辑</button>
                            <button class="btn btn-danger" onclick="deleteAccount(${acc.id})">删除</button>
                        </div>
                    </div>
                    <div style="font-size:12px; color:#7f8c8d;">
                        IMAP: ${acc.imap_server}:${acc.imap_port} |
                        SMTP: ${acc.smtp_server}:${acc.smtp_port}
                    </div>
                </div>
            `).join('');
        }

        function showAddAccount() {
            document.getElementById('modal-title').textContent = '添加邮箱账户';
            document.getElementById('edit_account_id').value = '';
            document.getElementById('account_email').value = '';
            document.getElementById('account_password').value = '';
            document.getElementById('account_imap_server').value = '';
            document.getElementById('account_imap_port').value = '993';
            document.getElementById('account_smtp_server').value = '';
            document.getElementById('account_smtp_port').value = '465';
            document.getElementById('account_use_ssl').checked = true;
            document.getElementById('account-modal').style.display = 'block';
        }

        async function editAccount(id) {
            const res = await apiGet('/api/accounts/' + id);
            if (!res.success) {
                showToast('获取账户信息失败', 'error');
                return;
            }
            const acc = res.data;
            document.getElementById('modal-title').textContent = '编辑邮箱账户';
            document.getElementById('edit_account_id').value = id;
            document.getElementById('account_email').value = acc.email;
            document.getElementById('account_password').value = acc.password || '';
            document.getElementById('account_imap_server').value = acc.imap_server || '';
            document.getElementById('account_imap_port').value = acc.imap_port || 993;
            document.getElementById('account_smtp_server').value = acc.smtp_server || '';
            document.getElementById('account_smtp_port').value = acc.smtp_port || 465;
            document.getElementById('account_use_ssl').checked = acc.use_ssl !== false;
            document.getElementById('account-modal').style.display = 'block';
        }

        async function saveAccount() {
            const id = document.getElementById('edit_account_id').value;
            const data = {
                email: document.getElementById('account_email').value,
                password: document.getElementById('account_password').value,
                imap_server: document.getElementById('account_imap_server').value,
                imap_port: parseInt(document.getElementById('account_imap_port').value) || 993,
                smtp_server: document.getElementById('account_smtp_server').value,
                smtp_port: parseInt(document.getElementById('account_smtp_port').value) || 465,
                use_ssl: document.getElementById('account_use_ssl').checked,
            };

            let res;
            if (id) {
                res = await apiPost('/api/accounts/' + id, data);
            } else {
                res = await apiPost('/api/accounts', data);
            }

            if (res.success) {
                showToast(id ? '账户已更新' : '账户已添加');
                closeModal();
                loadAccounts();
            } else {
                showToast('保存失败: ' + res.error, 'error');
            }
        }

        async function deleteAccount(id) {
            if (!confirm('确定要删除这个邮箱账户吗？')) return;

            const res = await apiDelete('/api/accounts/' + id);
            if (res.success) {
                showToast('账户已删除');
                loadAccounts();
            } else {
                showToast('删除失败: ' + res.error, 'error');
            }
        }

        function closeModal() {
            document.getElementById('account-modal').style.display = 'none';
        }

        function togglePassword(inputId) {
            const input = document.getElementById(inputId);
            input.type = input.type === 'password' ? 'text' : 'password';
        }
    </script>
</body>
</html>
'''


def find_available_port(port_range: tuple[int, int] = DEFAULT_PORT_RANGE) -> int:
    """Find an available port in the given range.

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
    raise RuntimeError(f"No available port in range {start_port}-{end_port}")


class ConfigHandler(BaseHTTPRequestHandler):
    """HTTP request handler for configuration API and UI."""

    # Class attribute set by ConfigServer
    config_manager: ConfigManager

    def log_message(self, format: str, *args: Any) -> None:
        """Override to use our logger instead of stderr."""
        logger.info(f"{self.address_string()} - {format % args}")

    def send_json(self, data: dict, status: int = 200) -> None:
        """Send JSON response."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def do_GET(self) -> None:
        """Handle GET requests."""
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self.send_html()
        elif path == "/api/settings":
            self.get_settings()
        elif path.startswith("/api/accounts/"):
            account_id = int(path.split("/")[-1])
            self.get_account(account_id)
        elif path == "/api/accounts":
            self.get_accounts()
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        """Handle POST requests."""
        parsed = urlparse(self.path)
        path = parsed.path

        # Read body
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length else "{}"
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self.send_json({"success": False, "error": "Invalid JSON"}, 400)
            return

        if path == "/api/settings":
            self.update_settings(data)
        elif path == "/api/accounts":
            self.add_account(data)
        elif path.startswith("/api/accounts/"):
            account_id = int(path.split("/")[-1])
            self.update_account(account_id, data)
        else:
            self.send_error(404)

    def do_DELETE(self) -> None:
        """Handle DELETE requests."""
        parsed = urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/accounts/"):
            account_id = int(path.split("/")[-1])
            self.delete_account(account_id)
        else:
            self.send_error(404)

    def send_html(self) -> None:
        """Send HTML UI."""
        html = get_html_template()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def get_settings(self) -> None:
        """Get all settings."""
        settings = self.config_manager.get_all_settings()
        self.send_json({"success": True, "data": settings})

    def update_settings(self, data: dict) -> None:
        """Update settings."""
        # Filter out empty values
        filtered = {k: v for k, v in data.items() if v is not None and v != ""}
        self.config_manager.set_settings(filtered)
        self.send_json({"success": True})

    def get_accounts(self) -> None:
        """Get all accounts."""
        accounts = self.config_manager.get_accounts()
        data = [
            {
                "id": acc.id,
                "email": acc.email,
                "password": acc.password,
                "imap_server": acc.imap_server,
                "imap_port": acc.imap_port,
                "smtp_server": acc.smtp_server,
                "smtp_port": acc.smtp_port,
                "use_ssl": acc.use_ssl,
            }
            for acc in accounts
        ]
        self.send_json({"success": True, "data": data})

    def get_account(self, account_id: int) -> None:
        """Get a single account."""
        account = self.config_manager.db.get_account(account_id)
        if not account:
            self.send_json({"success": False, "error": "Account not found"}, 404)
            return
        data = {
            "id": account.id,
            "email": account.email,
            "password": account.password,
            "imap_server": account.imap_server,
            "imap_port": account.imap_port,
            "smtp_server": account.smtp_server,
            "smtp_port": account.smtp_port,
            "use_ssl": account.use_ssl,
        }
        self.send_json({"success": True, "data": data})

    def add_account(self, data: dict) -> None:
        """Add a new account."""
        try:
            account_id = self.config_manager.add_account(
                email=data.get("email"),
                password=data.get("password"),
                imap_server=data.get("imap_server"),
                imap_port=data.get("imap_port", 993),
                smtp_server=data.get("smtp_server"),
                smtp_port=data.get("smtp_port", 465),
                use_ssl=data.get("use_ssl", True),
            )
            self.send_json({"success": True, "data": {"id": account_id}})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 400)

    def update_account(self, account_id: int, data: dict) -> None:
        """Update an existing account."""
        try:
            success = self.config_manager.update_account(
                account_id,
                email=data.get("email"),
                password=data.get("password"),
                imap_server=data.get("imap_server"),
                imap_port=data.get("imap_port"),
                smtp_server=data.get("smtp_server"),
                smtp_port=data.get("smtp_port"),
                use_ssl=data.get("use_ssl"),
            )
            if success:
                self.send_json({"success": True})
            else:
                self.send_json({"success": False, "error": "Account not found"}, 404)
        except Exception as e:
            self.send_json({"success": False, "error": str(e)}, 400)

    def delete_account(self, account_id: int) -> None:
        """Delete an account."""
        success = self.config_manager.delete_account(account_id)
        if success:
            self.send_json({"success": True})
        else:
            self.send_json({"success": False, "error": "Account not found"}, 404)


class ConfigServer:
    """Local HTTP server for configuration management.

    Security features:
    - Binds to 127.0.0.1 only (no external access)
    - No authentication required (local only)
    - Runs in daemon thread for clean shutdown
    """

    def __init__(
        self,
        port_range: tuple[int, int] = DEFAULT_PORT_RANGE,
        config_manager: ConfigManager | None = None,
    ):
        """Initialize the config server.

        Args:
            port_range: Range of ports to try (default 8100-8119).
            config_manager: ConfigManager instance (default: global singleton).
        """
        self.port_range = port_range
        self.config_manager = config_manager or get_config_manager()
        self.server: ThreadingHTTPServer | None = None
        self.thread: threading.Thread | None = None
        self.port: int | None = None

    def start(self) -> int:
        """Start the HTTP server in a daemon thread.

        Returns:
            Port number the server is listening on.
        """
        # Find available port
        self.port = find_available_port(self.port_range)

        # Create handler class with config_manager
        handler = type(
            "ConfigHandlerWithManager",
            (ConfigHandler,),
            {"config_manager": self.config_manager},
        )

        # Create server bound to localhost only
        self.server = ThreadingHTTPServer(("127.0.0.1", self.port), handler)
        self.server.daemon_threads = True

        # Start in daemon thread
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

        # Save server state to database
        self.config_manager.db.set_service_state(
            "config_server", self.port, os.getpid()
        )

        logger.info(f"Config server started on http://127.0.0.1:{self.port}")
        return self.port

    def stop(self) -> None:
        """Stop the HTTP server."""
        if self.server:
            self.server.shutdown()
            self.server = None
            self.thread = None
            self.config_manager.db.clear_service_state("config_server")
            logger.info(f"Config server stopped on port {self.port}")

    def get_url(self) -> str | None:
        """Get the URL of the config server.

        Returns:
            URL string or None if not running.
        """
        if self.port is None:
            return None
        return f"http://127.0.0.1:{self.port}"

    @classmethod
    def get_running_server(cls) -> ConfigServer | None:
        """Check for an existing running server and return it if found.

        Returns None if no server is running.
        """
        manager = get_config_manager()
        state = manager.db.get_service_state("config_server")

        if state is None:
            return None

        # Check if process is still running
        try:
            os.kill(state["pid"], 0)
            # Process is running, return a server reference
            server = cls()
            server.port = state["port"]
            server.config_manager = manager
            return server
        except OSError:
            # Process is not running, clean up state
            manager.db.clear_service_state("config_server")
            return None


def ensure_config_server() -> ConfigServer:
    """Ensure a config server is running, starting one if needed.

    Returns:
        Running ConfigServer instance.
    """
    # Check for existing server
    existing = ConfigServer.get_running_server()
    if existing:
        return existing

    # Start new server
    server = ConfigServer()
    server.start()
    return server


def get_config_url() -> str:
    """Get the configuration URL, starting server if needed.

    Returns:
        Configuration URL string.
    """
    server = ensure_config_server()
    url = server.get_url()
    if url is None:
        raise RuntimeError("Failed to start config server")
    return url


if __name__ == "__main__":
    # For testing: run the server directly
    logging.basicConfig(level=logging.INFO)
    server = ConfigServer()
    port = server.start()
    print(f"Config server running at http://127.0.0.1:{port}")
    print("Press Ctrl+C to stop")
    try:
        server.thread.join()
    except KeyboardInterrupt:
        server.stop()
