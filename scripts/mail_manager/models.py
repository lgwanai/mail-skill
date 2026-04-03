"""
Data models for mail-skill type annotations.

Provides dataclasses for structured email data, attachments, and command results.
Uses from __future__ import annotations for Python 3.8 compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class Attachment:
    """Represents an email attachment."""

    filename: str
    content_type: str
    size: int
    local_path: Optional[str] = None


@dataclass
class EmailData:
    """Represents an email with all its metadata."""

    # Required fields
    message_id: str
    subject: str
    sender: str
    recipient: str
    date: str
    body_text: str
    account: str

    # Optional fields with defaults
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
    attachments: List[Attachment] = field(default_factory=list)


@dataclass
class CommandResult:
    """Standard response format for CLI commands."""

    status: str  # 'success' or 'error'
    code: Optional[str] = None
    message: Optional[str] = None
    data: Optional[dict] = None

    def to_dict(self) -> dict:
        """
        Convert to dictionary for JSON serialization.

        Returns:
            dict with status, and optionally code, message, and data
        """
        result = {'status': self.status}
        if self.code:
            result['code'] = self.code
        if self.message:
            result['message'] = self.message
        if self.data:
            result['data'] = self.data
        return result
