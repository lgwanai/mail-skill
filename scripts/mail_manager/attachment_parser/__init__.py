"""
Attachment parser module for document content extraction.

Provides a unified interface for parsing various document types
(PDF, Excel, PowerPoint, text/markdown, images) using a protocol-based
architecture.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from scripts.mail_manager.attachment_parser.base import DocumentParser, ParseResult
from scripts.mail_manager.attachment_parser.excel_parser import ExcelParser
from scripts.mail_manager.attachment_parser.image_parser import ImageParser
from scripts.mail_manager.attachment_parser.pdf_parser import PDFParser
from scripts.mail_manager.attachment_parser.pptx_parser import PPTXParser
from scripts.mail_manager.attachment_parser.text_parser import TextParser

if TYPE_CHECKING:
    from scripts.mail_manager.db import MailDatabase
    from scripts.mail_manager.llm.client import LLMClient

__all__ = [
    "DocumentParser",
    "ParseResult",
    "parse_attachment",
    "get_parser",
    "parse_and_store_attachment",
    "PDFParser",
    "ExcelParser",
    "PPTXParser",
    "TextParser",
    "ImageParser",
]

# Parser registry: maps file extensions to parser classes
_PARSER_REGISTRY: dict[str, type[DocumentParser]] = {
    ".pdf": PDFParser,
    ".xlsx": ExcelParser,
    ".xls": ExcelParser,
    ".pptx": PPTXParser,
    ".txt": TextParser,
    ".md": TextParser,
    ".jpg": ImageParser,
    ".jpeg": ImageParser,
    ".png": ImageParser,
    ".gif": ImageParser,
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


def parse_attachment(file_path: Path, llm_client: LLMClient | None = None) -> ParseResult:
    """
    Parse an attachment file and extract text and metadata.

    Factory function that dispatches to the appropriate parser
    based on file extension.

    Args:
        file_path: Path to the attachment file.
        llm_client: Optional LLM client for image parsing.

    Returns:
        ParseResult with extracted text and metadata.
    """
    suffix = file_path.suffix.lower()
    parser_class = _PARSER_REGISTRY.get(suffix)

    if parser_class is None:
        return ParseResult(text="", metadata={"error": "unsupported_format"})

    # For image parser, pass LLM client if provided
    if parser_class is ImageParser and llm_client is not None:
        parser: DocumentParser = ImageParser(llm_client=llm_client)
    else:
        parser = parser_class()

    text = parser.extract_text(file_path)
    metadata = parser.extract_metadata(file_path)

    return ParseResult(text=text, metadata=metadata)


def parse_and_store_attachment(
    file_path: Path,
    db: "MailDatabase",
    llm_client: "LLMClient | None" = None,
) -> str:
    """
    Parse attachment content and store in database.

    Convenience function that parses an attachment and stores the
    extracted text in the database for later search.

    Args:
        file_path: Path to the attachment file.
        db: MailDatabase instance for storage.
        llm_client: Optional LLM client for image parsing.

    Returns:
        Parsed text content (also stored in database).
    """
    result = parse_attachment(file_path, llm_client=llm_client)

    if result.text and file_path.exists():
        db.save_attachment_content(str(file_path), result.text)

    return result.text
