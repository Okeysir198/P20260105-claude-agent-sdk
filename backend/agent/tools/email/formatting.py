"""Shared email formatting utilities for IMAP and Gmail tools."""

from typing import Any


def make_tool_result(text: str) -> dict[str, Any]:
    """Create a standard MCP tool result.

    Args:
        text: Result text content.

    Returns:
        MCP-compatible tool result dict.
    """
    return {"content": [{"type": "text", "text": text}]}


def format_email_preview(msg: dict[str, Any]) -> str:
    """Format an email message summary for list/search results.

    Args:
        msg: Dict with subject, from, date, id, and snippet keys.

    Returns:
        Formatted markdown string.
    """
    return (
        f"\n**Subject:** {msg['subject']}\n"
        f"**From:** {msg['from']}\n"
        f"**Date:** {msg['date']}\n"
        f"**ID:** {msg['id']}\n"
        f"---\n{msg.get('snippet', '')}\n"
    )


def format_email_detail(parsed: dict[str, Any], extra_fields: dict[str, str] | None = None) -> str:
    """Format a full email message for reading.

    Args:
        parsed: Dict with subject, from, to, date, body, has_attachments, attachments keys.
        extra_fields: Optional additional header fields to include (e.g., message_id, labels).

    Returns:
        Formatted markdown string.
    """
    formatted = (
        f"\n**Subject:** {parsed['subject']}\n"
        f"**From:** {parsed['from']}\n"
        f"**To:** {parsed['to']}\n"
        f"**Date:** {parsed['date']}\n"
    )

    if extra_fields:
        for label, value in extra_fields.items():
            formatted += f"**{label}:** {value}\n"

    formatted += (
        f"**Has Attachments:** {'Yes' if parsed.get('has_attachments') else 'No'}\n"
        f"\n---\n{parsed['body']}\n"
    )

    attachments = parsed.get("attachments", [])
    if attachments:
        formatted += f"\n\n**Attachments ({len(attachments)}):**\n"
        for att in attachments:
            filename = att.get("filename", att.get("name", "unknown"))
            size = att.get("size", 0)
            content_type = att.get("content_type", att.get("mimeType", "unknown"))
            formatted += f"- {filename} ({size} bytes, {content_type})\n"

    return formatted
