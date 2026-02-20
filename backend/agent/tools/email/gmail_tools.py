"""Gmail API tools using OAuth 2.0 authentication.

Provides MCP tools for listing, reading, searching emails and downloading attachments.
"""
import base64
import email.utils
import logging
from typing import Any

from agent.tools.email.credential_store import get_credential_store, OAuthCredentials
from agent.tools.email.attachment_store import get_attachment_store
from agent.tools.email.formatting import format_email_preview, format_email_detail, make_tool_result
from core.settings import get_settings

logger = logging.getLogger(__name__)


class GmailClient:
    """Gmail API client with OAuth authentication."""

    SCOPES = [
        "https://www.googleapis.com/auth/gmail.modify",
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

    @staticmethod
    def _build_mime_message(
        to: str,
        subject: str,
        body: str,
        cc: str = "",
        bcc: str = "",
        in_reply_to: str = "",
        references: str = "",
    ) -> str:
        from email.mime.text import MIMEText

        msg = MIMEText(body, "plain", "utf-8")
        msg["To"] = to
        msg["Subject"] = subject
        if cc:
            msg["Cc"] = cc
        if bcc:
            msg["Bcc"] = bcc
        if in_reply_to:
            msg["In-Reply-To"] = in_reply_to
        if references:
            msg["References"] = references

        return base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")

    def send_message(
        self,
        to: str,
        subject: str,
        body: str,
        cc: str = "",
        bcc: str = "",
        thread_id: str = "",
        in_reply_to: str = "",
        references: str = "",
    ) -> dict[str, Any]:
        service = self._get_service()
        raw = self._build_mime_message(to, subject, body, cc, bcc, in_reply_to, references)
        message_body: dict[str, Any] = {"raw": raw}
        if thread_id:
            message_body["threadId"] = thread_id
        result = service.users().messages().send(userId="me", body=message_body).execute()
        logger.info(f"Sent Gmail message, id={result.get('id')}")
        return result

    def create_draft(
        self,
        to: str,
        subject: str,
        body: str,
        cc: str = "",
        bcc: str = "",
    ) -> dict[str, Any]:
        service = self._get_service()
        raw = self._build_mime_message(to, subject, body, cc, bcc)
        draft_body = {"message": {"raw": raw}}
        result = service.users().drafts().create(userId="me", body=draft_body).execute()
        logger.info(f"Created Gmail draft, id={result.get('id')}")
        return result

    def modify_labels(
        self,
        message_id: str,
        add_labels: list[str] | None = None,
        remove_labels: list[str] | None = None,
    ) -> dict[str, Any]:
        service = self._get_service()
        body: dict[str, Any] = {}
        if add_labels:
            body["addLabelIds"] = add_labels
        if remove_labels:
            body["removeLabelIds"] = remove_labels
        result = service.users().messages().modify(userId="me", id=message_id, body=body).execute()
        logger.info(f"Modified labels on Gmail message {message_id}")
        return result


def _with_gmail_credentials(
    username: str,
    provider: str = "",
) -> tuple[OAuthCredentials, GmailClient] | dict[str, Any]:
    """Load Gmail credentials and create client.

    Args:
        username: Username for credential lookup
        provider: Provider key (e.g., 'gmail', 'gmail-nttrungassistant'). If empty,
                  auto-discovers first Gmail OAuth account.

    Returns:
        Tuple of (credentials, client) on success, or MCP error result dict on failure.
    """
    cred_store = get_credential_store(username)

    if provider:
        credentials = cred_store.load_credentials(provider)
    else:
        # Auto-discover first Gmail OAuth account
        credentials = None
        for key in cred_store.get_connected_providers():
            if key.startswith("gmail"):
                creds = cred_store.load_credentials(key)
                if creds and creds.auth_type == "oauth":
                    credentials = creds
                    break

    if credentials is None:
        return make_tool_result(
            "Gmail account not connected. Please connect your Gmail account first."
        )

    return credentials, GmailClient(credentials, username=username)


def _is_full_access_account(email_address: str) -> bool:
    settings = get_settings()
    full_access_list = [
        e.strip().lower()
        for e in settings.email.gmail_full_access_emails.split(",")
        if e.strip()
    ]
    return email_address.lower() in full_access_list


def list_gmail_impl(
    username: str,
    max_results: int = 10,
    query: str = "",
    label: str = "INBOX",
    provider: str = "",
) -> dict[str, Any]:
    """List Gmail emails with filters."""
    result = _with_gmail_credentials(username, provider)
    if isinstance(result, dict):
        return result
    _, client = result

    try:
        label_map = {
            "ALL": [], "INBOX": ["INBOX"], "UNREAD": ["UNREAD"],
            "STARRED": ["STARRED"], "IMPORTANT": ["IMPORTANT"],
            "SENT": ["SENT"], "DRAFT": ["DRAFT"],
            "SPAM": ["SPAM"], "TRASH": ["TRASH"],
        }
        label_ids = label_map.get(label.upper(), ["INBOX"])

        messages = client.list_messages(
            max_results=max_results, query=query, label_ids=label_ids
        )

        if not messages:
            return make_tool_result(
                f"No emails found matching criteria (label: {label}, query: '{query}')"
            )

        previews = []
        for msg in messages:
            try:
                message = client.get_message(msg["id"], format="metadata")
                parsed = client.parse_message(message)
                parsed["snippet"] = parsed.get("snippet", "")[:200]
                previews.append(format_email_preview(parsed))
            except Exception as e:
                logger.warning(f"Failed to parse message {msg['id']}: {e}")
                previews.append(f"*Message ID: {msg['id']} (failed to parse)*")

        return make_tool_result(
            f"Found {len(previews)} emails:\n\n" + "\n".join(previews)
        )

    except RuntimeError as e:
        return make_tool_result(f"Gmail library not available: {e}")
    except Exception as e:
        logger.error(f"Failed to list Gmail: {e}")
        return make_tool_result(f"Failed to list Gmail: {e}")


def read_gmail_impl(username: str, message_id: str, provider: str = "") -> dict[str, Any]:
    """Read a full Gmail email."""
    result = _with_gmail_credentials(username, provider)
    if isinstance(result, dict):
        return result
    _, client = result

    try:
        message = client.get_message(message_id, format="full")
        parsed = client.parse_message(message)

        if parsed['has_attachments']:
            parsed["attachments"] = client.get_attachments(message_id)

        extra_fields = {
            "Message ID": parsed["id"],
            "Labels": ", ".join(parsed["label_ids"]),
        }
        formatted = format_email_detail(parsed, extra_fields=extra_fields)

        return make_tool_result(formatted)

    except Exception as e:
        logger.error(f"Failed to read Gmail {message_id}: {e}")
        return make_tool_result(f"Failed to read email: {e}")


def download_gmail_attachments_impl(
    username: str,
    message_id: str,
    attachment_ids: list[str] | None = None,
    provider: str = "",
) -> dict[str, Any]:
    """Download attachments from a Gmail email."""
    result = _with_gmail_credentials(username, provider)
    if isinstance(result, dict):
        return result
    _, client = result
    attachment_store = get_attachment_store(username)

    try:
        attachments = client.get_attachments(message_id)
        filename_map = {a["id"]: a["filename"] for a in attachments}

        if attachment_ids is None:
            attachment_ids = list(filename_map.keys())

        if not attachment_ids:
            return make_tool_result("No attachments found in this email.")

        downloaded = []
        for att_id in attachment_ids:
            try:
                content = client.download_attachment(message_id, att_id)
                filename = filename_map.get(att_id, f"attachment_{att_id}")
                filepath = attachment_store.save_attachment(
                    "gmail", message_id, filename, content
                )
                downloaded.append(str(filepath))
            except Exception as e:
                logger.warning(f"Failed to download attachment {att_id}: {e}")
                downloaded.append(f"Failed: {att_id}")

        return make_tool_result(
            f"Downloaded {len(downloaded)} attachment(s):\n\n" + "\n".join(downloaded)
        )

    except Exception as e:
        logger.error(f"Failed to download attachments: {e}")
        return make_tool_result(f"Failed to download attachments: {e}")


def search_gmail_impl(
    username: str,
    query: str,
    max_results: int = 10,
    provider: str = "",
) -> dict[str, Any]:
    """Search Gmail emails by query.

    Args:
        username: Username for credential lookup
        query: Gmail search query (e.g., "from:john@example.com important:yes")
        max_results: Maximum results (default 10)
        provider: Provider key (e.g., 'gmail', 'gmail-nttrungassistant'). If empty, auto-discovers.

    Returns:
        Tool result with matching emails
    """
    # Search is just list with query
    return list_gmail_impl(username, max_results=max_results, query=query, label="ALL", provider=provider)


def _check_full_access(username: str, provider: str = "") -> tuple[OAuthCredentials, GmailClient] | dict[str, Any]:
    result = _with_gmail_credentials(username, provider)
    if isinstance(result, dict):
        return result
    creds, client = result
    if not creds.email_address or not _is_full_access_account(creds.email_address):
        return make_tool_result(
            f"Send/modify access denied for {creds.email_address}. "
            "This Gmail account is read-only. Only accounts listed in "
            "GMAIL_FULL_ACCESS_EMAILS have send/modify permissions."
        )
    return creds, client


def send_gmail_impl(
    username: str,
    to: str,
    subject: str,
    body: str,
    cc: str = "",
    bcc: str = "",
    provider: str = "",
) -> dict[str, Any]:
    result = _check_full_access(username, provider)
    if isinstance(result, dict):
        return result
    creds, client = result

    try:
        sent = client.send_message(to=to, subject=subject, body=body, cc=cc, bcc=bcc)
        return make_tool_result(
            f"Email sent successfully from {creds.email_address}.\n"
            f"Message ID: {sent.get('id')}\n"
            f"To: {to}\nSubject: {subject}"
        )
    except Exception as e:
        logger.error(f"Failed to send Gmail: {e}")
        return make_tool_result(f"Failed to send email: {e}")


def reply_gmail_impl(
    username: str,
    message_id: str,
    body: str,
    provider: str = "",
) -> dict[str, Any]:
    result = _check_full_access(username, provider)
    if isinstance(result, dict):
        return result
    creds, client = result

    try:
        original = client.get_message(message_id, format="metadata")
        headers = {h["name"]: h["value"] for h in original.get("payload", {}).get("headers", [])}
        thread_id = original.get("threadId", "")
        subject = headers.get("Subject", "")
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"
        reply_to = headers.get("Reply-To") or headers.get("From", "")
        orig_message_id_header = headers.get("Message-ID", "")
        references = headers.get("References", "")
        if orig_message_id_header:
            references = f"{references} {orig_message_id_header}".strip()

        sent = client.send_message(
            to=reply_to,
            subject=subject,
            body=body,
            thread_id=thread_id,
            in_reply_to=orig_message_id_header,
            references=references,
        )
        return make_tool_result(
            f"Reply sent successfully from {creds.email_address}.\n"
            f"Message ID: {sent.get('id')}\n"
            f"To: {reply_to}\nSubject: {subject}"
        )
    except Exception as e:
        logger.error(f"Failed to reply Gmail: {e}")
        return make_tool_result(f"Failed to send reply: {e}")


def create_gmail_draft_impl(
    username: str,
    to: str,
    subject: str,
    body: str,
    cc: str = "",
    bcc: str = "",
    provider: str = "",
) -> dict[str, Any]:
    result = _check_full_access(username, provider)
    if isinstance(result, dict):
        return result
    creds, client = result

    try:
        draft = client.create_draft(to=to, subject=subject, body=body, cc=cc, bcc=bcc)
        return make_tool_result(
            f"Draft created successfully in {creds.email_address}.\n"
            f"Draft ID: {draft.get('id')}\n"
            f"To: {to}\nSubject: {subject}"
        )
    except Exception as e:
        logger.error(f"Failed to create Gmail draft: {e}")
        return make_tool_result(f"Failed to create draft: {e}")


def modify_gmail_impl(
    username: str,
    message_id: str,
    action: str,
    provider: str = "",
) -> dict[str, Any]:
    action_map = {
        "mark_read": ([], ["UNREAD"]),
        "mark_unread": (["UNREAD"], []),
        "star": (["STARRED"], []),
        "unstar": ([], ["STARRED"]),
        "archive": ([], ["INBOX"]),
        "trash": (["TRASH"], []),
        "untrash": ([], ["TRASH"]),
    }

    if action not in action_map:
        return make_tool_result(
            f"Unknown action '{action}'. Valid actions: {', '.join(action_map.keys())}"
        )

    result = _check_full_access(username, provider)
    if isinstance(result, dict):
        return result
    creds, client = result

    add_labels, remove_labels = action_map[action]

    try:
        client.modify_labels(message_id, add_labels=add_labels, remove_labels=remove_labels)
        return make_tool_result(
            f"Successfully applied '{action}' to message {message_id} in {creds.email_address}."
        )
    except Exception as e:
        logger.error(f"Failed to modify Gmail message: {e}")
        return make_tool_result(f"Failed to modify message: {e}")
