"""Standalone stdio MCP server for email tools (Gmail OAuth + IMAP).

Runs as a subprocess speaking JSON-RPC over stdin/stdout.
Reads EMAIL_USERNAME from environment variable
(inherited from the backend process via the SDK subprocess chain).

Usage:
    python -m email_tools.stdio_server
"""
import logging
import os
import sys

from mcp.server.fastmcp import FastMCP

from email_tools.gmail_tools import (
    list_gmail_impl,
    read_gmail_impl,
    download_gmail_attachments_impl,
    search_gmail_impl,
    send_gmail_impl,
    reply_gmail_impl,
    create_gmail_draft_impl,
    modify_gmail_impl,
)
from email_tools.imap_client import (
    list_imap_impl,
    read_imap_impl,
    download_imap_attachments_impl,
    search_imap_impl,
    list_imap_folders_impl,
    list_email_accounts_impl,
)

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger(__name__)

mcp = FastMCP("email_tools")


def _get_username() -> str:
    """Get username from environment variable."""
    username = os.environ.get("EMAIL_USERNAME")
    if not username:
        raise ValueError("EMAIL_USERNAME environment variable is required but not set")
    return username


def _get_session_id() -> str | None:
    """Get session_id from environment variable."""
    return os.environ.get("EMAIL_SESSION_ID")


# --- Discovery tools ---

@mcp.tool(
    name="list_email_accounts",
    description=(
        "List all connected email accounts and their provider keys. "
        "ALWAYS call this first before using any other email tool — "
        "it tells you which accounts are available and what provider key to use. "
        "Returns provider keys (e.g., 'gmail-johndoe7', 'yahoo'), account type (Gmail OAuth or IMAP), "
        "and connection status for each account. "
        "Use the provider key from the results as the 'provider' parameter in other IMAP email tools."
    ),
)
async def tool_list_email_accounts() -> dict:
    """List all connected email accounts."""
    return list_email_accounts_impl(_get_username())


@mcp.tool(
    name="list_imap_folders",
    description=(
        "List all available folders/mailboxes for an IMAP email account. "
        "Use this to discover folders beyond INBOX — such as Sent, Drafts, Trash, Spam, Archive, "
        "or custom folders/labels the user has created. "
        "Useful when the user asks about sent emails, drafts, or emails in specific folders. "
        "The folder names returned can be used as the 'folder' parameter in list/search/read tools."
    ),
)
async def tool_list_imap_folders(provider: str) -> dict:
    """List IMAP folders."""
    return list_imap_folders_impl(_get_username(), provider)


# --- Gmail tools ---

@mcp.tool(
    name="list_gmail",
    description=(
        "List recent emails from a Gmail OAuth account. "
        "Use this for browsing/scanning recent emails when you don't need a specific search. "
        "For targeted searches, use search_gmail instead. "
        "Returns subject, sender, date, snippet, and message ID for each email. "
        "Use the message ID with read_gmail to see full content, or download_gmail_attachments to get files."
    ),
)
async def tool_list_gmail(
    provider: str = "",
    max_results: int = 10,
    query: str = "",
    label: str = "INBOX",
) -> dict:
    """List Gmail emails."""
    return list_gmail_impl(_get_username(), max_results, query, label, provider=provider)


@mcp.tool(
    name="search_gmail",
    description=(
        "Search emails in a Gmail OAuth account using Gmail search syntax. "
        "Use this when the user wants to find specific emails by sender, subject, date, or content. "
        "For IMAP accounts (Yahoo, Outlook, etc.), use search_imap_emails instead. "
        "\n"
        "Gmail search operators: "
        "from:, to:, subject:, has:attachment, is:unread, is:starred, is:important, "
        "after:YYYY/MM/DD, before:YYYY/MM/DD, newer_than:7d, older_than:30d, "
        "label:, filename:, larger:5M, smaller:1M, in:anywhere. "
        "\n"
        "Examples: "
        "'from:amazon subject:order' — order emails from Amazon. "
        "'has:attachment after:2026/02/01' — emails with attachments this month. "
        "'is:unread from:boss@company.com' — unread emails from boss."
    ),
)
async def tool_search_gmail(
    query: str,
    provider: str = "",
    max_results: int = 10,
) -> dict:
    """Search Gmail emails."""
    return search_gmail_impl(_get_username(), query, max_results, provider=provider)


@mcp.tool(
    name="read_gmail",
    description=(
        "Read the full content of a Gmail email — body text, HTML, headers, and attachment list. "
        "Requires a message ID from list_gmail or search_gmail. "
        "Use this when the user wants to see what an email says, check details, or review attachments before downloading."
    ),
)
async def tool_read_gmail(
    message_id: str,
    provider: str = "",
) -> dict:
    """Read a Gmail email."""
    return read_gmail_impl(_get_username(), message_id, provider=provider)


@mcp.tool(
    name="download_gmail_attachments",
    description=(
        "Download attachments from a Gmail email to local storage. "
        "Requires a message ID from list_gmail, search_gmail, or read_gmail. "
        "By default downloads ALL attachments. Optionally specify attachment IDs to download only specific files."
    ),
)
async def tool_download_gmail_attachments(
    message_id: str,
    provider: str = "",
    attachment_ids: list[str] | None = None,
) -> dict:
    """Download Gmail attachments."""
    return download_gmail_attachments_impl(_get_username(), message_id, attachment_ids, provider=provider)


@mcp.tool(
    name="send_gmail",
    description=(
        "Send a new email from your connected Gmail account. "
        "Supports plain text and HTML body, plus file attachments. "
        "Only works for Gmail accounts with full access enabled (configured by admin). "
        "IMPORTANT: Always confirm with the user before sending."
    ),
)
async def tool_send_gmail(
    to: str,
    subject: str,
    body: str,
    provider: str = "",
    cc: str = "",
    bcc: str = "",
    attachments: list[dict] | None = None,
    html_body: str | None = None,
    from_name: str = "Trung Assistant Bot",
) -> dict:
    """Send a Gmail email.

    Args:
        to: Recipient email address
        subject: Email subject
        body: Plain text body (required for compatibility)
        provider: Gmail provider key (auto-discovers if empty)
        cc: CC recipients (comma-separated)
        bcc: BCC recipients (comma-separated)
        attachments: List of attachment dicts with keys:
            - data: bytes content (required)
            - filename: str filename (required)
            - mime_type: str MIME type (optional, auto-detected if missing)
        html_body: Optional HTML body for rich formatting
        from_name: Display name for sender (default: "Trung Assistant Bot")
    """
    return send_gmail_impl(
        _get_username(), to=to, subject=subject, body=body,
        cc=cc, bcc=bcc, provider=provider,
        attachments=attachments, html_body=html_body, from_name=from_name,
        session_id=_get_session_id(),
    )


@mcp.tool(
    name="reply_gmail",
    description=(
        "Reply to an existing Gmail email. Automatically threads the reply with the original message. "
        "Supports plain text and HTML body, plus file attachments. "
        "Only works for Gmail accounts with full access enabled. "
        "IMPORTANT: Always confirm with the user before sending."
    ),
)
async def tool_reply_gmail(
    message_id: str,
    body: str,
    provider: str = "",
    attachments: list[dict] | None = None,
    html_body: str | None = None,
    from_name: str = "Trung Assistant Bot",
) -> dict:
    """Reply to a Gmail email.

    Args:
        message_id: Gmail message ID to reply to
        body: Plain text body (required for compatibility)
        provider: Gmail provider key (auto-discovers if empty)
        attachments: List of attachment dicts with keys:
            - data: bytes content (required)
            - filename: str filename (required)
            - mime_type: str MIME type (optional, auto-detected if missing)
        html_body: Optional HTML body for rich formatting
        from_name: Display name for sender (default: "Trung Assistant Bot")
    """
    return reply_gmail_impl(
        _get_username(), message_id=message_id, body=body, provider=provider,
        attachments=attachments, html_body=html_body, from_name=from_name,
        session_id=_get_session_id(),
    )


@mcp.tool(
    name="create_gmail_draft",
    description=(
        "Create a draft email in your Gmail account without sending it. "
        "Supports plain text and HTML body, plus file attachments. "
        "Only works for Gmail accounts with full access enabled."
    ),
)
async def tool_create_gmail_draft(
    to: str,
    subject: str,
    body: str,
    provider: str = "",
    cc: str = "",
    bcc: str = "",
    attachments: list[dict] | None = None,
    html_body: str | None = None,
    from_name: str = "Trung Assistant Bot",
) -> dict:
    """Create a Gmail draft.

    Args:
        to: Recipient email address
        subject: Email subject
        body: Plain text body (required for compatibility)
        provider: Gmail provider key (auto-discovers if empty)
        cc: CC recipients (comma-separated)
        bcc: BCC recipients (comma-separated)
        attachments: List of attachment dicts with keys:
            - data: bytes content (required)
            - filename: str filename (required)
            - mime_type: str MIME type (optional, auto-detected if missing)
        html_body: Optional HTML body for rich formatting
        from_name: Display name for sender (default: "Trung Assistant Bot")
    """
    return create_gmail_draft_impl(
        _get_username(), to=to, subject=subject, body=body,
        cc=cc, bcc=bcc, provider=provider,
        attachments=attachments, html_body=html_body, from_name=from_name,
        session_id=_get_session_id(),
    )


@mcp.tool(
    name="modify_gmail_message",
    description=(
        "Modify labels on a Gmail message: mark as read/unread, star/unstar, archive, or trash/untrash. "
        "Only works for Gmail accounts with full access enabled."
    ),
)
async def tool_modify_gmail_message(
    message_id: str,
    action: str,
    provider: str = "",
) -> dict:
    """Modify a Gmail message."""
    return modify_gmail_impl(
        _get_username(), message_id=message_id, action=action, provider=provider,
    )


# --- IMAP tools ---

@mcp.tool(
    name="list_imap_emails",
    description=(
        "List recent emails from an IMAP email account. "
        "Works with any IMAP provider: Yahoo, Outlook, iCloud, Zoho, Gmail (app password), or custom servers. "
        "Use this for browsing recent emails. For targeted searches, use search_imap_emails instead. "
        "To list emails in other folders (Sent, Drafts, etc.), use the folder parameter — "
        "call list_imap_folders first to discover available folders."
    ),
)
async def tool_list_imap_emails(
    provider: str,
    max_results: int = 10,
    folder: str = "INBOX",
) -> dict:
    """List emails from an IMAP account."""
    return list_imap_impl(_get_username(), provider, max_results, folder)


@mcp.tool(
    name="search_imap_emails",
    description=(
        "Search emails in an IMAP account by sender, subject, date range, or keywords. "
        "Works with any IMAP provider: Yahoo, Outlook, iCloud, Zoho, Gmail (app password), or custom servers. "
        "\n"
        "Query syntax — use prefixes to target specific fields: "
        "  subject:TERM, from:ADDRESS, to:ADDRESS, since:DATE, before:DATE. "
        "  Plain words without prefix search by subject."
    ),
)
async def tool_search_imap_emails(
    provider: str,
    query: str,
    max_results: int = 10,
    folder: str = "INBOX",
) -> dict:
    """Search emails in an IMAP account."""
    return search_imap_impl(_get_username(), provider, query, max_results, folder)


@mcp.tool(
    name="read_imap_email",
    description=(
        "Read the full content of an email from an IMAP account — body text, HTML, headers, and attachment list. "
        "Requires a message ID from list_imap_emails or search_imap_emails. "
        "Make sure to use the same folder parameter as the list/search that returned the message ID."
    ),
)
async def tool_read_imap_email(
    provider: str,
    message_id: str,
    folder: str = "INBOX",
) -> dict:
    """Read an email from an IMAP account."""
    return read_imap_impl(_get_username(), provider, message_id, folder)


@mcp.tool(
    name="download_imap_attachments",
    description=(
        "Download attachments from an IMAP email to local storage. "
        "Requires a message ID from list_imap_emails, search_imap_emails, or read_imap_email. "
        "By default downloads ALL attachments. Optionally specify filenames to download only specific files. "
        "Make sure to use the same folder parameter as the list/search/read that returned the message ID."
    ),
)
async def tool_download_imap_attachments(
    provider: str,
    message_id: str,
    filenames: list[str] | None = None,
    folder: str = "INBOX",
) -> dict:
    """Download attachments from an IMAP email."""
    return download_imap_attachments_impl(_get_username(), provider, message_id, filenames, folder)


if __name__ == "__main__":
    mcp.run()
