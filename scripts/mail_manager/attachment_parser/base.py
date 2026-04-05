"""
Base classes and protocol for document parsers.

Provides the DocumentParser protocol and ParseResult dataclass for
consistent parser interface across different document types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


class DocumentParser(Protocol):
    """
    Protocol for document parsers.

    All document parsers must implement this protocol to ensure
    consistent interface for attachment content extraction.
    """

    def can_parse(self, file_path: Path) -> bool:
        """
        Check if this parser can handle the file type.

        Args:
            file_path: Path to the file to check.

        Returns:
            True if this parser can handle the file type.
        """
        ...

    def extract_text(self, file_path: Path) -> str:
        """
        Extract text content from document.

        Args:
            file_path: Path to the file to parse.

        Returns:
            Extracted text content.
        """
        ...

    def extract_metadata(self, file_path: Path) -> dict[str, Any]:
        """
        Extract metadata from document.

        Args:
            file_path: Path to the file to parse.

        Returns:
            Dictionary of metadata (e.g., page count, author).
        """
        ...


@dataclass
class ParseResult:
    """
    Result of parsing an attachment.

    Contains extracted text and metadata from the document.
    """

    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
