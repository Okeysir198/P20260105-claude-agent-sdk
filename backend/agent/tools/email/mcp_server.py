"""MCP server for email tools.

Registers Gmail and IMAP email tools with the Claude Agent SDK.
Provides a complete email assistant toolkit: list accounts, browse folders,
list/search/read emails, and download attachments across all connected accounts.
"""
import contextvars
import logging
from typing import Any

from claude_agent_sdk import tool, create_sdk_mcp_server

from agent.tools.email.credential_store import get_credential_store
from agent.tools.email.gmail_tools import (
    list_gmail_impl,
    read_gmail_impl,
    download_gmail_attachments_impl,
    search_gmail_impl,
    send_gmail_impl,
    reply_gmail_impl,
    create_gmail_draft_impl,
    modify_gmail_impl,
)
from agent.tools.email.imap_client import (
    list_imap_impl,
    read_imap_impl,
    download_imap_attachments_impl,
    search_imap_impl,
    list_imap_folders_impl,
    list_email_accounts_impl,
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
    """Get the current username for email operations.

    First tries context variable (for in-process calls), then falls back to
    environment variable EMAIL_USERNAME (for subprocess calls from SDK).
    """
    # Try context variable first (for direct in-process calls)
    username = _current_username.get()
    if username:
        return username

    # Fall back to environment variable (for SDK subprocess calls)
    import os
    username = os.environ.get("EMAIL_USERNAME")
    if username:
        logger.debug(f"Using username from environment: {username}")
        return username

    raise ValueError("Username not set for email operations. Call set_username() first or set EMAIL_USERNAME environment variable.")


# ======================================================================
# WORKFLOW GUIDE (embedded in tool descriptions so the agent learns the pattern)
#
# Step 1: list_email_accounts → discover which accounts are connected + their provider keys
# Step 2: list_imap_folders (optional) → discover folders beyond INBOX (Sent, Drafts, etc.)
# Step 3: list_*_emails or search_*_emails → browse or find specific emails → get message IDs
# Step 4: read_*_email → read full email content using message ID from step 3
# Step 5: download_*_attachments → download files using message ID from step 3/4
#
# Gmail OAuth accounts → use list_gmail, search_gmail, read_gmail, download_gmail_attachments
# IMAP accounts → use list_imap_emails, search_imap_emails, read_imap_email, download_imap_attachments
# ======================================================================


# --- Discovery tools ---

@tool(
    name="list_email_accounts",
    description=(
        "List all connected email accounts and their provider keys. "
        "ALWAYS call this first before using any other email tool — "
        "it tells you which accounts are available and what provider key to use. "
        "Returns provider keys (e.g., 'gmail-nthanhtrung1987', 'yahoo'), account type (Gmail OAuth or IMAP), "
        "and connection status for each account. "
        "Use the provider key from the results as the 'provider' parameter in other IMAP email tools."
    ),
    input_schema={
        "type": "object",
        "properties": {}
    }
)
async def list_email_accounts(inputs: dict[str, Any]) -> dict[str, Any]:
    """List all connected email accounts."""
    username = get_username()
    return list_email_accounts_impl(username)


@tool(
    name="list_imap_folders",
    description=(
        "List all available folders/mailboxes for an IMAP email account. "
        "Use this to discover folders beyond INBOX — such as Sent, Drafts, Trash, Spam, Archive, "
        "or custom folders/labels the user has created. "
        "Useful when the user asks about sent emails, drafts, or emails in specific folders. "
        "The folder names returned can be used as the 'folder' parameter in list/search/read tools."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "provider": {
                "type": "string",
                "description": "Provider key from list_email_accounts (e.g., 'gmail-nthanhtrung1987', 'yahoo')"
            }
        },
        "required": ["provider"]
    }
)
async def list_imap_folders(inputs: dict[str, Any]) -> dict[str, Any]:
    """List IMAP folders."""
    username = get_username()
    provider = inputs["provider"]
    return list_imap_folders_impl(username, provider)


# --- Gmail tools (for Gmail OAuth accounts only) ---

@tool(
    name="list_gmail",
    description=(
        "List recent emails from a Gmail OAuth account. "
        "Use this for browsing/scanning recent emails when you don't need a specific search. "
        "For targeted searches, use search_gmail instead. "
        "Returns subject, sender, date, snippet, and message ID for each email. "
        "Use the message ID with read_gmail to see full content, or download_gmail_attachments to get files."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "provider": {
                "type": "string",
                "description": "Provider key for the Gmail account (e.g., 'gmail', 'gmail-nttrungassistant'). Optional — if omitted, uses first connected Gmail OAuth account."
            },
            "max_results": {
                "type": "integer",
                "description": "Number of emails to return (default: 10, max recommended: 50)",
                "default": 10
            },
            "query": {
                "type": "string",
                "description": (
                    "Optional Gmail search filter to narrow the list. "
                    "Uses Gmail search syntax: from:, to:, subject:, is:unread, has:attachment, "
                    "after:YYYY/MM/DD, before:YYYY/MM/DD. "
                    "Example: 'is:unread' to list only unread emails. Leave empty for all recent emails."
                ),
                "default": ""
            },
            "label": {
                "type": "string",
                "description": "Gmail label/folder: INBOX, UNREAD, STARRED, IMPORTANT, SENT, DRAFT, SPAM, TRASH (default: INBOX)",
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
    provider = inputs.get("provider", "")
    return list_gmail_impl(username, max_results, query, label, provider=provider)


@tool(
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
        "'is:unread from:boss@company.com' — unread emails from boss. "
        "'subject:\"meeting invite\" newer_than:7d' — recent meeting invites. "
        "'filename:pdf after:2026/01/01' — emails with PDF attachments this year. "
        "\n"
        "Tips: Keep queries simple (1-3 operators). If no results, broaden by removing filters. "
        "Returns message IDs — use read_gmail to see full content."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "provider": {
                "type": "string",
                "description": "Provider key for the Gmail account (e.g., 'gmail', 'gmail-nttrungassistant'). Optional — if omitted, uses first connected Gmail OAuth account."
            },
            "query": {
                "type": "string",
                "description": (
                    "Gmail search query. Use operators: from:, to:, subject:, has:attachment, "
                    "is:unread, after:YYYY/MM/DD, before:YYYY/MM/DD, filename:, newer_than:, older_than:. "
                    "Example: 'from:bank after:2026/02/01 has:attachment'"
                )
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum results to return (default: 10)",
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
    provider = inputs.get("provider", "")
    return search_gmail_impl(username, query, max_results, provider=provider)


@tool(
    name="read_gmail",
    description=(
        "Read the full content of a Gmail email — body text, HTML, headers, and attachment list. "
        "Requires a message ID from list_gmail or search_gmail. "
        "Use this when the user wants to see what an email says, check details, or review attachments before downloading. "
        "If the email has attachments, the response includes attachment IDs for use with download_gmail_attachments."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "provider": {
                "type": "string",
                "description": "Provider key for the Gmail account (e.g., 'gmail', 'gmail-nttrungassistant'). Optional — if omitted, uses first connected Gmail OAuth account."
            },
            "message_id": {
                "type": "string",
                "description": "Gmail message ID from list_gmail or search_gmail results"
            }
        },
        "required": ["message_id"]
    }
)
async def read_gmail(inputs: dict[str, Any]) -> dict[str, Any]:
    """Read a Gmail email."""
    username = get_username()
    message_id = inputs["message_id"]
    provider = inputs.get("provider", "")
    return read_gmail_impl(username, message_id, provider=provider)


@tool(
    name="download_gmail_attachments",
    description=(
        "Download attachments from a Gmail email to local storage. "
        "Requires a message ID from list_gmail, search_gmail, or read_gmail. "
        "By default downloads ALL attachments. Optionally specify attachment IDs (from read_gmail) "
        "to download only specific files. "
        "Returns the local file paths of downloaded attachments — use these paths to read or process the files. "
        "Common use cases: saving PDF invoices, downloading reports, extracting spreadsheet data."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "provider": {
                "type": "string",
                "description": "Provider key for the Gmail account (e.g., 'gmail', 'gmail-nttrungassistant'). Optional — if omitted, uses first connected Gmail OAuth account."
            },
            "message_id": {
                "type": "string",
                "description": "Gmail message ID"
            },
            "attachment_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional: specific attachment IDs from read_gmail. Omit to download all attachments."
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
    provider = inputs.get("provider", "")
    return download_gmail_attachments_impl(username, message_id, attachment_ids, provider=provider)


# --- Gmail write tools (for full-access Gmail accounts only) ---

@tool(
    name="send_gmail",
    description=(
        "Send a new email from your connected Gmail account. "
        "Only works for Gmail accounts with full access enabled (configured by admin). "
        "IMPORTANT: Always confirm with the user before sending — show them the recipient, subject, and body for approval. "
        "Returns the sent message ID on success."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "provider": {
                "type": "string",
                "description": "Provider key for the Gmail account (e.g., 'gmail', 'gmail-nttrungassistant'). Optional — if omitted, uses first connected Gmail OAuth account."
            },
            "to": {
                "type": "string",
                "description": "Recipient email address(es), comma-separated for multiple"
            },
            "subject": {
                "type": "string",
                "description": "Email subject line"
            },
            "body": {
                "type": "string",
                "description": "Email body text (plain text)"
            },
            "cc": {
                "type": "string",
                "description": "CC recipients, comma-separated (optional)",
                "default": ""
            },
            "bcc": {
                "type": "string",
                "description": "BCC recipients, comma-separated (optional)",
                "default": ""
            }
        },
        "required": ["to", "subject", "body"]
    }
)
async def send_gmail(inputs: dict[str, Any]) -> dict[str, Any]:
    """Send a Gmail email."""
    username = get_username()
    return send_gmail_impl(
        username,
        to=inputs["to"],
        subject=inputs["subject"],
        body=inputs["body"],
        cc=inputs.get("cc", ""),
        bcc=inputs.get("bcc", ""),
        provider=inputs.get("provider", ""),
    )


@tool(
    name="reply_gmail",
    description=(
        "Reply to an existing Gmail email. Automatically threads the reply with the original message. "
        "Only works for Gmail accounts with full access enabled. "
        "IMPORTANT: Always confirm with the user before sending — show them the reply content for approval. "
        "Requires a message ID from list_gmail, search_gmail, or read_gmail."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "provider": {
                "type": "string",
                "description": "Provider key for the Gmail account (e.g., 'gmail', 'gmail-nttrungassistant'). Optional — if omitted, uses first connected Gmail OAuth account."
            },
            "message_id": {
                "type": "string",
                "description": "Gmail message ID of the email to reply to"
            },
            "body": {
                "type": "string",
                "description": "Reply body text (plain text)"
            }
        },
        "required": ["message_id", "body"]
    }
)
async def reply_gmail(inputs: dict[str, Any]) -> dict[str, Any]:
    """Reply to a Gmail email."""
    username = get_username()
    return reply_gmail_impl(
        username,
        message_id=inputs["message_id"],
        body=inputs["body"],
        provider=inputs.get("provider", ""),
    )


@tool(
    name="create_gmail_draft",
    description=(
        "Create a draft email in your Gmail account without sending it. "
        "Only works for Gmail accounts with full access enabled. "
        "Useful when the user wants to prepare an email for later review and sending."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "provider": {
                "type": "string",
                "description": "Provider key for the Gmail account (e.g., 'gmail', 'gmail-nttrungassistant'). Optional — if omitted, uses first connected Gmail OAuth account."
            },
            "to": {
                "type": "string",
                "description": "Recipient email address(es), comma-separated for multiple"
            },
            "subject": {
                "type": "string",
                "description": "Email subject line"
            },
            "body": {
                "type": "string",
                "description": "Email body text (plain text)"
            },
            "cc": {
                "type": "string",
                "description": "CC recipients, comma-separated (optional)",
                "default": ""
            },
            "bcc": {
                "type": "string",
                "description": "BCC recipients, comma-separated (optional)",
                "default": ""
            }
        },
        "required": ["to", "subject", "body"]
    }
)
async def create_gmail_draft(inputs: dict[str, Any]) -> dict[str, Any]:
    """Create a Gmail draft."""
    username = get_username()
    return create_gmail_draft_impl(
        username,
        to=inputs["to"],
        subject=inputs["subject"],
        body=inputs["body"],
        cc=inputs.get("cc", ""),
        bcc=inputs.get("bcc", ""),
        provider=inputs.get("provider", ""),
    )


@tool(
    name="modify_gmail_message",
    description=(
        "Modify labels on a Gmail message: mark as read/unread, star/unstar, archive, or trash/untrash. "
        "Only works for Gmail accounts with full access enabled. "
        "Requires a message ID from list_gmail, search_gmail, or read_gmail."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "provider": {
                "type": "string",
                "description": "Provider key for the Gmail account (e.g., 'gmail', 'gmail-nttrungassistant'). Optional — if omitted, uses first connected Gmail OAuth account."
            },
            "message_id": {
                "type": "string",
                "description": "Gmail message ID to modify"
            },
            "action": {
                "type": "string",
                "description": "Action to perform: mark_read, mark_unread, star, unstar, archive, trash, untrash",
                "enum": ["mark_read", "mark_unread", "star", "unstar", "archive", "trash", "untrash"]
            }
        },
        "required": ["message_id", "action"]
    }
)
async def modify_gmail_message(inputs: dict[str, Any]) -> dict[str, Any]:
    """Modify a Gmail message."""
    username = get_username()
    return modify_gmail_impl(
        username,
        message_id=inputs["message_id"],
        action=inputs["action"],
        provider=inputs.get("provider", ""),
    )


# --- IMAP tools (for Yahoo, Outlook, iCloud, Zoho, Gmail via app password, custom) ---

@tool(
    name="list_imap_emails",
    description=(
        "List recent emails from an IMAP email account. "
        "Works with any IMAP provider: Yahoo, Outlook, iCloud, Zoho, Gmail (app password), or custom servers. "
        "Use this for browsing recent emails. For targeted searches, use search_imap_emails instead. "
        "Returns subject, sender, date, snippet, and message ID for each email. "
        "Use the message ID with read_imap_email to see full content, "
        "or download_imap_attachments to get files. "
        "To list emails in other folders (Sent, Drafts, etc.), use the folder parameter — "
        "call list_imap_folders first to discover available folders."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "provider": {
                "type": "string",
                "description": "Provider key from list_email_accounts (e.g., 'gmail-nthanhtrung1987', 'yahoo')"
            },
            "max_results": {
                "type": "integer",
                "description": "Number of emails to return (default: 10, max recommended: 50)",
                "default": 10
            },
            "folder": {
                "type": "string",
                "description": "IMAP folder (default: INBOX). Use list_imap_folders to discover available folders.",
                "default": "INBOX"
            }
        },
        "required": ["provider"]
    }
)
async def list_imap_emails(inputs: dict[str, Any]) -> dict[str, Any]:
    """List emails from an IMAP account."""
    username = get_username()
    provider = inputs["provider"]
    max_results = inputs.get("max_results", 10)
    folder = inputs.get("folder", "INBOX")
    return list_imap_impl(username, provider, max_results, folder)


@tool(
    name="search_imap_emails",
    description=(
        "Search emails in an IMAP account by sender, subject, date range, or keywords. "
        "Works with any IMAP provider: Yahoo, Outlook, iCloud, Zoho, Gmail (app password), or custom servers. "
        "\n"
        "Query syntax — use prefixes to target specific fields: "
        "  subject:TERM  — search in subject line (use quotes for phrases: subject:\"monthly report\") "
        "  from:ADDRESS  — search by sender email or name "
        "  to:ADDRESS    — search by recipient "
        "  since:DATE    — emails on or after date (any format: YYYY-MM-DD, YYYY/MM/DD, DD-Mon-YYYY) "
        "  before:DATE   — emails before date "
        "  Plain words without prefix search by subject. "
        "\n"
        "Examples: "
        "  'from:amazon since:2026-02-01' — emails from Amazon this month. "
        "  'subject:invoice' — emails with 'invoice' in subject. "
        "  'subject:\"meeting notes\" from:team@company.com' — specific subject from specific sender. "
        "  'since:2026-02-01 before:2026-02-28' — all emails in a date range. "
        "  'has:attachment from:boss' — (note: has: is Gmail-only, for IMAP use subject/from/date filters then check attachments via read). "
        "  'report' — simple keyword search in subject. "
        "\n"
        "Tips: "
        "- Keep queries simple — 1-2 prefixes work best. "
        "- If no results, broaden: remove date filters, try shorter keywords, or just use from: alone. "
        "- Multiple prefixes are AND-combined (all must match). "
        "- Dates are auto-converted — use whatever format is natural. "
        "- Returns message IDs — use read_imap_email to see full content."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "provider": {
                "type": "string",
                "description": "Provider key from list_email_accounts (e.g., 'gmail-nthanhtrung1987', 'yahoo')"
            },
            "query": {
                "type": "string",
                "description": (
                    "Search query. Prefixes: subject:, from:, to:, since:, before:. "
                    "Plain words search by subject. Dates accept any format (YYYY-MM-DD, YYYY/MM/DD). "
                    "Examples: 'from:bank since:2026-02-01', 'subject:\"monthly statement\"', 'invoice'"
                )
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum results to return (default: 10)",
                "default": 10
            },
            "folder": {
                "type": "string",
                "description": "IMAP folder to search (default: INBOX). Use list_imap_folders to discover available folders.",
                "default": "INBOX"
            }
        },
        "required": ["provider", "query"]
    }
)
async def search_imap_emails(inputs: dict[str, Any]) -> dict[str, Any]:
    """Search emails in an IMAP account."""
    username = get_username()
    provider = inputs["provider"]
    query = inputs["query"]
    max_results = inputs.get("max_results", 10)
    folder = inputs.get("folder", "INBOX")
    return search_imap_impl(username, provider, query, max_results, folder)


@tool(
    name="read_imap_email",
    description=(
        "Read the full content of an email from an IMAP account — body text, HTML, headers, and attachment list. "
        "Requires a message ID from list_imap_emails or search_imap_emails. "
        "Use this when the user wants to see what an email says, review details, or check attachments before downloading. "
        "If the email has attachments, the response lists filenames — "
        "use these with download_imap_attachments to save specific files. "
        "Make sure to use the same folder parameter as the list/search that returned the message ID."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "provider": {
                "type": "string",
                "description": "Provider key from list_email_accounts (e.g., 'gmail-nthanhtrung1987', 'yahoo')"
            },
            "message_id": {
                "type": "string",
                "description": "Message ID from list_imap_emails or search_imap_emails results"
            },
            "folder": {
                "type": "string",
                "description": "IMAP folder where the message is located (must match the folder used in list/search). Default: INBOX",
                "default": "INBOX"
            }
        },
        "required": ["provider", "message_id"]
    }
)
async def read_imap_email(inputs: dict[str, Any]) -> dict[str, Any]:
    """Read an email from an IMAP account."""
    username = get_username()
    provider = inputs["provider"]
    message_id = inputs["message_id"]
    folder = inputs.get("folder", "INBOX")
    return read_imap_impl(username, provider, message_id, folder)


@tool(
    name="download_imap_attachments",
    description=(
        "Download attachments from an IMAP email to local storage. "
        "Requires a message ID from list_imap_emails, search_imap_emails, or read_imap_email. "
        "By default downloads ALL attachments. Optionally specify filenames (from read_imap_email) "
        "to download only specific files. "
        "Returns the local file paths of downloaded attachments — use these paths to read or process the files "
        "(e.g., read PDFs, parse spreadsheets, extract data from documents). "
        "Make sure to use the same folder parameter as the list/search/read that returned the message ID."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "provider": {
                "type": "string",
                "description": "Provider key from list_email_accounts (e.g., 'gmail-nthanhtrung1987', 'yahoo')"
            },
            "message_id": {
                "type": "string",
                "description": "Message ID from list/search/read results"
            },
            "filenames": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional: specific attachment filenames from read_imap_email. Omit to download all attachments."
            },
            "folder": {
                "type": "string",
                "description": "IMAP folder where the message is located (must match the folder used in list/search/read). Default: INBOX",
                "default": "INBOX"
            }
        },
        "required": ["provider", "message_id"]
    }
)
async def download_imap_attachments(inputs: dict[str, Any]) -> dict[str, Any]:
    """Download attachments from an IMAP email."""
    username = get_username()
    provider = inputs["provider"]
    message_id = inputs["message_id"]
    filenames = inputs.get("filenames")
    folder = inputs.get("folder", "INBOX")
    return download_imap_attachments_impl(username, provider, message_id, filenames, folder)


def initialize_email_tools(username: str) -> None:
    """Initialize email tools for a user by loading and verifying credentials.

    This should be called after setting the username context to preload
    all credential information and log available accounts.

    Args:
        username: Username to load credentials for
    """
    try:
        cred_store = get_credential_store(username)
        accounts = cred_store.get_all_accounts()

        logger.info(f"Email tools initialized for user '{username}': {len(accounts)} accounts available")
        for acct in accounts:
            access_info = ""
            if acct.get("access_level") == "full_access":
                access_info = " (full_access)"
            logger.info(f"  - {acct['provider_name']}: {acct['email']} [{acct['auth_type']}]{access_info}")

    except Exception as e:
        logger.warning(f"Failed to initialize email tools for user '{username}': {e}")


# Create MCP server
email_tools_server = create_sdk_mcp_server(
    name="email_tools",
    version="1.0.0",
    tools=[
        # Discovery (call first)
        list_email_accounts,
        list_imap_folders,
        # Gmail OAuth tools (read)
        list_gmail,
        search_gmail,
        read_gmail,
        download_gmail_attachments,
        # Gmail OAuth tools (write — full-access accounts only)
        send_gmail,
        reply_gmail,
        create_gmail_draft,
        modify_gmail_message,
        # IMAP tools (Yahoo, Outlook, iCloud, Zoho, Gmail app password, custom)
        list_imap_emails,
        search_imap_emails,
        read_imap_email,
        download_imap_attachments,
    ]
)


__all__ = [
    "email_tools_server",
    "set_username",
    "reset_username",
    "get_username",
    "initialize_email_tools",
]
