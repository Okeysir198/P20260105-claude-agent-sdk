"""Gmail API tools using OAuth 2.0 authentication.

Provides MCP tools for listing, reading, searching emails and downloading attachments.
"""
import base64
import email
import email.utils
import logging
from typing import Any

from agent.tools.email.credential_store import get_credential_store, OAuthCredentials
from agent.tools.email.attachment_store import get_attachment_store
from core.settings import get_settings

logger = logging.getLogger(__name__)


class GmailClient:
    """Gmail API client with OAuth authentication."""

    SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
    ]

    def __init__(self, credentials: OAuthCredentials, username: str | None = None):
        """Initialize Gmail client.

        Args:
            credentials: OAuth credentials for Gmail
            username: Username for persisting refreshed tokens back to credential store
        """
        self._credentials = credentials
        self._username = username
        self._service = None

    def _get_service(self):
        """Get or create Gmail API service.

        Uses client_id and client_secret from settings to enable automatic
        token refresh when the access token expires.

        Returns:
            Gmail API service instance
        """
        if self._service is not None:
            return self._service

        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            settings = get_settings()

            # Create Credentials with client_id/secret for automatic token refresh
            creds = Credentials(
                token=self._credentials.access_token,
                refresh_token=self._credentials.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.email.gmail_client_id,
                client_secret=settings.email.gmail_client_secret,
                scopes=self.SCOPES,
            )

            self._service = build("gmail", "v1", credentials=creds)

            # Check if token was refreshed during service creation
            if creds.token and creds.token != self._credentials.access_token:
                self._save_refreshed_credentials(creds)

            return self._service

        except ImportError as e:
            logger.error(f"Google libraries not installed: {e}")
            raise RuntimeError(
                "Gmail integration requires google-api-python-client and google-auth-oauthlib. "
                "Install with: pip install google-api-python-client google-auth-oauthlib"
            )
        except Exception as e:
            logger.error(f"Failed to create Gmail service: {e}")
            raise

    def _save_refreshed_credentials(self, creds) -> None:
        """Persist refreshed access token back to the credential store.

        Args:
            creds: Google Credentials object with refreshed token
        """
        if not self._username:
            logger.debug("No username set, skipping token persistence after refresh")
            return

        try:
            self._credentials.access_token = creds.token
            if creds.expiry:
                self._credentials.expires_at = creds.expiry.isoformat()

            cred_store = get_credential_store(self._username)
            cred_store.save_credentials(self._credentials)
            logger.info(f"Persisted refreshed Gmail token for user {self._username}")
        except Exception as e:
            logger.warning(f"Failed to persist refreshed Gmail token: {e}")

    def list_messages(
        self,
        max_results: int = 10,
        query: str = "",
        label_ids: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """List Gmail messages.

        Args:
            max_results: Maximum number of messages to return
            query: Gmail search query (e.g., "from:john@example.com", "is:unread")
            label_ids: List of label IDs to filter (e.g., ["INBOX", "UNREAD"])

        Returns:
            List of message dictionaries with id, threadId, snippet
        """
        service = self._get_service()

        try:
            results = service.users().messages().list(
                userId="me",
                maxResults=max_results,
                q=query,
                labelIds=label_ids or ["INBOX"]
            ).execute()

            messages = results.get("messages", [])
            logger.info(f"Listed {len(messages)} Gmail messages")
            return messages

        except Exception as e:
            logger.error(f"Failed to list Gmail messages: {e}")
            raise

    def get_message(self, message_id: str, format: str = "full") -> dict[str, Any]:
        """Get a Gmail message by ID.

        Args:
            message_id: Gmail message ID
            format: Message format ("full", "metadata", "minimal", "raw")

        Returns:
            Message dictionary with full details
        """
        service = self._get_service()

        try:
            message = service.users().messages().get(
                userId="me",
                id=message_id,
                format=format
            ).execute()

            logger.debug(f"Retrieved Gmail message {message_id}")
            return message

        except Exception as e:
            logger.error(f"Failed to get Gmail message {message_id}: {e}")
            raise

    def get_attachments(self, message_id: str) -> list[dict[str, Any]]:
        """Get attachment metadata from a message.

        Args:
            message_id: Gmail message ID

        Returns:
            List of attachment dictionaries with id, filename, size
        """
        message = self.get_message(message_id, format="full")
        attachments = []

        def find_attachments(payload: dict):
            """Recursively find attachments in message payload."""
            if "parts" in payload:
                for part in payload["parts"]:
                    body = part.get("body", {})
                    if "attachmentId" in body:
                        attachments.append({
                            "id": body["attachmentId"],
                            "filename": part.get("filename", "unknown"),
                            "size": body.get("size", 0),
                            "mimeType": part.get("mimeType", "application/octet-stream")
                        })
                    # Recurse into nested parts
                    find_attachments(part)

        payload = message.get("payload", {})
        find_attachments(payload)

        return attachments

    def download_attachment(self, message_id: str, attachment_id: str) -> bytes:
        """Download an attachment.

        Args:
            message_id: Gmail message ID
            attachment_id: Attachment ID

        Returns:
            Attachment content as bytes
        """
        service = self._get_service()

        try:
            attachment = service.users().messages().attachments().get(
                userId="me",
                messageId=message_id,
                id=attachment_id
            ).execute()

            # Decode base64 data
            data = attachment.get("data", "")
            content = base64.urlsafe_b64decode(data)

            logger.debug(f"Downloaded attachment {attachment_id}")
            return content

        except Exception as e:
            logger.error(f"Failed to download attachment {attachment_id}: {e}")
            raise

    def parse_message(self, message: dict[str, Any]) -> dict[str, Any]:
        """Parse Gmail message into readable format.

        Args:
            message: Gmail message dict from API

        Returns:
            Parsed message with subject, from, to, date, body
        """
        payload = message.get("payload", {})
        headers = {h["name"]: h["value"] for h in payload.get("headers", [])}

        # Extract body text
        body = ""
        def extract_body(payload_part: dict):
            nonlocal body
            if "body" in payload_part and "data" in payload_part["body"]:
                data = payload_part["body"]["data"]
                try:
                    body = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
                except Exception:
                    body = "[Could not decode message body]"
            elif "parts" in payload_part:
                for part in payload_part["parts"]:
                    if part.get("mimeType", "") == "text/plain":
                        extract_body(part)
                        break

        extract_body(payload)

        # Parse date
        date_str = headers.get("Date", "")
        try:
            # Parse RFC 2822 date
            date_obj = email.utils.parsedate_to_datetime(date_str)
            date_formatted = date_obj.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            date_formatted = date_str

        return {
            "id": message.get("id"),
            "thread_id": message.get("threadId"),
            "subject": headers.get("Subject", "(No subject)"),
            "from": headers.get("From", ""),
            "to": headers.get("To", ""),
            "date": date_formatted,
            "snippet": message.get("snippet", ""),
            "body": body,
            "label_ids": message.get("labelIds", []),
            "has_attachments": any(
                "attachmentId" in part.get("body", {})
                for part in payload.get("parts", [])
            )
        }


def list_gmail_impl(
    username: str,
    max_results: int = 10,
    query: str = "",
    label: str = "INBOX"
) -> dict[str, Any]:
    """List Gmail emails with filters.

    Args:
        username: Username for credential lookup
        max_results: Maximum number of emails to return (default 10)
        query: Optional Gmail search query (e.g., "from:john@example.com", "is:unread")
        label: Label filter (INBOX, UNREAD, STARRED, IMPORTANT, etc.)

    Returns:
        Tool result with email list
    """
    # Get credentials
    cred_store = get_credential_store(username)
    credentials = cred_store.load_credentials("gmail")

    if credentials is None:
        return {
            "content": [{
                "type": "text",
                "text": "Gmail account not connected. Please connect your Gmail account first."
            }]
        }

    try:
        # Map label name to label ID
        label_map = {
            "ALL": [],
            "INBOX": ["INBOX"],
            "UNREAD": ["UNREAD"],
            "STARRED": ["STARRED"],
            "IMPORTANT": ["IMPORTANT"],
            "SENT": ["SENT"],
            "DRAFT": ["DRAFT"],
            "SPAM": ["SPAM"],
            "TRASH": ["TRASH"],
        }
        label_ids = label_map.get(label.upper(), ["INBOX"])

        # Create client and fetch messages
        client = GmailClient(credentials, username=username)
        messages = client.list_messages(
            max_results=max_results,
            query=query,
            label_ids=label_ids
        )

        if not messages:
            return {
                "content": [{
                    "type": "text",
                    "text": f"No emails found matching criteria (label: {label}, query: '{query}')"
                }]
            }

        # Fetch details for each message
        email_list = []
        for msg in messages:
            try:
                message = client.get_message(msg["id"], format="metadata")
                parsed = client.parse_message(message)
                email_list.append(f"""
**Subject:** {parsed['subject']}
**From:** {parsed['from']}
**Date:** {parsed['date']}
**ID:** {parsed['id']}
---
{parsed['snippet'][:200]}
""")
            except Exception as e:
                logger.warning(f"Failed to parse message {msg['id']}: {e}")
                email_list.append(f"*Message ID: {msg['id']} (failed to parse)*")

        return {
            "content": [{
                "type": "text",
                "text": f"Found {len(email_list)} emails:\n\n" + "\n".join(email_list)
            }]
        }

    except RuntimeError as e:
        return {
            "content": [{
                "type": "text",
                "text": f"Gmail library not available: {e}"
            }]
        }
    except Exception as e:
        logger.error(f"Failed to list Gmail: {e}")
        return {
            "content": [{
                "type": "text",
                "text": f"Failed to list Gmail: {str(e)}"
            }]
        }


def read_gmail_impl(username: str, message_id: str) -> dict[str, Any]:
    """Read a full Gmail email.

    Args:
        username: Username for credential lookup
        message_id: Gmail message ID

    Returns:
        Tool result with full email content
    """
    cred_store = get_credential_store(username)
    credentials = cred_store.load_credentials("gmail")

    if credentials is None:
        return {
            "content": [{
                "type": "text",
                "text": "Gmail account not connected. Please connect your Gmail account first."
            }]
        }

    try:
        client = GmailClient(credentials, username=username)
        message = client.get_message(message_id, format="full")
        parsed = client.parse_message(message)

        # Format email body
        formatted = f"""
**Subject:** {parsed['subject']}
**From:** {parsed['from']}
**To:** {parsed['to']}
**Date:** {parsed['date']}
**Message ID:** {parsed['id']}
**Labels:** {', '.join(parsed['label_ids'])}
**Has Attachments:** {'Yes' if parsed['has_attachments'] else 'No'}

---
{parsed['body']}
"""

        # List attachments if any
        if parsed['has_attachments']:
            attachments = client.get_attachments(message_id)
            if attachments:
                formatted += f"\n\n**Attachments ({len(attachments)}):**\n"
                for att in attachments:
                    formatted += f"- {att['filename']} ({att['size']} bytes, {att['mimeType']})\n"

        return {
            "content": [{
                "type": "text",
                "text": formatted
            }]
        }

    except Exception as e:
        logger.error(f"Failed to read Gmail {message_id}: {e}")
        return {
            "content": [{
                "type": "text",
                "text": f"Failed to read email: {str(e)}"
            }]
        }


def download_gmail_attachments_impl(
    username: str,
    message_id: str,
    attachment_ids: list[str] | None = None
) -> dict[str, Any]:
    """Download attachments from a Gmail email.

    Args:
        username: Username for credential lookup
        message_id: Gmail message ID
        attachment_ids: Optional list of specific attachment IDs to download. If None, downloads all.

    Returns:
        Tool result with download paths
    """
    cred_store = get_credential_store(username)
    credentials = cred_store.load_credentials("gmail")
    attachment_store = get_attachment_store(username)

    if credentials is None:
        return {
            "content": [{
                "type": "text",
                "text": "Gmail account not connected. Please connect your Gmail account first."
            }]
        }

    try:
        client = GmailClient(credentials, username=username)

        # Get attachments if not specified
        if attachment_ids is None:
            attachments = client.get_attachments(message_id)
            attachment_ids = [a["id"] for a in attachments]

        if not attachment_ids:
            return {
                "content": [{
                    "type": "text",
                    "text": "No attachments found in this email."
                }]
            }

        # Fetch message once to resolve attachment filenames
        message = client.get_message(message_id, format="full")

        def _build_filename_map(payload: dict) -> dict[str, str]:
            """Build a map of attachment_id -> filename from message payload."""
            result = {}
            if "parts" in payload:
                for part in payload["parts"]:
                    body = part.get("body", {})
                    aid = body.get("attachmentId")
                    if aid:
                        result[aid] = part.get("filename", f"attachment_{aid}")
                    result.update(_build_filename_map(part))
            return result

        filename_map = _build_filename_map(message.get("payload", {}))

        # Download each attachment
        downloaded = []
        for att_id in attachment_ids:
            try:
                content = client.download_attachment(message_id, att_id)
                filename = filename_map.get(att_id, f"attachment_{att_id}")

                # Save to attachment store
                filepath = attachment_store.save_attachment(
                    "gmail", message_id, filename, content
                )
                downloaded.append(str(filepath))

            except Exception as e:
                logger.warning(f"Failed to download attachment {att_id}: {e}")
                downloaded.append(f"Failed: {att_id}")

        return {
            "content": [{
                "type": "text",
                "text": f"Downloaded {len(downloaded)} attachment(s):\n\n" + "\n".join(downloaded)
            }]
        }

    except Exception as e:
        logger.error(f"Failed to download attachments: {e}")
        return {
            "content": [{
                "type": "text",
                "text": f"Failed to download attachments: {str(e)}"
            }]
        }


def search_gmail_impl(
    username: str,
    query: str,
    max_results: int = 10
) -> dict[str, Any]:
    """Search Gmail emails by query.

    Args:
        username: Username for credential lookup
        query: Gmail search query (e.g., "from:john@example.com important:yes")
        max_results: Maximum results (default 10)

    Returns:
        Tool result with matching emails
    """
    # Search is just list with query
    return list_gmail_impl(username, max_results=max_results, query=query, label="ALL")
