"""Content normalization utilities for SDK message format.

This module provides utilities to normalize user content into the format
expected by the Claude Agent SDK.
"""
import logging
from typing import Any

logger = logging.getLogger(__name__)


def normalize_content(content: str | list) -> str | list:
    """Normalize user content to SDK-expected format.

    This function ensures content is in the correct format for the SDK:
    - String content is returned as-is
    - List content is validated and normalized
    - Handles multi-part content (text, images, etc.)

    Args:
        content: The content to normalize (string or list).

    Returns:
        Normalized content in SDK-compatible format.

    Raises:
        ValueError: If content format is invalid.
        TypeError: If content type is unsupported.

    Examples:
        >>> normalize_content("Hello")
        'Hello'
        >>> normalize_content([{"type": "text", "text": "Hi"}])
        [{'type': 'text', 'text': 'Hi'}]
    """
    if isinstance(content, str):
        # String content is already valid
        return content

    if isinstance(content, list):
        # Validate list content has required structure
        if not content:
            raise ValueError("Content list cannot be empty")

        # Basic validation - each item should be a dict with 'type' key
        for i, item in enumerate(content):
            if not isinstance(item, dict):
                raise TypeError(
                    f"Content list item {i} must be a dict, got {type(item).__name__}"
                )
            if "type" not in item:
                raise ValueError(
                    f"Content list item {i} must have 'type' key"
                )

        return content

    raise TypeError(
        f"Content must be str or list, got {type(content).__name__}"
    )
