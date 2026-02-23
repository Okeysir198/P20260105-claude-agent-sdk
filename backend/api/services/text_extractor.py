"""Shared utility for extracting clean text from SDK AssistantMessage content blocks."""
import re

from claude_agent_sdk.types import TextBlock


def extract_clean_text_blocks(content_blocks: list, tool_ref_pattern: re.Pattern) -> list[str]:
    """Extract and clean text from AssistantMessage content blocks, stripping tool references."""
    result = []
    for block in content_blocks:
        if isinstance(block, TextBlock) and block.text.strip():
            cleaned = tool_ref_pattern.sub("", block.text).strip()
            if cleaned:
                result.append(cleaned)
    return result
