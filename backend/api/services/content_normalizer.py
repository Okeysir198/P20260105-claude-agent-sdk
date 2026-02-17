"""
Content normalization utilities for handling multi-part message content.

This module provides functions to convert between different content representations:
- Plain strings (legacy format)
- Multi-part content (list of content blocks)
- Mixed formats (for validation/normalization)

Content blocks follow Claude's message format with support for:
- Text blocks: {"type": "text", "text": "content"}
- Image blocks: {"type": "image", "source": {...}}
"""

from typing import Any, Literal

from pydantic import BaseModel, field_validator, ValidationInfo


class ContentBlock(BaseModel):
    """A single content block in a multi-part message."""

    type: Literal["text", "image"]
    """Content block type"""

    text: str | None = None
    """Text content (for text blocks)"""

    source: dict[str, Any] | None = None
    """Image source data (for image blocks)"""

    @field_validator('source')
    @classmethod
    def validate_image_source(cls, v: dict[str, Any] | None, info: ValidationInfo) -> dict[str, Any] | None:
        """Validate image source structure."""
        if v is None:
            return v

        if info.data.get('type') != 'image':
            return v

        if not isinstance(v, dict):
            raise ValueError("Image source must be a dictionary")

        source_type = v.get('type')
        if source_type not in ('base64', 'url'):
            raise ValueError(f"Image source type must be 'base64' or 'url', got '{source_type}'")

        if source_type == 'base64' and 'data' not in v:
            raise ValueError("Base64 image source must include 'data' field")

        if source_type == 'url' and 'url' not in v:
            raise ValueError("URL image source must include 'url' field")

        return v


ContentBlockInput = str | list[dict[str, Any]] | dict[str, Any]
"""Accepted input types for content normalization"""


def normalize_content(content: ContentBlockInput) -> list[ContentBlock]:
    """
    Normalize content to a list of ContentBlock objects.

    Handles three input formats:
    1. Plain string → Converts to single text block
    2. List of dicts → Validates and converts each dict to ContentBlock
    3. Single dict → Wraps in list and validates

    Args:
        content: Content in string, list, or dict format

    Returns:
        List of validated ContentBlock objects

    Raises:
        ValueError: If content format is invalid or block structure is incorrect
        TypeError: If content type is unsupported

    Examples:
        >>> normalize_content("Hello world")
        [ContentBlock(type='text', text='Hello world', source=None)]

        >>> normalize_content([{"type": "text", "text": "Hello"}])
        [ContentBlock(type='text', text='Hello', source=None)]

        >>> normalize_content({"type": "text", "text": "Hello"})
        [ContentBlock(type='text', text='Hello', source=None)]
    """
    if isinstance(content, str):
        # Legacy string format → single text block
        return [ContentBlock(type='text', text=content)]

    if isinstance(content, list):
        # Multi-part content → validate each block
        if not content:
            raise ValueError("Content list cannot be empty")

        blocks: list[ContentBlock] = []
        for i, block in enumerate(content):
            try:
                blocks.append(_validate_and_create_block(block))
            except (ValueError, TypeError) as e:
                raise ValueError(f"Invalid content block at index {i}: {e}") from e

        return blocks

    if isinstance(content, dict):
        # Single block → wrap in list
        return [_validate_and_create_block(content)]

    raise TypeError(
        f"Unsupported content type: {type(content).__name__}. "
        "Expected str, list, or dict"
    )


def extract_text_content(content: ContentBlockInput) -> str:
    """
    Extract text from content for legacy compatibility.

    For plain strings, returns the string as-is.
    For multi-part content, concatenates all text blocks with newlines.

    Args:
        content: Content in any supported format

    Returns:
        Concatenated text content

    Examples:
        >>> extract_text_content("Hello")
        'Hello'

        >>> extract_text_content([{"type": "text", "text": "Hello"}, {"type": "text", "text": "World"}])
        'Hello\\nWorld'

        >>> extract_text_content([{"type": "image", "source": {...}}, {"type": "text", "text": "Caption"}])
        'Caption'
    """
    if isinstance(content, str):
        return content

    blocks = normalize_content(content)
    text_parts = [block.text for block in blocks if block.type == 'text' and block.text]

    return '\n'.join(text_parts) if text_parts else ''


def _validate_and_create_block(block: dict[str, Any]) -> ContentBlock:
    """
    Internal helper to validate and create a ContentBlock.

    Args:
        block: Dictionary representing a content block

    Returns:
        Validated ContentBlock object

    Raises:
        ValueError: If block structure is invalid
    """
    if not isinstance(block, dict):
        raise TypeError(f"Block must be a dictionary, got {type(block).__name__}")

    block_type = block.get('type')
    if not block_type:
        raise ValueError("Content block must have a 'type' field")

    if block_type not in ('text', 'image'):
        raise ValueError(f"Invalid block type '{block_type}'. Must be 'text' or 'image'")

    try:
        return ContentBlock(**block)
    except Exception as e:
        raise ValueError(f"Failed to create content block: {e}") from e


