"""Configuration manager for mail-skill.

Reads configuration from config.txt file using dotenv.
"""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv


def load_config() -> dict[str, Any]:
    """Load configuration from config.txt file.

    Returns:
        Configuration dictionary with STORAGE_ROOT, DB_PATH, ATTACHMENT_PATH, ACCOUNTS.
    """
    config_path = _find_config_file()
    if config_path:
        load_dotenv(config_path, override=True)

    config: dict[str, Any] = {
        "STORAGE_ROOT": os.getenv("MAIL_STORAGE_ROOT", "./mail_data"),
        "DB_PATH": os.getenv("MAIL_DB_PATH", "./mail_data/mail_index.db"),
        "ATTACHMENT_PATH": os.getenv("MAIL_ATTACHMENT_PATH", "./mail_data/attachments"),
        "ACCOUNTS": {},
    }

    # Parse accounts from environment variables
    account_prefixes = set()
    for key in os.environ:
        if key.startswith("MAIL_ACCOUNT_") and key.endswith("_EMAIL"):
            prefix = key[:-6]
            account_prefixes.add(prefix)

    for prefix in sorted(account_prefixes):
        email = os.getenv(f"{prefix}_EMAIL")
        if not email:
            continue

        config["ACCOUNTS"][email] = {
            "EMAIL": email,
            "PASSWORD": os.getenv(f"{prefix}_PASSWORD"),
            "IMAP_SERVER": os.getenv(f"{prefix}_IMAP_SERVER"),
            "IMAP_PORT": os.getenv(f"{prefix}_IMAP_PORT", "993"),
            "SMTP_SERVER": os.getenv(f"{prefix}_SMTP_SERVER"),
            "SMTP_PORT": os.getenv(f"{prefix}_SMTP_PORT", "465"),
            "USE_SSL": os.getenv(f"{prefix}_USE_SSL", "true"),
        }

    return config


def _find_config_file() -> str | None:
    """Find config.txt file location."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    candidates = [
        os.path.join(project_root, "config.txt"),
        os.path.join(os.getcwd(), "config.txt"),
    ]

    for path in candidates:
        if os.path.exists(path):
            return path

    return None
