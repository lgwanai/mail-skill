"""Image parser using vision API for content extraction.

Provides image parsing capabilities using LLM vision API to describe
image content for search and indexing.
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Any

from mail_manager.attachment_parser.base import DocumentParser
from mail_manager.llm.client import LLMClient
from mail_manager.llm.prompts import IMAGE_DESCRIPTION_PROMPT

logger = logging.getLogger(__name__)


class ImageParser(DocumentParser):
    """Parser for image files using vision API.

    Supports common image formats (jpg, jpeg, png, gif) and uses
    LLM vision API to generate text descriptions for search.
    """

    SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif"}

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        """Initialize image parser.

        Args:
            llm_client: Optional LLM client for vision API. If not provided,
                        a new client will be created when needed.
        """
        self._llm_client = llm_client

    @property
    def _llm(self) -> LLMClient:
        """Get or create LLM client."""
        if self._llm_client is None:
            self._llm_client = LLMClient()
        return self._llm_client

    def can_parse(self, file_path: Path) -> bool:
        """Check if this parser can handle the file type.

        Args:
            file_path: Path to the file to check.

        Returns:
            True if this parser can handle the file type.
        """
        return file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS

    def extract_text(self, file_path: Path) -> str:
        """Extract text description from image using vision API.

        Encodes image as base64 and sends to vision model for description.

        Args:
            file_path: Path to the image file.

        Returns:
            Text description of the image content.
        """
        try:
            # Read and encode image
            image_data = file_path.read_bytes()
            base64_image = base64.b64encode(image_data).decode("utf-8")

            # Determine MIME type from extension
            suffix = file_path.suffix.lower()
            mime_types = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".gif": "image/gif",
            }
            mime_type = mime_types.get(suffix, "image/jpeg")

            # Build vision API message
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": IMAGE_DESCRIPTION_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64_image}"
                            },
                        },
                    ],
                }
            ]

            # Call vision API
            response = self._llm.chat(messages, max_tokens=1000)
            return response.content

        except Exception as e:
            logger.error(f"Failed to extract text from image {file_path}: {e}")
            return ""

    def extract_metadata(self, file_path: Path) -> dict[str, Any]:
        """Extract metadata from image file.

        Args:
            file_path: Path to the image file.

        Returns:
            Dictionary with image type, format, and size.
        """
        suffix = file_path.suffix.lower()
        format_map = {
            ".jpg": "jpeg",
            ".jpeg": "jpeg",
            ".png": "png",
            ".gif": "gif",
        }

        return {
            "type": "image",
            "format": format_map.get(suffix, "unknown"),
            "size_bytes": file_path.stat().st_size if file_path.exists() else 0,
        }
