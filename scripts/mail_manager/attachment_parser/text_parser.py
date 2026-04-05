"""
Text and markdown parser implementation.

Extracts text content from plain text and markdown files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


class TextParser:
    """Parser for plain text and markdown files."""

    def can_parse(self, file_path: Path) -> bool:
        """
        Check if this parser can handle text files.

        Args:
            file_path: Path to the file to check.

        Returns:
            True if file has .txt or .md extension.
        """
        return file_path.suffix.lower() in (".txt", ".md")

    def extract_text(self, file_path: Path) -> str:
        """
        Extract text content from text/markdown file.

        Reads file with UTF-8 encoding, ignoring errors for
        non-UTF-8 bytes.

        Args:
            file_path: Path to the text file.

        Returns:
            File content as string.
        """
        with open(file_path, encoding="utf-8", errors="ignore") as f:
            return f.read()

    def extract_metadata(self, file_path: Path) -> dict[str, Any]:
        """
        Extract metadata from text/markdown file.

        Args:
            file_path: Path to the text file.

        Returns:
            Dictionary with size_bytes and type.
        """
        file_type = "markdown" if file_path.suffix.lower() == ".md" else "text"
        return {
            "size_bytes": file_path.stat().st_size,
            "type": file_type,
        }
