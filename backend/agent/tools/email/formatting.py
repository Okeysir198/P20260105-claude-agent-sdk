"""Shared email formatting utilities for IMAP and Gmail tools."""

from typing import Any


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


def format_email_detail(parsed: dict[str, Any]) -> str:
    """Format a full email message for reading.

    Args:
        parsed: Dict with subject, from, to, date, body, has_attachments, attachments keys.

    Returns:
        Formatted markdown string.
    """
    formatted = (
        f"\n**Subject:** {parsed['subject']}\n"
        f"**From:** {parsed['from']}\n"
        f"**To:** {parsed['to']}\n"
        f"**Date:** {parsed['date']}\n"
        f"**Has Attachments:** {'Yes' if parsed.get('has_attachments') else 'No'}\n"
        f"\n---\n{parsed['body']}\n"
    )

    attachments = parsed.get("attachments", [])
    if attachments:
        formatted += f"\n\n**Attachments ({len(attachments)}):**\n"
        for att in attachments:
            size_key = "size" if "size" in att else "size"
            type_key = "content_type" if "content_type" in att else "mimeType"
            formatted += (
                f"- {att.get('filename', att.get('name', 'unknown'))} "
                f"({att.get(size_key, 0)} bytes, {att.get(type_key, 'unknown')})\n"
            )

    return formatted
