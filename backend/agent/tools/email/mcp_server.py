"""MCP server for email tools.

Registers Gmail and Yahoo Mail tools with the Claude Agent SDK.
"""
import contextvars
import logging
from typing import Any

from claude_agent_sdk import tool, create_sdk_mcp_server

from agent.tools.email.gmail_tools import (
    list_gmail_impl,
    read_gmail_impl,
    download_gmail_attachments_impl,
    search_gmail_impl,
)
from agent.tools.email.yahoo_tools import (
    list_yahoo_impl,
    read_yahoo_impl,
    download_yahoo_attachments_impl,
)

logger = logging.getLogger(__name__)


# Thread-safe context variable for current username
_current_username: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "_current_username", default=None
)


def set_username(username: str) -> contextvars.Token[str | None]:
    """Set the current username for email operations. Returns a token for resetting."""
    return _current_username.set(username)


def reset_username(token: contextvars.Token[str | None]) -> None:
    """Reset username to its previous value using a token from set_username."""
    _current_username.reset(token)


def get_username() -> str:
    """Get the current username for email operations."""
    username = _current_username.get()
    if username is None:
        raise ValueError("Username not set for email operations. Call set_username() first.")
    return username


# Gmail tools
@tool(
    name="list_gmail",
    description="List Gmail emails with optional filters. You can filter by date, sender, subject, unread status, or label.",
    input_schema={
        "type": "object",
        "properties": {
            "max_results": {
                "type": "integer",
                "description": "Maximum number of emails to return (default: 10)",
                "default": 10
            },
            "query": {
                "type": "string",
                "description": "Gmail search query (e.g., 'from:john@example.com', 'is:unread', 'subject:invoice')",
                "default": ""
            },
            "label": {
                "type": "string",
                "description": "Label filter (INBOX, UNREAD, STARRED, IMPORTANT, SENT, DRAFT, SPAM, TRASH)",
                "default": "INBOX"
            }
        }
    }
)
async def list_gmail(inputs: dict[str, Any]) -> dict[str, Any]:
    """List Gmail emails."""
    username = get_username()
    max_results = inputs.get("max_results", 10)
    query = inputs.get("query", "")
    label = inputs.get("label", "INBOX")

    return list_gmail_impl(username, max_results, query, label)


@tool(
    name="read_gmail",
    description="Read a full Gmail email including body, headers, and attachments list. Use this to see the complete content of an email.",
    input_schema={
        "type": "object",
        "properties": {
            "message_id": {
                "type": "string",
                "description": "Gmail message ID (get this from list_gmail)"
            }
        },
        "required": ["message_id"]
    }
)
async def read_gmail(inputs: dict[str, Any]) -> dict[str, Any]:
    """Read a Gmail email."""
    username = get_username()
    message_id = inputs["message_id"]

    return read_gmail_impl(username, message_id)


@tool(
    name="download_gmail_attachments",
    description="Download attachments from a Gmail email. If no specific attachment IDs are provided, downloads all attachments.",
    input_schema={
        "type": "object",
        "properties": {
            "message_id": {
                "type": "string",
                "description": "Gmail message ID"
            },
            "attachment_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of attachment IDs to download. If not provided, downloads all attachments."
            }
        },
        "required": ["message_id"]
    }
)
async def download_gmail_attachments(inputs: dict[str, Any]) -> dict[str, Any]:
    """Download Gmail attachments."""
    username = get_username()
    message_id = inputs["message_id"]
    attachment_ids = inputs.get("attachment_ids")

    return download_gmail_attachments_impl(username, message_id, attachment_ids)


@tool(
    name="search_gmail",
    description="Search Gmail emails by query. Supports Gmail search operators like 'from:', 'to:', 'subject:', 'has:attachment', 'is:unread', etc.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Gmail search query (e.g., 'from:john@example.com important:yes', 'subject:invoice has:attachment')"
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum results (default: 10)",
                "default": 10
            }
        },
        "required": ["query"]
    }
)
async def search_gmail(inputs: dict[str, Any]) -> dict[str, Any]:
    """Search Gmail emails."""
    username = get_username()
    query = inputs["query"]
    max_results = inputs.get("max_results", 10)

    return search_gmail_impl(username, query, max_results)


# Yahoo Mail tools
@tool(
    name="list_yahoo",
    description="List Yahoo Mail emails from a folder. By default lists emails from INBOX.",
    input_schema={
        "type": "object",
        "properties": {
            "max_results": {
                "type": "integer",
                "description": "Maximum number of emails to return (default: 10)",
                "default": 10
            },
            "folder": {
                "type": "string",
                "description": "IMAP folder name (default: INBOX)",
                "default": "INBOX"
            }
        }
    }
)
async def list_yahoo(inputs: dict[str, Any]) -> dict[str, Any]:
    """List Yahoo Mail emails."""
    username = get_username()
    max_results = inputs.get("max_results", 10)
    folder = inputs.get("folder", "INBOX")

    return list_yahoo_impl(username, max_results, folder)


@tool(
    name="read_yahoo",
    description="Read a full Yahoo Mail email including body, headers, and attachments list.",
    input_schema={
        "type": "object",
        "properties": {
            "message_id": {
                "type": "string",
                "description": "IMAP message ID (get this from list_yahoo)"
            },
            "folder": {
                "type": "string",
                "description": "IMAP folder name (default: INBOX)",
                "default": "INBOX"
            }
        },
        "required": ["message_id"]
    }
)
async def read_yahoo(inputs: dict[str, Any]) -> dict[str, Any]:
    """Read a Yahoo Mail email."""
    username = get_username()
    message_id = inputs["message_id"]
    folder = inputs.get("folder", "INBOX")

    return read_yahoo_impl(username, message_id, folder)


@tool(
    name="download_yahoo_attachments",
    description="Download attachments from a Yahoo Mail email. If no specific filenames are provided, downloads all attachments.",
    input_schema={
        "type": "object",
        "properties": {
            "message_id": {
                "type": "string",
                "description": "IMAP message ID"
            },
            "filenames": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional list of attachment filenames to download. If not provided, downloads all attachments."
            },
            "folder": {
                "type": "string",
                "description": "IMAP folder name (default: INBOX)",
                "default": "INBOX"
            }
        },
        "required": ["message_id"]
    }
)
async def download_yahoo_attachments(inputs: dict[str, Any]) -> dict[str, Any]:
    """Download Yahoo Mail attachments."""
    username = get_username()
    message_id = inputs["message_id"]
    filenames = inputs.get("filenames")
    folder = inputs.get("folder", "INBOX")

    return download_yahoo_attachments_impl(username, message_id, filenames, folder)


# Create MCP server
email_tools_server = create_sdk_mcp_server(
    name="email_tools",
    version="1.0.0",
    tools=[
        list_gmail,
        read_gmail,
        download_gmail_attachments,
        search_gmail,
        list_yahoo,
        read_yahoo,
        download_yahoo_attachments,
    ]
)


__all__ = [
    "email_tools_server",
    "set_username",
    "reset_username",
    "get_username",
]
