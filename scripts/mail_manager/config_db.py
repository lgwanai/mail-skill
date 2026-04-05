"""Configuration database for storing settings and accounts.

Provides a SQLite-based configuration store with support for:
- Global key-value settings
- Email account management
- Service state persistence
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator


@dataclass
class Account:
    """Email account configuration."""

    id: int | None
    email: str
    password: str | None
    imap_server: str | None
    imap_port: int
    smtp_server: str | None
    smtp_port: int
    use_ssl: bool
    is_default: bool

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format compatible with existing load_config()."""
        return {
            "EMAIL": self.email,
            "PASSWORD": self.password,
            "IMAP_SERVER": self.imap_server,
            "IMAP_PORT": str(self.imap_port),
            "SMTP_SERVER": self.smtp_server,
            "SMTP_PORT": str(self.smtp_port),
            "USE_SSL": "true" if self.use_ssl else "false",
            "PREFIX": f"MAIL_ACCOUNT_{self.id}",
        }


class ConfigDatabase:
    """SQLite-based configuration storage."""

    def __init__(self, db_path: str | None = None) -> None:
        """Initialize configuration database.

        Args:
            db_path: Path to config database. Defaults to ./mail_data/config.db
        """
        if db_path is None:
            db_path = os.path.join(
                os.getenv("MAIL_STORAGE_ROOT", "./mail_data"), "config.db"
            )
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database tables."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Global settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Accounts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    password TEXT,
                    imap_server TEXT,
                    imap_port INTEGER DEFAULT 993,
                    smtp_server TEXT,
                    smtp_port INTEGER DEFAULT 465,
                    use_ssl BOOLEAN DEFAULT 1,
                    is_default BOOLEAN DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Service state table (for config server port tracking)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS service_state (
                    service_name TEXT PRIMARY KEY,
                    port INTEGER,
                    pid INTEGER,
                    started_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()

    @contextmanager
    def _get_connection(self) -> Iterator[sqlite3.Connection]:
        """Get database connection with context manager."""
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    # === Settings Operations ===

    def get_setting(self, key: str, default: str | None = None) -> str | None:
        """Get a setting value by key.

        Args:
            key: Setting key name.
            default: Default value if not found.

        Returns:
            Setting value or default.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        """Set a setting value.

        Args:
            key: Setting key name.
            value: Setting value.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (key, value),
            )
            conn.commit()

    def get_all_settings(self) -> dict[str, str]:
        """Get all settings as a dictionary.

        Returns:
            Dictionary of all settings.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM settings")
            return {row["key"]: row["value"] for row in cursor.fetchall()}

    def set_settings(self, settings: dict[str, str]) -> None:
        """Set multiple settings at once.

        Args:
            settings: Dictionary of settings to set.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            for key, value in settings.items():
                cursor.execute(
                    """
                    INSERT INTO settings (key, value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(key) DO UPDATE SET
                        value = excluded.value,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (key, value),
                )
            conn.commit()

    # === Account Operations ===

    def get_accounts(self) -> list[Account]:
        """Get all email accounts.

        Returns:
            List of Account objects.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM accounts ORDER BY id")
            return [
                Account(
                    id=row["id"],
                    email=row["email"],
                    password=row["password"],
                    imap_server=row["imap_server"],
                    imap_port=row["imap_port"] or 993,
                    smtp_server=row["smtp_server"],
                    smtp_port=row["smtp_port"] or 465,
                    use_ssl=bool(row["use_ssl"]),
                    is_default=bool(row["is_default"]),
                )
                for row in cursor.fetchall()
            ]

    def get_account(self, account_id: int) -> Account | None:
        """Get an account by ID.

        Args:
            account_id: Account ID.

        Returns:
            Account object or None if not found.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM accounts WHERE id = ?", (account_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return Account(
                id=row["id"],
                email=row["email"],
                password=row["password"],
                imap_server=row["imap_server"],
                imap_port=row["imap_port"] or 993,
                smtp_server=row["smtp_server"],
                smtp_port=row["smtp_port"] or 465,
                use_ssl=bool(row["use_ssl"]),
                is_default=bool(row["is_default"]),
            )

    def add_account(
        self,
        email: str,
        password: str | None = None,
        imap_server: str | None = None,
        imap_port: int = 993,
        smtp_server: str | None = None,
        smtp_port: int = 465,
        use_ssl: bool = True,
        is_default: bool = False,
    ) -> int:
        """Add a new email account.

        Args:
            email: Account email address.
            password: Account password.
            imap_server: IMAP server address.
            imap_port: IMAP server port.
            smtp_server: SMTP server address.
            smtp_port: SMTP server port.
            use_ssl: Whether to use SSL.
            is_default: Whether this is the default account.

        Returns:
            The ID of the newly created account.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO accounts (
                    email, password, imap_server, imap_port,
                    smtp_server, smtp_port, use_ssl, is_default
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    email,
                    password,
                    imap_server,
                    imap_port,
                    smtp_server,
                    smtp_port,
                    use_ssl,
                    is_default,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def update_account(
        self,
        account_id: int,
        email: str | None = None,
        password: str | None = None,
        imap_server: str | None = None,
        imap_port: int | None = None,
        smtp_server: str | None = None,
        smtp_port: int | None = None,
        use_ssl: bool | None = None,
        is_default: bool | None = None,
    ) -> bool:
        """Update an existing account.

        Args:
            account_id: Account ID to update.
            Other args: Fields to update (None = no change).

        Returns:
            True if updated, False if account not found.
        """
        updates = []
        values = []

        if email is not None:
            updates.append("email = ?")
            values.append(email)
        if password is not None:
            updates.append("password = ?")
            values.append(password)
        if imap_server is not None:
            updates.append("imap_server = ?")
            values.append(imap_server)
        if imap_port is not None:
            updates.append("imap_port = ?")
            values.append(imap_port)
        if smtp_server is not None:
            updates.append("smtp_server = ?")
            values.append(smtp_server)
        if smtp_port is not None:
            updates.append("smtp_port = ?")
            values.append(smtp_port)
        if use_ssl is not None:
            updates.append("use_ssl = ?")
            values.append(use_ssl)
        if is_default is not None:
            updates.append("is_default = ?")
            values.append(is_default)

        if not updates:
            return False

        updates.append("updated_at = CURRENT_TIMESTAMP")
        values.append(account_id)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE accounts SET {', '.join(updates)} WHERE id = ?",
                values,
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete_account(self, account_id: int) -> bool:
        """Delete an account.

        Args:
            account_id: Account ID to delete.

        Returns:
            True if deleted, False if not found.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
            conn.commit()
            return cursor.rowcount > 0

    # === Service State Operations ===

    def get_service_state(self, service_name: str) -> dict[str, Any] | None:
        """Get service state by name.

        Args:
            service_name: Name of the service.

        Returns:
            Service state dict or None.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM service_state WHERE service_name = ?", (service_name,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "port": row["port"],
                "pid": row["pid"],
                "started_at": row["started_at"],
            }

    def set_service_state(
        self, service_name: str, port: int, pid: int
    ) -> None:
        """Set service state.

        Args:
            service_name: Name of the service.
            port: Port the service is running on.
            pid: Process ID of the service.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO service_state (service_name, port, pid, started_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(service_name) DO UPDATE SET
                    port = excluded.port,
                    pid = excluded.pid,
                    started_at = CURRENT_TIMESTAMP
                """,
                (service_name, port, pid),
            )
            conn.commit()

    def clear_service_state(self, service_name: str) -> None:
        """Clear service state.

        Args:
            service_name: Name of the service.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM service_state WHERE service_name = ?", (service_name,)
            )
            conn.commit()

    # === Configuration Check ===

    def is_configured(self) -> bool:
        """Check if any configuration exists.

        Returns:
            True if at least one account exists.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM accounts")
            row = cursor.fetchone()
            return row["count"] > 0

    def has_required_settings(self) -> bool:
        """Check if required settings exist.

        Returns:
            True if storage_root is configured.
        """
        return self.get_setting("STORAGE_ROOT") is not None
