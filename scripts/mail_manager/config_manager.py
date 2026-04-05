"""Configuration manager for mail-skill.

Provides a unified configuration interface that:
1. Reads from SQLite config database
2. Falls back to config.txt environment variables
3. Auto-imports existing config.txt on first run
4. Provides access to config web server URL
"""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv

from mail_manager.config_db import Account, ConfigDatabase


class ConfigManager:
    """Manages configuration from database with fallback to environment."""

    _instance: ConfigManager | None = None
    _db: ConfigDatabase | None = None
    _imported_from_env: bool = False

    def __new__(cls) -> ConfigManager:
        """Singleton pattern to ensure single database connection."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize config manager with database."""
        if self._db is None:
            self._db = ConfigDatabase()
            self._try_import_from_env()

    def _try_import_from_env(self) -> None:
        """Try to import configuration from config.txt if database is empty."""
        if self._imported_from_env:
            return

        # Check if database already has accounts
        if self._db.is_configured():
            self._imported_from_env = True
            return

        # Try to load from config.txt
        config_path = self._find_config_file()
        if config_path:
            load_dotenv(config_path)
            self._import_from_environment()
            self._imported_from_env = True

    def _find_config_file(self) -> str | None:
        """Find config.txt file location."""
        # Check project root
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_path = os.path.join(os.path.dirname(script_dir), "config.txt")
        if os.path.exists(env_path):
            return env_path

        # Check current directory
        if os.path.exists("config.txt"):
            return "config.txt"

        return None

    def _import_from_environment(self) -> None:
        """Import configuration from environment variables to database."""
        # Import settings
        settings_map = {
            "MAIL_STORAGE_ROOT": "STORAGE_ROOT",
            "MAIL_DB_PATH": "DB_PATH",
            "MAIL_ATTACHMENT_PATH": "ATTACHMENT_PATH",
            "OPENAI_API_KEY": "OPENAI_API_KEY",
            "OPENAI_API_BASE": "OPENAI_API_BASE",
            "LLM_MODEL_NAME": "LLM_MODEL_NAME",
            "LLM_TIMEOUT": "LLM_TIMEOUT",
            "EMBEDDING_MODEL_NAME": "EMBEDDING_MODEL_NAME",
            "RERANKER_MODEL_NAME": "RERANKER_MODEL_NAME",
        }

        for env_key, db_key in settings_map.items():
            value = os.getenv(env_key)
            if value:
                self._db.set_setting(db_key, value)

        # Import accounts
        account_prefixes = set()
        for key in os.environ:
            if key.startswith("MAIL_ACCOUNT_") and key.endswith("_EMAIL"):
                prefix = key[:-6]  # Remove _EMAIL
                account_prefixes.add(prefix)

        for prefix in sorted(account_prefixes):
            email = os.getenv(f"{prefix}_EMAIL")
            if not email:
                continue

            # Check if account already exists
            existing = [a for a in self._db.get_accounts() if a.email == email]
            if existing:
                continue

            self._db.add_account(
                email=email,
                password=os.getenv(f"{prefix}_PASSWORD"),
                imap_server=os.getenv(f"{prefix}_IMAP_SERVER"),
                imap_port=int(os.getenv(f"{prefix}_IMAP_PORT", "993")),
                smtp_server=os.getenv(f"{prefix}_SMTP_SERVER"),
                smtp_port=int(os.getenv(f"{prefix}_SMTP_PORT", "465")),
                use_ssl=os.getenv(f"{prefix}_USE_SSL", "true").lower() == "true",
            )

    def load_config(self) -> dict[str, Any]:
        """Load configuration in format compatible with existing load_config().

        Returns:
            Configuration dictionary with STORAGE_ROOT, DB_PATH, ATTACHMENT_PATH, ACCOUNTS.
        """
        config: dict[str, Any] = {
            "STORAGE_ROOT": self.get_setting("STORAGE_ROOT", "./mail_data"),
            "DB_PATH": self.get_setting("DB_PATH", "./mail_data/mail_index.db"),
            "ATTACHMENT_PATH": self.get_setting(
                "ATTACHMENT_PATH", "./mail_data/attachments"
            ),
            "ACCOUNTS": {},
        }

        # Load accounts from database
        for account in self._db.get_accounts():
            config["ACCOUNTS"][account.email] = account.to_dict()

        return config

    def get_setting(self, key: str, default: str | None = None) -> str | None:
        """Get a setting value.

        Args:
            key: Setting key name.
            default: Default value if not found.

        Returns:
            Setting value or default.
        """
        # First check database
        value = self._db.get_setting(key)
        if value is not None:
            return value

        # Fall back to environment variable
        env_key = f"MAIL_{key}" if not key.startswith("MAIL_") else key
        env_value = os.getenv(env_key)
        if env_value is not None:
            return env_value

        return default

    def set_setting(self, key: str, value: str) -> None:
        """Set a setting value in database.

        Args:
            key: Setting key name.
            value: Setting value.
        """
        self._db.set_setting(key, value)

    def is_configured(self) -> bool:
        """Check if the system has been configured.

        Returns:
            True if at least one account exists.
        """
        return self._db.is_configured()

    def get_accounts(self) -> list[Account]:
        """Get all configured email accounts.

        Returns:
            List of Account objects.
        """
        return self._db.get_accounts()

    def add_account(self, **kwargs: Any) -> int:
        """Add a new email account.

        Args:
            **kwargs: Account fields (email, password, imap_server, etc.)

        Returns:
            The ID of the newly created account.
        """
        return self._db.add_account(**kwargs)

    def update_account(self, account_id: int, **kwargs: Any) -> bool:
        """Update an existing account.

        Args:
            account_id: Account ID to update.
            **kwargs: Fields to update.

        Returns:
            True if updated, False if not found.
        """
        return self._db.update_account(account_id, **kwargs)

    def delete_account(self, account_id: int) -> bool:
        """Delete an account.

        Args:
            account_id: Account ID to delete.

        Returns:
            True if deleted, False if not found.
        """
        return self._db.delete_account(account_id)

    def get_config_url(self) -> str | None:
        """Get the URL of the configuration web interface.

        Returns:
            Configuration URL or None if server is not running.
        """
        state = self._db.get_service_state("config_server")
        if not state:
            return None

        # Check if the process is still running
        try:
            import signal
            os.kill(state["pid"], 0)
            return f"http://127.0.0.1:{state['port']}"
        except (OSError, ProcessLookupError):
            return None

    def get_all_settings(self) -> dict[str, str]:
        """Get all settings from database.

        Returns:
            Dictionary of all settings.
        """
        return self._db.get_all_settings()

    def set_settings(self, settings: dict[str, str]) -> None:
        """Set multiple settings at once.

        Args:
            settings: Dictionary of settings to set.
        """
        self._db.set_settings(settings)

    @property
    def db(self) -> ConfigDatabase:
        """Get the underlying database instance."""
        return self._db


# Singleton instance for convenience
_config_manager: ConfigManager | None = None


def get_config_manager() -> ConfigManager:
    """Get the singleton ConfigManager instance.

    Returns:
        ConfigManager instance.
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager
