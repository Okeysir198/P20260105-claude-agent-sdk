"""Shared utility for extracting clean text from SDK AssistantMessage content blocks."""
import re

from claude_agent_sdk.types import TextBlock


def extract_clean_text_blocks(content_blocks: list, tool_ref_pattern: re.Pattern) -> list[str]:
    """Extract and clean text from SDK AssistantMessage content blocks.

    Iterates over content blocks, selects TextBlock instances with non-empty text,
    strips proxy-injected tool reference patterns, and returns cleaned strings.

    Args:
        content_blocks: List of content blocks from AssistantMessage.content.
        tool_ref_pattern: Compiled regex pattern to strip from text.

    Returns:
        List of cleaned, non-empty text strings.
    """
    result = []
    for block in content_blocks:
        if isinstance(block, TextBlock) and block.text.strip():
            cleaned = tool_ref_pattern.sub("", block.text).strip()
            if cleaned:
                result.append(cleaned)
    return result
