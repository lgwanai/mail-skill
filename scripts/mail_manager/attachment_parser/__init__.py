"""
Attachment parser module for document content extraction.

Provides a unified interface for parsing various document types
(PDF, Excel, PowerPoint, text/markdown, images) using a protocol-based
architecture.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from mail_manager.attachment_parser.base import DocumentParser, ParseResult
from mail_manager.attachment_parser.text_parser import TextParser

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
_PARSER_REGISTRY: dict[str, str] = {
    ".pdf": "mail_manager.attachment_parser.pdf_parser.PDFParser",
    ".xlsx": "mail_manager.attachment_parser.excel_parser.ExcelParser",
    ".pptx": "mail_manager.attachment_parser.pptx_parser.PPTXParser",
    ".txt": "mail_manager.attachment_parser.text_parser.TextParser",
    ".md": "mail_manager.attachment_parser.text_parser.TextParser",
    ".markdown": "mail_manager.attachment_parser.text_parser.TextParser",
    ".jpg": "mail_manager.attachment_parser.image_parser.ImageParser",
    ".jpeg": "mail_manager.attachment_parser.image_parser.ImageParser",
    ".png": "mail_manager.attachment_parser.image_parser.ImageParser",
    ".gif": "mail_manager.attachment_parser.image_parser.ImageParser",
}

import importlib


def get_parser(file_path: Path) -> DocumentParser | None:
    suffix = file_path.suffix.lower()
    parser_path = _PARSER_REGISTRY.get(suffix)
    if not parser_path:
        return None
    module_name, class_name = parser_path.rsplit(".", 1)
    module = importlib.import_module(module_name)
    parser_class = getattr(module, class_name)
    return parser_class()


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
