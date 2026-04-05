"""
Error code definitions and response helpers for mail-skill CLI.

Provides centralized error code constants with clear categorization:
- USER_xxx: Client errors (invalid parameters, resource not found)
- SERVER_xxx: Server errors (IMAP/SMTP/Database failures)
- BIZ_xxx: Business logic errors (permission denied, state conflicts)
"""

from dataclasses import dataclass
from typing import Optional


class MailSkillError(Exception):
    """Base exception for mail-skill operations."""

    pass


class ErrorCodes:
    """Centralized error code definitions."""

    # USER_xxx - Client errors (4xx equivalent)
    USER_EMAIL_NOT_FOUND = "USER_EMAIL_NOT_FOUND"
    USER_INVALID_MESSAGE_ID = "USER_INVALID_MESSAGE_ID"
    USER_MISSING_PARAMETER = "USER_MISSING_PARAMETER"
    USER_INVALID_PARAMETER = "USER_INVALID_PARAMETER"

    # SERVER_xxx - Server errors (5xx equivalent)
    SERVER_IMAP_CONNECTION_FAILED = "SERVER_IMAP_CONNECTION_FAILED"
    SERVER_SMTP_CONNECTION_FAILED = "SERVER_SMTP_CONNECTION_FAILED"
    SERVER_SMTP_SEND_FAILED = "SERVER_SMTP_SEND_FAILED"
    SERVER_DATABASE_ERROR = "SERVER_DATABASE_ERROR"
    SERVER_CHROMADB_ERROR = "SERVER_CHROMADB_ERROR"

    # BIZ_xxx - Business logic errors
    BIZ_EMAIL_ALREADY_SENT = "BIZ_EMAIL_ALREADY_SENT"
    BIZ_PERMISSION_DENIED = "BIZ_PERMISSION_DENIED"
    BIZ_ACCOUNT_NOT_CONFIGURED = "BIZ_ACCOUNT_NOT_CONFIGURED"


@dataclass
class ErrorResponse:
    """Standard error response structure."""

    status: str = "error"
    code: str = ""
    message: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "status": self.status,
            "code": self.code,
            "message": self.message,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        import json

        return json.dumps(self.to_dict(), ensure_ascii=False)


def error_response(code: str, message: str) -> dict:
    """
    Create a standardized error response dictionary.

    Args:
        code: Error code from ErrorCodes class
        message: Human-readable error message

    Returns:
        dict with status='error', code, and message
    """
    return {
        "status": "error",
        "code": code,
        "message": message,
    }


def success_response(data: Optional[dict] = None, message: str = "Success") -> dict:
    """
    Create a standardized success response dictionary.

    Args:
        data: Optional data to include in response (merged into top level)
        message: Human-readable success message

    Returns:
        dict with status='success' and optional data/message
    """
    result = {"status": "success"}
    if data:
        result.update(data)
    if message:
        result["message"] = message
    return result
