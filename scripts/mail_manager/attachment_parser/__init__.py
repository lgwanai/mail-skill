"""
Attachment parser module for document content extraction.

Provides a unified interface for parsing various document types
(PDF, Excel, PowerPoint, text/markdown) using a protocol-based
architecture.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.mail_manager.attachment_parser.base import DocumentParser, ParseResult
from scripts.mail_manager.attachment_parser.excel_parser import ExcelParser
from scripts.mail_manager.attachment_parser.pdf_parser import PDFParser
from scripts.mail_manager.attachment_parser.pptx_parser import PPTXParser
from scripts.mail_manager.attachment_parser.text_parser import TextParser

__all__ = [
    "DocumentParser",
    "ParseResult",
    "parse_attachment",
    "get_parser",
    "PDFParser",
    "ExcelParser",
    "PPTXParser",
    "TextParser",
]

# Parser registry: maps file extensions to parser classes
_PARSER_REGISTRY: dict[str, type[DocumentParser]] = {
    ".pdf": PDFParser,
    ".xlsx": ExcelParser,
    ".xls": ExcelParser,
    ".pptx": PPTXParser,
    ".txt": TextParser,
    ".md": TextParser,
}


def get_parser(file_path: Path) -> DocumentParser | None:
    """
    Get appropriate parser for a file based on its extension.

    Args:
        file_path: Path to the file to parse.

    Returns:
        Parser instance for the file type, or None if unsupported.
    """
    suffix = file_path.suffix.lower()
    parser_class = _PARSER_REGISTRY.get(suffix)
    if parser_class:
        return parser_class()
    return None


def parse_attachment(file_path: Path) -> ParseResult:
    """
    Parse an attachment file and extract text and metadata.

    Factory function that dispatches to the appropriate parser
    based on file extension.

    Args:
        file_path: Path to the attachment file.

    Returns:
        ParseResult with extracted text and metadata.
    """
    parser = get_parser(file_path)
    if parser is None:
        return ParseResult(text="", metadata={"error": "unsupported_format"})

    text = parser.extract_text(file_path)
    metadata = parser.extract_metadata(file_path)

    return ParseResult(text=text, metadata=metadata)
