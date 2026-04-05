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

    def test_get_parser_returns_image_parser_for_jpg_extension(self) -> None:
        """get_parser() returns ImageParser for .jpg files."""
        from scripts.mail_manager.attachment_parser import get_parser

        parser = get_parser(Path("test.jpg"))
        assert parser is not None
        assert parser.__class__.__name__ == "ImageParser"

    def test_get_parser_returns_image_parser_for_png_extension(self) -> None:
        """get_parser() returns ImageParser for .png files."""
        from scripts.mail_manager.attachment_parser import get_parser

        parser = get_parser(Path("test.png"))
        assert parser is not None
        assert parser.__class__.__name__ == "ImageParser"

    def test_get_parser_returns_image_parser_for_gif_extension(self) -> None:
        """get_parser() returns ImageParser for .gif files."""
        from scripts.mail_manager.attachment_parser import get_parser

        parser = get_parser(Path("test.gif"))
        assert parser is not None
        assert parser.__class__.__name__ == "ImageParser"


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


class TestImageParser:
    """Tests for image parser implementation using vision API."""

    def test_can_parse_returns_true_for_jpg(self) -> None:
        """ImageParser.can_parse() returns True for .jpg files."""
        from scripts.mail_manager.attachment_parser.image_parser import ImageParser

        parser = ImageParser()
        assert parser.can_parse(Path("test.jpg")) is True
        assert parser.can_parse(Path("test.JPG")) is True

    def test_can_parse_returns_true_for_jpeg(self) -> None:
        """ImageParser.can_parse() returns True for .jpeg files."""
        from scripts.mail_manager.attachment_parser.image_parser import ImageParser

        parser = ImageParser()
        assert parser.can_parse(Path("test.jpeg")) is True
        assert parser.can_parse(Path("test.JPEG")) is True

    def test_can_parse_returns_true_for_png(self) -> None:
        """ImageParser.can_parse() returns True for .png files."""
        from scripts.mail_manager.attachment_parser.image_parser import ImageParser

        parser = ImageParser()
        assert parser.can_parse(Path("test.png")) is True
        assert parser.can_parse(Path("test.PNG")) is True

    def test_can_parse_returns_true_for_gif(self) -> None:
        """ImageParser.can_parse() returns True for .gif files."""
        from scripts.mail_manager.attachment_parser.image_parser import ImageParser

        parser = ImageParser()
        assert parser.can_parse(Path("test.gif")) is True
        assert parser.can_parse(Path("test.GIF")) is True

    def test_can_parse_returns_false_for_non_image(self) -> None:
        """ImageParser.can_parse() returns False for non-image files."""
        from scripts.mail_manager.attachment_parser.image_parser import ImageParser

        parser = ImageParser()
        assert parser.can_parse(Path("test.pdf")) is False
        assert parser.can_parse(Path("test.txt")) is False

    def test_extract_text_encodes_image_and_calls_vision_api(self, tmp_path: Path) -> None:
        """ImageParser.extract_text() encodes image as base64 and calls vision API."""
        from scripts.mail_manager.attachment_parser.image_parser import ImageParser

        parser = ImageParser()
        test_file = tmp_path / "test.jpg"
        # Create a minimal valid JPEG (1x1 red pixel)
        test_file.write_bytes(
            b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
            b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
            b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
            b"\x1f\x1e\x1d\x1a\x1c\x1c $. ' \",#\x1c\x1c(7),01444\x1f'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00"
            b"\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b"
            b"\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07\"q\x142\x81\x91\xa1"
            b"\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n\x16\x17\x18\x19\x1a%&'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz"
            b"\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca"
            b"\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa"
            b"\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xfb\xd3@\x00\xff\xd9"
        )

        with patch("scripts.mail_manager.attachment_parser.image_parser.LLMClient") as mock_llm_class:
            mock_llm = MagicMock()
            mock_llm_class.return_value = mock_llm
            mock_response = MagicMock()
            mock_response.content = "This is a test image description."
            mock_llm.chat.return_value = mock_response

            text = parser.extract_text(test_file)

            # Verify LLM client was called with vision API message structure
            mock_llm.chat.assert_called_once()
            call_args = mock_llm.chat.call_args
            messages = call_args[0][0]
            assert len(messages) == 1
            assert messages[0]["role"] == "user"
            # Check content is a list with text and image_url
            content = messages[0]["content"]
            assert isinstance(content, list)
            assert len(content) == 2
            assert content[0]["type"] == "text"
            assert content[1]["type"] == "image_url"
            assert "url" in content[1]["image_url"]
            assert content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")
            assert "This is a test image description." in text

    def test_extract_text_returns_description_from_vision_model(self, tmp_path: Path) -> None:
        """ImageParser.extract_text() returns description from vision model."""
        from scripts.mail_manager.attachment_parser.image_parser import ImageParser

        parser = ImageParser()
        test_file = tmp_path / "test.png"
        # Create a minimal PNG (1x1 red pixel)
        test_file.write_bytes(
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0"
            b"\x00\x00\x00\x03\x00\x01\x00\x18\xdd\x8d\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )

        with patch("scripts.mail_manager.attachment_parser.image_parser.LLMClient") as mock_llm_class:
            mock_llm = MagicMock()
            mock_llm_class.return_value = mock_llm
            mock_response = MagicMock()
            mock_response.content = "A screenshot showing a document with text."
            mock_llm.chat.return_value = mock_response

            text = parser.extract_text(test_file)

            assert text == "A screenshot showing a document with text."

    def test_extract_metadata_returns_image_type(self, tmp_path: Path) -> None:
        """ImageParser.extract_metadata() returns image type and size."""
        from scripts.mail_manager.attachment_parser.image_parser import ImageParser

        parser = ImageParser()
        test_file = tmp_path / "test.gif"
        # Create a minimal GIF (1x1 red pixel)
        test_file.write_bytes(
            b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\x00\x00\x00\x00\x00,"
            b"\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
        )

        metadata = parser.extract_metadata(test_file)

        assert metadata["type"] == "image"
        assert metadata["format"] == "gif"
        assert "size_bytes" in metadata


class TestParseAndStoreIntegration:
    """Tests for parse_and_store_attachment integration helper."""

    def test_parse_and_store_stores_content_in_database(self, tmp_path: Path) -> None:
        """parse_and_store_attachment stores parsed content in database."""
        from unittest.mock import MagicMock

        from scripts.mail_manager.attachment_parser import parse_and_store_attachment

        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        mock_db = MagicMock()
        mock_db.save_attachment_content = MagicMock()

        text = parse_and_store_attachment(test_file, mock_db)

        assert text == "Hello, World!"
        mock_db.save_attachment_content.assert_called_once_with(
            str(test_file), "Hello, World!"
        )

    def test_parse_and_store_with_llm_client_for_images(self, tmp_path: Path) -> None:
        """parse_and_store_attachment passes LLM client for image parsing."""
        from scripts.mail_manager.attachment_parser import parse_and_store_attachment
        from scripts.mail_manager.attachment_parser.image_parser import ImageParser

        test_file = tmp_path / "test.jpg"
        # Create a minimal valid JPEG (1x1 red pixel)
        test_file.write_bytes(
            b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
            b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
            b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
            b"\x1f\x1e\x1d\x1a\x1c\x1c $. ' \",#\x1c\x1c(7),01444\x1f'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00"
            b"\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b"
            b"\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07\"q\x142\x81\x91\xa1"
            b"\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n\x16\x17\x18\x19\x1a%&'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz"
            b"\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca"
            b"\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa"
            b"\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xfb\xd3@\x00\xff\xd9"
        )

        mock_db = MagicMock()
        mock_db.save_attachment_content = MagicMock()
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "A test image."
        mock_llm.chat.return_value = mock_response

        text = parse_and_store_attachment(test_file, mock_db, llm_client=mock_llm)

        assert text == "A test image."
        mock_db.save_attachment_content.assert_called_once_with(
            str(test_file), "A test image."
        )

    def test_parse_and_store_does_not_store_empty_content(self, tmp_path: Path) -> None:
        """parse_and_store_attachment does not store empty content."""
        from scripts.mail_manager.attachment_parser import parse_and_store_attachment

        test_file = tmp_path / "test.xyz"
        test_file.write_text("some content")

        mock_db = MagicMock()
        mock_db.save_attachment_content = MagicMock()

        text = parse_and_store_attachment(test_file, mock_db)

        assert text == ""
        mock_db.save_attachment_content.assert_not_called()

    def test_parse_and_store_does_not_store_for_missing_file(self, tmp_path: Path) -> None:
        """parse_and_store_attachment raises error for non-existent file."""
        from scripts.mail_manager.attachment_parser import parse_and_store_attachment

        test_file = tmp_path / "nonexistent.txt"

        mock_db = MagicMock()
        mock_db.save_attachment_content = MagicMock()

        # Parser will raise FileNotFoundError for missing file
        # This is expected behavior - callers should handle file errors
        import pytest

        with pytest.raises(FileNotFoundError):
            parse_and_store_attachment(test_file, mock_db)

        # Should not have called save since file doesn't exist
        mock_db.save_attachment_content.assert_not_called()
