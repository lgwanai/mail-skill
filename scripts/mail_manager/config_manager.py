"""Configuration manager for mail-skill.

Reads configuration from config.txt file using dotenv.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

_PROJECT_ROOT: str | None = None


def _get_project_root() -> str:
    global _PROJECT_ROOT
    if _PROJECT_ROOT is None:
        try:
            _PROJECT_ROOT = os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))
            )
        except NameError:
            _PROJECT_ROOT = os.getcwd()
    return _PROJECT_ROOT


def load_config() -> dict[str, Any]:
    """Load configuration from config.txt file."""
    config_path = _find_config_file()
    if config_path:
        try:
            load_dotenv(config_path, override=True)
        except Exception as e:
            logger.warning(f"Failed to load config.txt: {e}")

    project_root = _get_project_root()

    config: dict[str, Any] = {
        "STORAGE_ROOT": os.getenv(
            "MAIL_STORAGE_ROOT", os.path.join(project_root, "mail_data")
        ),
        "DB_PATH": os.getenv(
            "MAIL_DB_PATH", os.path.join(project_root, "mail_data", "mail_index.db")
        ),
        "ATTACHMENT_PATH": os.getenv(
            "MAIL_ATTACHMENT_PATH", os.path.join(project_root, "mail_data", "attachments")
        ),
        "ACCOUNTS": {},
    }

    account_prefixes = set()
    for key in os.environ:
        if key.startswith("MAIL_ACCOUNT_") and key.endswith("_EMAIL"):
            prefix = key[:-6]
            account_prefixes.add(prefix)

    for prefix in sorted(account_prefixes):
        email = os.getenv(f"{prefix}_EMAIL")
        if not email:
            continue

        use_ssl_raw = os.getenv(f"{prefix}_USE_SSL", "true").lower()
        use_ssl = use_ssl_raw in ("true", "1", "yes")

        def _safe_int(val: str | None, default: int) -> int:
            try:
                return int(val.strip()) if val else default
            except (ValueError, TypeError):
                return default

        config["ACCOUNTS"][email] = {
            "EMAIL": email,
            "PASSWORD": os.getenv(f"{prefix}_PASSWORD"),
            "PROTOCOL": os.getenv(f"{prefix}_PROTOCOL", "imap"),
            "IMAP_SERVER": os.getenv(f"{prefix}_IMAP_SERVER"),
            "IMAP_PORT": _safe_int(os.getenv(f"{prefix}_IMAP_PORT"), 993),
            "POP3_SERVER": os.getenv(f"{prefix}_POP3_SERVER"),
            "POP3_PORT": _safe_int(os.getenv(f"{prefix}_POP3_PORT"), 995),
            "SMTP_SERVER": os.getenv(f"{prefix}_SMTP_SERVER"),
            "SMTP_PORT": _safe_int(os.getenv(f"{prefix}_SMTP_PORT"), 465),
            "USE_SSL": use_ssl,
        }

    return config


def _find_config_file() -> str | None:
    candidates = [
        os.path.join(_get_project_root(), "config.txt"),
        os.path.join(os.getcwd(), "config.txt"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None
