"""
Tests for attachment parser infrastructure.

Tests the DocumentParser protocol, parser factory, and individual parser implementations.
Uses mocks for external dependencies (PyMuPDF, openpyxl, python-pptx).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


class TestDocumentParserProtocol:
    """Tests for DocumentParser protocol definition."""

    def test_protocol_has_can_parse_method(self) -> None:
        """DocumentParser protocol must define can_parse method."""
        from scripts.mail_manager.attachment_parser.base import DocumentParser

        # Protocol methods should exist
        assert hasattr(DocumentParser, "can_parse")

    def test_protocol_has_extract_text_method(self) -> None:
        """DocumentParser protocol must define extract_text method."""
        from scripts.mail_manager.attachment_parser.base import DocumentParser

        assert hasattr(DocumentParser, "extract_text")

    def test_protocol_has_extract_metadata_method(self) -> None:
        """DocumentParser protocol must define extract_metadata method."""
        from scripts.mail_manager.attachment_parser.base import DocumentParser

        assert hasattr(DocumentParser, "extract_metadata")


class TestParserFactory:
    """Tests for parser factory functions."""

    def test_get_parser_returns_pdf_parser_for_pdf_extension(self) -> None:
        """get_parser() returns PDFParser for .pdf files."""
        from scripts.mail_manager.attachment_parser import get_parser

        parser = get_parser(Path("test.pdf"))
        assert parser is not None
        assert parser.__class__.__name__ == "PDFParser"

    def test_get_parser_returns_excel_parser_for_xlsx_extension(self) -> None:
        """get_parser() returns ExcelParser for .xlsx files."""
        from scripts.mail_manager.attachment_parser import get_parser

        parser = get_parser(Path("test.xlsx"))
        assert parser is not None
        assert parser.__class__.__name__ == "ExcelParser"

    def test_get_parser_returns_excel_parser_for_xls_extension(self) -> None:
        """get_parser() returns ExcelParser for .xls files."""
        from scripts.mail_manager.attachment_parser import get_parser

        parser = get_parser(Path("test.xls"))
        assert parser is not None
        assert parser.__class__.__name__ == "ExcelParser"

    def test_get_parser_returns_pptx_parser_for_pptx_extension(self) -> None:
        """get_parser() returns PPTXParser for .pptx files."""
        from scripts.mail_manager.attachment_parser import get_parser

        parser = get_parser(Path("test.pptx"))
        assert parser is not None
        assert parser.__class__.__name__ == "PPTXParser"

    def test_get_parser_returns_text_parser_for_txt_extension(self) -> None:
        """get_parser() returns TextParser for .txt files."""
        from scripts.mail_manager.attachment_parser import get_parser

        parser = get_parser(Path("test.txt"))
        assert parser is not None
        assert parser.__class__.__name__ == "TextParser"

    def test_get_parser_returns_text_parser_for_md_extension(self) -> None:
        """get_parser() returns TextParser for .md files."""
        from scripts.mail_manager.attachment_parser import get_parser

        parser = get_parser(Path("test.md"))
        assert parser is not None
        assert parser.__class__.__name__ == "TextParser"

    def test_get_parser_returns_none_for_unsupported_extension(self) -> None:
        """get_parser() returns None for unsupported file types."""
        from scripts.mail_manager.attachment_parser import get_parser

        parser = get_parser(Path("test.xyz"))
        assert parser is None

    def test_get_parser_is_case_insensitive(self) -> None:
        """get_parser() handles uppercase extensions."""
        from scripts.mail_manager.attachment_parser import get_parser

        parser = get_parser(Path("test.PDF"))
        assert parser is not None
        assert parser.__class__.__name__ == "PDFParser"


class TestParseAttachmentFactory:
    """Tests for parse_attachment() factory function."""

    def test_parse_attachment_dispatches_to_correct_parser(self, tmp_path: Path) -> None:
        """parse_attachment() dispatches to the correct parser based on extension."""
        from scripts.mail_manager.attachment_parser import parse_attachment
        from scripts.mail_manager.attachment_parser.base import ParseResult

        # Create a test text file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, world!")

        result = parse_attachment(test_file)

        assert isinstance(result, ParseResult)
        assert "Hello, world!" in result.text

    def test_parse_attachment_returns_empty_result_for_unsupported(self, tmp_path: Path) -> None:
        """parse_attachment() returns empty ParseResult for unsupported types."""
        from scripts.mail_manager.attachment_parser import parse_attachment
        from scripts.mail_manager.attachment_parser.base import ParseResult

        test_file = tmp_path / "test.xyz"
        test_file.write_text("some content")

        result = parse_attachment(test_file)

        assert isinstance(result, ParseResult)
        assert result.text == ""
        assert result.metadata.get("error") == "unsupported_format"


class TestParseResult:
    """Tests for ParseResult dataclass."""

    def test_parse_result_has_text_field(self) -> None:
        """ParseResult must have text field."""
        from scripts.mail_manager.attachment_parser.base import ParseResult

        result = ParseResult(text="sample text", metadata={})
        assert result.text == "sample text"

    def test_parse_result_has_metadata_field(self) -> None:
        """ParseResult must have metadata field."""
        from scripts.mail_manager.attachment_parser.base import ParseResult

        result = ParseResult(text="", metadata={"page_count": 5})
        assert result.metadata == {"page_count": 5}

    def test_parse_result_defaults_empty_metadata(self) -> None:
        """ParseResult metadata defaults to empty dict."""
        from scripts.mail_manager.attachment_parser.base import ParseResult

        result = ParseResult(text="test")
        assert result.metadata == {}


class TestPDFParser:
    """Tests for PDF parser implementation."""

    def test_can_parse_returns_true_for_pdf(self) -> None:
        """PDFParser.can_parse() returns True for .pdf files."""
        from scripts.mail_manager.attachment_parser.pdf_parser import PDFParser

        parser = PDFParser()
        assert parser.can_parse(Path("test.pdf")) is True
        assert parser.can_parse(Path("test.PDF")) is True

    def test_can_parse_returns_false_for_non_pdf(self) -> None:
        """PDFParser.can_parse() returns False for non-pdf files."""
        from scripts.mail_manager.attachment_parser.pdf_parser import PDFParser

        parser = PDFParser()
        assert parser.can_parse(Path("test.txt")) is False
        assert parser.can_parse(Path("test.xlsx")) is False

    def test_extract_text_extracts_all_pages(self, tmp_path: Path) -> None:
        """PDFParser.extract_text() extracts text from all pages."""
        from scripts.mail_manager.attachment_parser.pdf_parser import PDFParser

        parser = PDFParser()
        test_file = tmp_path / "test.pdf"

        with patch("scripts.mail_manager.attachment_parser.pdf_parser.fitz") as mock_fitz:
            mock_doc = MagicMock()
            mock_page1 = MagicMock()
            mock_page1.get_text.return_value = "Page 1 content"
            mock_page2 = MagicMock()
            mock_page2.get_text.return_value = "Page 2 content"
            mock_doc.__iter__ = MagicMock(return_value=iter([mock_page1, mock_page2]))
            mock_doc.close = MagicMock()
            mock_fitz.open.return_value = mock_doc

            text = parser.extract_text(test_file)

            assert "Page 1 content" in text
            assert "Page 2 content" in text
            mock_doc.close.assert_called_once()

    def test_extract_metadata_returns_page_count(self, tmp_path: Path) -> None:
        """PDFParser.extract_metadata() returns page count."""
        from scripts.mail_manager.attachment_parser.pdf_parser import PDFParser

        parser = PDFParser()
        test_file = tmp_path / "test.pdf"

        with patch("scripts.mail_manager.attachment_parser.pdf_parser.fitz") as mock_fitz:
            mock_doc = MagicMock()
            mock_doc.__len__ = MagicMock(return_value=3)
            mock_doc.metadata = {}
            mock_doc.close = MagicMock()
            mock_fitz.open.return_value = mock_doc

            metadata = parser.extract_metadata(test_file)

            assert metadata["page_count"] == 3
            assert metadata["type"] == "pdf"
            mock_doc.close.assert_called_once()


class TestExcelParser:
    """Tests for Excel parser implementation."""

    def test_can_parse_returns_true_for_xlsx(self) -> None:
        """ExcelParser.can_parse() returns True for .xlsx files."""
        from scripts.mail_manager.attachment_parser.excel_parser import ExcelParser

        parser = ExcelParser()
        assert parser.can_parse(Path("test.xlsx")) is True
        assert parser.can_parse(Path("test.XLSX")) is True

    def test_can_parse_returns_true_for_xls(self) -> None:
        """ExcelParser.can_parse() returns True for .xls files."""
        from scripts.mail_manager.attachment_parser.excel_parser import ExcelParser

        parser = ExcelParser()
        assert parser.can_parse(Path("test.xls")) is True

    def test_can_parse_returns_false_for_non_excel(self) -> None:
        """ExcelParser.can_parse() returns False for non-Excel files."""
        from scripts.mail_manager.attachment_parser.excel_parser import ExcelParser

        parser = ExcelParser()
        assert parser.can_parse(Path("test.pdf")) is False
        assert parser.can_parse(Path("test.csv")) is False

    def test_extract_text_handles_multiple_sheets(self, tmp_path: Path) -> None:
        """ExcelParser.extract_text() handles multiple sheets."""
        from scripts.mail_manager.attachment_parser.excel_parser import ExcelParser

        parser = ExcelParser()
        test_file = tmp_path / "test.xlsx"

        with patch("scripts.mail_manager.attachment_parser.excel_parser.load_workbook") as mock_load:
            mock_wb = MagicMock()
            mock_sheet1 = MagicMock()
            mock_sheet1.title = "Sheet1"
            # iter_rows with values_only=True returns tuples of values directly
            mock_sheet1.iter_rows.return_value = [
                ("A1", "B1"),
                ("A2", "B2"),
            ]
            mock_sheet2 = MagicMock()
            mock_sheet2.title = "Sheet2"
            mock_sheet2.iter_rows.return_value = [
                ("C1", "D1"),
            ]
            mock_wb.worksheets = [mock_sheet1, mock_sheet2]
            mock_wb.close = MagicMock()
            mock_load.return_value = mock_wb

            text = parser.extract_text(test_file)

            assert "A1 | B1" in text
            assert "A2 | B2" in text
            assert "C1 | D1" in text
            mock_wb.close.assert_called_once()

    def test_extract_metadata_returns_sheet_names(self, tmp_path: Path) -> None:
        """ExcelParser.extract_metadata() returns sheet names."""
        from scripts.mail_manager.attachment_parser.excel_parser import ExcelParser

        parser = ExcelParser()
        test_file = tmp_path / "test.xlsx"

        with patch("scripts.mail_manager.attachment_parser.excel_parser.load_workbook") as mock_load:
            mock_wb = MagicMock()
            mock_sheet1 = MagicMock()
            mock_sheet1.title = "Sheet1"
            mock_sheet1.max_row = 10
            mock_sheet2 = MagicMock()
            mock_sheet2.title = "Sheet2"
            mock_sheet2.max_row = 5
            mock_wb.sheetnames = ["Sheet1", "Sheet2"]
            mock_wb.worksheets = [mock_sheet1, mock_sheet2]
            mock_wb.close = MagicMock()
            mock_load.return_value = mock_wb

            metadata = parser.extract_metadata(test_file)

            assert metadata["sheet_names"] == ["Sheet1", "Sheet2"]
            assert metadata["type"] == "excel"
            mock_wb.close.assert_called_once()


class TestPPTXParser:
    """Tests for PowerPoint parser implementation."""

    def test_can_parse_returns_true_for_pptx(self) -> None:
        """PPTXParser.can_parse() returns True for .pptx files."""
        from scripts.mail_manager.attachment_parser.pptx_parser import PPTXParser

        parser = PPTXParser()
        assert parser.can_parse(Path("test.pptx")) is True
        assert parser.can_parse(Path("test.PPTX")) is True

    def test_can_parse_returns_false_for_non_pptx(self) -> None:
        """PPTXParser.can_parse() returns False for non-pptx files."""
        from scripts.mail_manager.attachment_parser.pptx_parser import PPTXParser

        parser = PPTXParser()
        assert parser.can_parse(Path("test.ppt")) is False  # Old format not supported
        assert parser.can_parse(Path("test.pdf")) is False

    def test_extract_text_extracts_from_all_shapes(self, tmp_path: Path) -> None:
        """PPTXParser.extract_text() extracts text from all shapes."""
        from scripts.mail_manager.attachment_parser.pptx_parser import PPTXParser

        parser = PPTXParser()
        test_file = tmp_path / "test.pptx"

        with patch("scripts.mail_manager.attachment_parser.pptx_parser.Presentation") as mock_pres_class:
            mock_pres = MagicMock()
            mock_slide1 = MagicMock()
            mock_shape1 = MagicMock()
            mock_shape1.text = "Slide 1 Title"
            mock_shape2 = MagicMock()
            mock_shape2.text = "Slide 1 Body"
            mock_slide1.shapes = [mock_shape1, mock_shape2]

            mock_slide2 = MagicMock()
            mock_shape3 = MagicMock()
            mock_shape3.text = "Slide 2 Content"
            mock_slide2.shapes = [mock_shape3]

            mock_pres.slides = [mock_slide1, mock_slide2]
            mock_pres_class.return_value = mock_pres

            text = parser.extract_text(test_file)

            assert "Slide 1 Title" in text
            assert "Slide 1 Body" in text
            assert "Slide 2 Content" in text

    def test_extract_metadata_returns_slide_count(self, tmp_path: Path) -> None:
        """PPTXParser.extract_metadata() returns slide count."""
        from scripts.mail_manager.attachment_parser.pptx_parser import PPTXParser

        parser = PPTXParser()
        test_file = tmp_path / "test.pptx"

        with patch("scripts.mail_manager.attachment_parser.pptx_parser.Presentation") as mock_pres_class:
            mock_pres = MagicMock()
            mock_slide = MagicMock()
            mock_pres.slides = [mock_slide, mock_slide, mock_slide]  # 3 slides
            mock_pres_class.return_value = mock_pres

            metadata = parser.extract_metadata(test_file)

            assert metadata["slide_count"] == 3
            assert metadata["type"] == "powerpoint"


class TestTextParser:
    """Tests for text/markdown parser implementation."""

    def test_can_parse_returns_true_for_txt(self) -> None:
        """TextParser.can_parse() returns True for .txt files."""
        from scripts.mail_manager.attachment_parser.text_parser import TextParser

        parser = TextParser()
        assert parser.can_parse(Path("test.txt")) is True
        assert parser.can_parse(Path("test.TXT")) is True

    def test_can_parse_returns_true_for_md(self) -> None:
        """TextParser.can_parse() returns True for .md files."""
        from scripts.mail_manager.attachment_parser.text_parser import TextParser

        parser = TextParser()
        assert parser.can_parse(Path("test.md")) is True
        assert parser.can_parse(Path("test.MD")) is True

    def test_can_parse_returns_false_for_other(self) -> None:
        """TextParser.can_parse() returns False for non-text files."""
        from scripts.mail_manager.attachment_parser.text_parser import TextParser

        parser = TextParser()
        assert parser.can_parse(Path("test.pdf")) is False
        assert parser.can_parse(Path("test.doc")) is False

    def test_extract_text_reads_file_content(self, tmp_path: Path) -> None:
        """TextParser.extract_text() reads file content correctly."""
        from scripts.mail_manager.attachment_parser.text_parser import TextParser

        parser = TextParser()
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!\nThis is a test.", encoding="utf-8")

        text = parser.extract_text(test_file)

        assert text == "Hello, World!\nThis is a test."

    def test_extract_text_handles_utf8_with_errors(self, tmp_path: Path) -> None:
        """TextParser.extract_text() handles encoding errors gracefully."""
        from scripts.mail_manager.attachment_parser.text_parser import TextParser

        parser = TextParser()
        test_file = tmp_path / "test.txt"
        # Write some content that's valid UTF-8
        test_file.write_text("Valid UTF-8 content", encoding="utf-8")

        text = parser.extract_text(test_file)

        assert text == "Valid UTF-8 content"

    def test_extract_metadata_returns_size_and_type(self, tmp_path: Path) -> None:
        """TextParser.extract_metadata() returns size and type."""
        from scripts.mail_manager.attachment_parser.text_parser import TextParser

        parser = TextParser()
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello")

        metadata = parser.extract_metadata(test_file)

        assert "size_bytes" in metadata
        assert metadata["type"] == "text"

    def test_extract_metadata_returns_markdown_type(self, tmp_path: Path) -> None:
        """TextParser.extract_metadata() returns correct type for markdown."""
        from scripts.mail_manager.attachment_parser.text_parser import TextParser

        parser = TextParser()
        test_file = tmp_path / "test.md"
        test_file.write_text("# Heading")

        metadata = parser.extract_metadata(test_file)

        assert metadata["type"] == "markdown"
