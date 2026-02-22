"""Content normalization utilities for multi-part message content.

Converts between plain strings, multi-part content block lists, and mixed
formats. Supports text and image blocks following Claude's message format.
"""
import json
import re
from typing import Any, Literal

from pydantic import BaseModel, field_validator, ValidationInfo

from api.utils.sensitive_data_filter import redact_sensitive_data


class ContentBlock(BaseModel):
    """A single content block in a multi-part message."""

    type: Literal["text", "image"]
    text: str | None = None
    source: dict[str, Any] | None = None

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


# Pattern to strip agentId metadata from tool results
# Matches agentId: <identifier> patterns in content
AGENT_ID_PATTERN = re.compile(r'agentId:\s*\S+')


def _unwrap_mcp_content(text: str) -> str:
    """Unwrap MCP content wrapper if present.

    MCP tools return results wrapped as {"content": [{"type": "text", "text": "<json>"}]}.
    The SDK may store ToolResultBlock.content as a string of this wrapper.
    Extract the inner text to get the actual tool result.
    """
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, TypeError, ValueError):
        return text

    if not isinstance(parsed, dict):
        return text

    # Check for MCP wrapper: has "content" key but no domain-specific keys
    inner = parsed.get("content")
    if inner is None or "action" in parsed or "error" in parsed:
        return text  # Not an MCP wrapper, or already unwrapped

    if isinstance(inner, list):
        for block in inner:
            if isinstance(block, dict) and block.get("type") == "text":
                return block.get("text", text)
    elif isinstance(inner, str):
        try:
            json.loads(inner)  # Validate it's JSON
            return inner
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

    return text


def normalize_tool_result_content(content: Any, agent_id_pattern: re.Pattern | None = None) -> str:
    """Normalize tool result content to a clean string, stripping agentId metadata.

    Handles None, str, list of text dicts, single text dict, and other types.
    Unwraps MCP content wrappers and applies sensitive data redaction.
    """
    if content is None:
        return ""

    pattern = agent_id_pattern or AGENT_ID_PATTERN

    if isinstance(content, str):
        result = _unwrap_mcp_content(content)
        result = pattern.sub('', result)
        return redact_sensitive_data(result)

    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text", "")
                parts.append(pattern.sub('', text))
            else:
                parts.append(str(item))
        result = pattern.sub('', "\n".join(parts))
        return redact_sensitive_data(result)

    if isinstance(content, dict) and content.get("type") == "text":
        result = pattern.sub('', content.get("text", ""))
        return redact_sensitive_data(result)

    # Dict with "content" key (MCP wrapper as dict, not string)
    if isinstance(content, dict) and "content" in content and "action" not in content:
        inner = content.get("content")
        if isinstance(inner, list):
            parts = []
            for item in inner:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(pattern.sub('', item.get("text", "")))
            if parts:
                result = "\n".join(parts)
                return redact_sensitive_data(result)

    result = pattern.sub('', str(content))
    return redact_sensitive_data(result)


def normalize_content(content: ContentBlockInput) -> list[ContentBlock]:
    """Normalize content to a list of validated ContentBlock objects.

    Accepts plain strings, list of dicts, or a single dict.
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
    """Extract and concatenate text from content blocks for legacy compatibility."""
    if isinstance(content, str):
        return content

    blocks = normalize_content(content)
    text_parts = [block.text for block in blocks if block.type == 'text' and block.text]

    return '\n'.join(text_parts) if text_parts else ''


def _validate_and_create_block(block: dict[str, Any]) -> ContentBlock:
    """Validate a dict and create a ContentBlock from it."""
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


