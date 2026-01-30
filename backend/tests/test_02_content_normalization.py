"""Test suite for content normalization functionality.

Tests core multi-part content normalization:
- String to ContentBlock conversion
- Multi-part text and image handling
- Text extraction for history
- Basic error handling
"""
import pytest

from api.services.content_normalizer import normalize_content, extract_text_content


class TestContentNormalization:
    """Test content normalization functionality."""

    def test_normalize_plain_string(self):
        """Plain strings should convert to single text block."""
        content = "Hello, world!"
        blocks = normalize_content(content)

        assert len(blocks) == 1
        assert blocks[0].type == "text"
        assert blocks[0].text == content

    def test_normalize_multipart_text(self):
        """Multiple text blocks should be preserved."""
        content = [
            {"type": "text", "text": "First message"},
            {"type": "text", "text": "Second message"}
        ]
        blocks = normalize_content(content)

        assert len(blocks) == 2
        assert blocks[0].text == "First message"
        assert blocks[1].text == "Second message"

    def test_normalize_multipart_with_image_url(self):
        """Text and image blocks (URL) should be preserved."""
        content = [
            {"type": "text", "text": "Analyze this:"},
            {
                "type": "image",
                "source": {"type": "url", "url": "https://example.com/img.jpg"}
            }
        ]
        blocks = normalize_content(content)

        assert len(blocks) == 2
        assert blocks[0].type == "text"
        assert blocks[1].type == "image"
        assert blocks[1].source["type"] == "url"

    def test_normalize_multipart_with_image_base64(self):
        """Text and image blocks (base64) should be preserved."""
        content = [
            {"type": "text", "text": "Base64 image:"},
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBD..."
                }
            }
        ]
        blocks = normalize_content(content)

        assert len(blocks) == 2
        assert blocks[1].type == "image"
        assert blocks[1].source["type"] == "base64"
        assert "data" in blocks[1].source

    def test_extract_text_from_string(self):
        """Extracting text from plain string should return original."""
        content = "Hello, world!"
        text = extract_text_content(content)
        assert text == content

    def test_extract_text_from_multipart(self):
        """Extracting text from multi-part should concatenate text blocks."""
        content = [
            {"type": "text", "text": "First"},
            {"type": "image", "source": {"type": "url", "url": "https://example.com/img.jpg"}},
            {"type": "text", "text": "Second"}
        ]
        text = extract_text_content(content)
        assert text == "First\nSecond"

    def test_error_invalid_block_type(self):
        """Invalid block type should raise error."""
        content = [{"type": "video", "url": "https://example.com/video.mp4"}]
        with pytest.raises(ValueError, match="Invalid block type"):
            normalize_content(content)
