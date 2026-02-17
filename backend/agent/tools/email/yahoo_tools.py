"""Yahoo Mail tools using OAuth 2.0 and IMAP.

Provides MCP tools for listing, reading emails and downloading attachments via IMAP.
"""
import email
import email.header
import imaplib
import logging
from email import policy
from email.message import EmailMessage
from typing import Any

from agent.tools.email.credential_store import get_credential_store, OAuthCredentials
from agent.tools.email.attachment_store import get_attachment_store

logger = logging.getLogger(__name__)


class YahooIMAPClient:
    """Yahoo Mail IMAP client with OAuth authentication."""

    IMAP_SERVER = "imap.mail.yahoo.com"
    IMAP_PORT = 993

    def __init__(self, credentials: OAuthCredentials):
        """Initialize Yahoo IMAP client.

        Args:
            credentials: OAuth credentials for Yahoo
        """
        self._credentials = credentials
        self._client = None
        self._authenticated = False

    def _authenticate(self):
        """Authenticate with Yahoo IMAP using OAuth.

        Yahoo requires using app-specific password for IMAP access.
        """
        if self._authenticated and self._client:
            return

        try:
            # Create IMAP client
            self._client = imaplib.IMAP4_SSL(self.IMAP_SERVER, self.IMAP_PORT)

            # For Yahoo, we use app password stored as refresh_token
            # This is a workaround since Yahoo doesn't support OAuth for IMAP directly
            app_password = self._credentials.refresh_token

            # Login with email and app password
            email_address = self._credentials.email_address or ""
            self._client.login(email_address, app_password)
            self._authenticated = True

            logger.info("Authenticated with Yahoo IMAP")

        except Exception as e:
            logger.error(f"Failed to authenticate with Yahoo IMAP: {e}")
            self._client = None
            raise

    def list_messages(
        self,
        folder: str = "INBOX",
        criteria: str = "ALL",
        limit: int = 10
    ) -> list[dict[str, Any]]:
        """List Yahoo Mail messages.

        Args:
            folder: IMAP folder name (default: INBOX)
            criteria: IMAP search criteria (e.g., "UNSEEN", "FROM sender@example.com")
            limit: Maximum number of messages

        Returns:
            List of message dictionaries
        """
        self._authenticate()

        try:
            # Select folder
            self._client.select(folder)

            # Search messages
            status, messages = self._client.search(None, criteria)
            if status != "OK":
                return []

            msg_ids = messages[0].split()
            # Get the most recent messages
            msg_ids = msg_ids[-limit:] if len(msg_ids) > limit else msg_ids

            result = []
            for msg_id in reversed(msg_ids):
                # Fetch message headers
                status, msg_data = self._client.fetch(msg_id, "(RFC822.HEADER)")
                if status == "OK":
                    raw_header = msg_data[0][1]
                    msg = email.message_from_bytes(raw_header, policy=policy.default)

                    result.append({
                        "id": msg_id.decode(),
                        "subject": self._decode_header(msg.get("Subject", "(No subject)")),
                        "from": self._decode_header(msg.get("From", "")),
                        "date": msg.get("Date", ""),
                        "snippet": "[Full content available when reading message]"
                    })

            logger.info(f"Listed {len(result)} Yahoo messages")
            return result

        except Exception as e:
            logger.error(f"Failed to list Yahoo messages: {e}")
            raise
        finally:
            try:
                self._client.close()
            except Exception:
                pass

    def get_message(self, msg_id: str, folder: str = "INBOX") -> EmailMessage:
        """Get a full Yahoo Mail message.

        Args:
            msg_id: IMAP message ID
            folder: IMAP folder name

        Returns:
            EmailMessage object
        """
        self._authenticate()

        try:
            self._client.select(folder)
            status, msg_data = self._client.fetch(msg_id, "(RFC822)")

            if status != "OK":
                raise ValueError(f"Failed to fetch message {msg_id}")

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email, policy=policy.default)

            return msg

        except Exception as e:
            logger.error(f"Failed to get Yahoo message {msg_id}: {e}")
            raise
        finally:
            try:
                self._client.close()
            except Exception:
                pass

    def get_attachments(self, msg: EmailMessage) -> list[dict[str, Any]]:
        """Get attachment list from a message.

        Args:
            msg: EmailMessage object

        Returns:
            List of attachment info dicts
        """
        attachments = []

        for part in msg.walk():
            if part.get_content_maintype() == "multipart":
                continue
            if part.get("Content-Disposition") is None:
                continue

            filename = part.get_filename()
            if filename:
                attachments.append({
                    "filename": filename,
                    "content_type": part.get_content_type(),
                    "size": len(part.get_payload(decode=True) or b"")
                })

        return attachments

    def download_attachment(self, msg: EmailMessage, filename: str) -> bytes:
        """Download an attachment from a message.

        Args:
            msg: EmailMessage object
            filename: Attachment filename

        Returns:
            Attachment content as bytes
        """
        for part in msg.walk():
            if part.get_content_maintype() == "multipart":
                continue
            if part.get("Content-Disposition") is None:
                continue

            if part.get_filename() == filename:
                content = part.get_payload(decode=True)
                if content:
                    return content

        raise ValueError(f"Attachment not found: {filename}")

    def _decode_header(self, header: str) -> str:
        """Decode email header (handles encoded words).

        Args:
            header: Raw header value

        Returns:
            Decoded string
        """
        try:
            decoded_parts = email.header.decode_header(header)
            decoded_string = ""
            for content, encoding in decoded_parts:
                if isinstance(content, bytes):
                    decoded_string += content.decode(encoding or "utf-8", errors="replace")
                else:
                    decoded_string += content
            return decoded_string
        except Exception:
            return header

    def parse_message(self, msg: EmailMessage) -> dict[str, Any]:
        """Parse Yahoo email into readable format.

        Args:
            msg: EmailMessage object

        Returns:
            Parsed message dict
        """
        # Extract body
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        body = payload.decode("utf-8", errors="replace")
                        break
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode("utf-8", errors="replace")

        # Check for attachments
        attachments = self.get_attachments(msg)

        return {
            "subject": self._decode_header(msg.get("Subject", "(No subject)")),
            "from": self._decode_header(msg.get("From", "")),
            "to": self._decode_header(msg.get("To", "")),
            "date": msg.get("Date", ""),
            "body": body,
            "has_attachments": len(attachments) > 0,
            "attachments": attachments
        }

    def __enter__(self):
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up IMAP connection on context exit."""
        self.close()
        return False

    def close(self):
        """Explicitly close the IMAP connection."""
        if self._client:
            try:
                self._client.logout()
            except Exception:
                pass
            finally:
                self._client = None
                self._authenticated = False


def list_yahoo_impl(
    username: str,
    max_results: int = 10,
    folder: str = "INBOX"
) -> dict[str, Any]:
    """List Yahoo Mail emails.

    Args:
        username: Username for credential lookup
        max_results: Maximum number of emails (default 10)
        folder: IMAP folder (default: INBOX)

    Returns:
        Tool result with email list
    """
    cred_store = get_credential_store(username)
    credentials = cred_store.load_credentials("yahoo")

    if credentials is None:
        return {
            "content": [{
                "type": "text",
                "text": "Yahoo Mail account not connected. Please connect your Yahoo account first."
            }]
        }

    try:
        with YahooIMAPClient(credentials) as client:
            messages = client.list_messages(folder=folder, limit=max_results)

            if not messages:
                return {
                    "content": [{
                        "type": "text",
                        "text": f"No emails found in {folder}"
                    }]
                }

            email_list = []
            for msg in messages:
                email_list.append(f"""
**Subject:** {msg['subject']}
**From:** {msg['from']}
**Date:** {msg['date']}
**ID:** {msg['id']}
---
{msg['snippet']}
""")

            return {
                "content": [{
                    "type": "text",
                    "text": f"Found {len(email_list)} emails:\n\n" + "\n".join(email_list)
                }]
            }

    except Exception as e:
        logger.error(f"Failed to list Yahoo Mail: {e}")
        return {
            "content": [{
                "type": "text",
                "text": f"Failed to list Yahoo Mail: {str(e)}"
            }]
        }


def read_yahoo_impl(username: str, message_id: str, folder: str = "INBOX") -> dict[str, Any]:
    """Read a full Yahoo Mail email.

    Args:
        username: Username for credential lookup
        message_id: IMAP message ID
        folder: IMAP folder (default: INBOX)

    Returns:
        Tool result with full email content
    """
    cred_store = get_credential_store(username)
    credentials = cred_store.load_credentials("yahoo")

    if credentials is None:
        return {
            "content": [{
                "type": "text",
                "text": "Yahoo Mail account not connected. Please connect your Yahoo account first."
            }]
        }

    try:
        with YahooIMAPClient(credentials) as client:
            msg = client.get_message(message_id, folder=folder)
            parsed = client.parse_message(msg)

            formatted = f"""
**Subject:** {parsed['subject']}
**From:** {parsed['from']}
**To:** {parsed['to']}
**Date:** {parsed['date']}
**Has Attachments:** {'Yes' if parsed['has_attachments'] else 'No'}

---
{parsed['body']}
"""

            # List attachments if any
            if parsed['has_attachments']:
                formatted += f"\n\n**Attachments ({len(parsed['attachments'])}):**\n"
                for att in parsed['attachments']:
                    formatted += f"- {att['filename']} ({att['size']} bytes, {att['content_type']})\n"

            return {
                "content": [{
                    "type": "text",
                    "text": formatted
                }]
            }

    except Exception as e:
        logger.error(f"Failed to read Yahoo message {message_id}: {e}")
        return {
            "content": [{
                "type": "text",
                "text": f"Failed to read email: {str(e)}"
            }]
        }


def download_yahoo_attachments_impl(
    username: str,
    message_id: str,
    filenames: list[str] | None = None,
    folder: str = "INBOX"
) -> dict[str, Any]:
    """Download attachments from a Yahoo Mail email.

    Args:
        username: Username for credential lookup
        message_id: IMAP message ID
        filenames: Optional list of specific filenames to download. If None, downloads all.
        folder: IMAP folder (default: INBOX)

    Returns:
        Tool result with download paths
    """
    cred_store = get_credential_store(username)
    credentials = cred_store.load_credentials("yahoo")
    attachment_store = get_attachment_store(username)

    if credentials is None:
        return {
            "content": [{
                "type": "text",
                "text": "Yahoo Mail account not connected. Please connect your Yahoo account first."
            }]
        }

    try:
        with YahooIMAPClient(credentials) as client:
            msg = client.get_message(message_id, folder=folder)

            # Get attachments if not specified
            attachments = client.get_attachments(msg)
            if filenames is None:
                filenames = [a["filename"] for a in attachments]

            if not filenames:
                return {
                    "content": [{
                        "type": "text",
                        "text": "No attachments found in this email."
                    }]
                }

            # Download each attachment
            downloaded = []
            for filename in filenames:
                try:
                    content = client.download_attachment(msg, filename)
                    filepath = attachment_store.save_attachment(
                        "yahoo", message_id, filename, content
                    )
                    downloaded.append(str(filepath))
                except Exception as e:
                    logger.warning(f"Failed to download attachment {filename}: {e}")
                    downloaded.append(f"Failed: {filename}")

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
