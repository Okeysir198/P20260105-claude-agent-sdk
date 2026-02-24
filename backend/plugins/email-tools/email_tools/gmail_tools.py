"""Gmail API tools using OAuth 2.0 authentication."""
import base64
import email.utils
import logging
import os
from typing import Any

from .credential_store import get_credential_store, OAuthCredentials
from .attachment_store import get_attachment_store
from .formatting import format_email_preview, format_email_detail, make_tool_result
from . import email_templates
from . import attachment_utils

logger = logging.getLogger(__name__)


def _get_default_from_name() -> str:
    """Get default from name from settings."""
    try:
        from core.settings import get_settings
        return get_settings().platform.bot_name
    except Exception:
        return "Trung Assistant Bot"


class GmailClient:
    """Gmail API client with OAuth authentication."""

    SCOPES = [
        "https://www.googleapis.com/auth/gmail.modify",
    ]

    def __init__(self, credentials: OAuthCredentials, username: str | None = None):
        self._credentials = credentials
        self._username = username
        self._service = None

    def _get_service(self):
        """Get or create Gmail API service with automatic token refresh."""
        if self._service is not None:
            return self._service

        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            client_id = os.getenv("EMAIL_GMAIL_CLIENT_ID", "")
            client_secret = os.getenv("EMAIL_GMAIL_CLIENT_SECRET", "")

            creds = Credentials(
                token=self._credentials.access_token,
                refresh_token=self._credentials.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_id,
                client_secret=client_secret,
                scopes=self.SCOPES,
            )

            self._service = build("gmail", "v1", credentials=creds)

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
        """Persist refreshed access token back to the credential store."""
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
        label_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """List Gmail messages with optional query and label filters."""
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
        """Get a Gmail message by ID."""
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
        """Get attachment metadata from a message."""
        message = self.get_message(message_id, format="full")
        attachments = []

        def find_attachments(payload: dict):
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
                    find_attachments(part)

        payload = message.get("payload", {})
        find_attachments(payload)

        return attachments

    def download_attachment(self, message_id: str, attachment_id: str) -> bytes:
        """Download an attachment by ID and return its content as bytes."""
        service = self._get_service()

        try:
            attachment = service.users().messages().attachments().get(
                userId="me",
                messageId=message_id,
                id=attachment_id
            ).execute()

            data = attachment.get("data", "")
            content = base64.urlsafe_b64decode(data)

            logger.debug(f"Downloaded attachment {attachment_id}")
            return content

        except Exception as e:
            logger.error(f"Failed to download attachment {attachment_id}: {e}")
            raise

    def parse_message(self, message: dict[str, Any]) -> dict[str, Any]:
        """Parse Gmail message into readable format."""
        payload = message.get("payload", {})
        headers = {h["name"]: h["value"] for h in payload.get("headers", [])}

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

        date_str = headers.get("Date", "")
        try:
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

    @staticmethod
    def _build_mime_message_with_attachments(
        to: str,
        subject: str,
        body: str,
        cc: str = "",
        bcc: str = "",
        in_reply_to: str = "",
        references: str = "",
        attachments: list[dict] | None = None,
        html_body: str | None = None,
        from_name: str = "",
    ) -> str:
        """Build MIME message with optional HTML body and file attachments."""
        # Use default from_name if not provided
        if not from_name:
            from_name = _get_default_from_name()

        from email.mime.application import MIMEApplication
        from email.mime.audio import MIMEAudio
        from email.mime.image import MIMEImage
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        if attachments:
            msg = MIMEMultipart("mixed")
        elif html_body:
            msg = MIMEMultipart("alternative")
        else:
            msg = MIMEText(body, "plain", "utf-8")

        msg["To"] = to
        msg["Subject"] = subject
        msg["From"] = from_name
        if cc:
            msg["Cc"] = cc
        if bcc:
            msg["Bcc"] = bcc
        if in_reply_to:
            msg["In-Reply-To"] = in_reply_to
        if references:
            msg["References"] = references

        if attachments:
            alt_part = MIMEMultipart("alternative")
            alt_part.attach(MIMEText(body, "plain", "utf-8"))
            if html_body:
                alt_part.attach(MIMEText(html_body, "html", "utf-8"))
            msg.attach(alt_part)

            for attachment in attachments:
                data = attachment.get("data")
                filename = attachment.get("filename", "attachment")
                mime_type = attachment.get("mime_type", "application/octet-stream")

                if not data:
                    logger.warning(f"Skipping attachment {filename}: no data")
                    continue

                main_type, _, sub_type = mime_type.partition("/")
                if not sub_type:
                    main_type, sub_type = "application", "octet-stream"

                if main_type == "text":
                    part = MIMEText(data.decode("utf-8", errors="replace"), _subtype=sub_type, _charset="utf-8")
                elif main_type == "image":
                    part = MIMEImage(data, _subtype=sub_type)
                elif main_type == "audio":
                    part = MIMEAudio(data, _subtype=sub_type)
                else:
                    part = MIMEApplication(data, _subtype=sub_type)

                part.add_header("Content-Disposition", "attachment", filename=filename)
                msg.attach(part)

        elif html_body:
            msg.attach(MIMEText(body, "plain", "utf-8"))
            msg.attach(MIMEText(html_body, "html", "utf-8"))

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
        attachments: list[dict] | None = None,
        html_body: str | None = None,
        from_name: str = "",
    ) -> dict[str, Any]:
        """Send a Gmail message with optional attachments and HTML body."""
        if not from_name:
            from_name = _get_default_from_name()
        service = self._get_service()

        if attachments or html_body:
            raw = self._build_mime_message_with_attachments(
                to=to,
                subject=subject,
                body=body,
                cc=cc,
                bcc=bcc,
                in_reply_to=in_reply_to,
                references=references,
                attachments=attachments,
                html_body=html_body,
                from_name=from_name,
            )
            logger.info(f"Building MIME message with {len(attachments or [])} attachment(s), HTML={bool(html_body)}")
        else:
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
        attachments: list[dict] | None = None,
        html_body: str | None = None,
        from_name: str = "",
    ) -> dict[str, Any]:
        """Create a Gmail draft with optional attachments and HTML body."""
    if not from_name:
        from_name = _get_default_from_name()
        if not from_name:
            from_name = _get_default_from_name()
        service = self._get_service()

        if attachments or html_body:
            raw = self._build_mime_message_with_attachments(
                to=to,
                subject=subject,
                body=body,
                cc=cc,
                bcc=bcc,
                attachments=attachments,
                html_body=html_body,
                from_name=from_name,
            )
            logger.info(f"Building MIME draft with {len(attachments or [])} attachment(s), HTML={bool(html_body)}")
        else:
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
    """Load Gmail credentials and create client. Auto-discovers if provider is empty."""
    cred_store = get_credential_store(username)

    if provider:
        credentials = cred_store.load_credentials(provider)
    else:
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
    full_access_env = os.getenv("EMAIL_GMAIL_FULL_ACCESS_EMAILS", "")
    full_access_list = [
        e.strip().lower()
        for e in full_access_env.split(",")
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
    """Search Gmail emails by query."""
    return list_gmail_impl(username, max_results=max_results, query=query, label="ALL", provider=provider)


def _check_full_access(username: str, provider: str = "") -> tuple[OAuthCredentials, GmailClient] | dict[str, Any]:
    """Load Gmail credentials and verify full access permissions."""
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


def _prepare_html_and_attachments(
    body: str,
    html_body: str | None,
    attachments: list[dict] | None,
    username: str,
    session_id: str | None,
) -> tuple[str | None, list[dict] | None]:
    """Auto-generate HTML body and resolve/load attachment files.

    Returns (final_html_body, resolved_attachments).
    """
    final_html_body = html_body
    if not final_html_body and body:
        final_html_body = email_templates.format_body_as_html(body)

    resolved_attachments = None
    if attachments:
        resolved_attachments = attachment_utils.resolve_attachments(
            attachments, username, session_id=session_id
        )
        for att in resolved_attachments:
            with open(att["path"], "rb") as f:
                att["data"] = f.read()
        logger.info(f"Resolved {len(resolved_attachments)} attachment(s)")

    return final_html_body, resolved_attachments


def _format_send_info(
    resolved_attachments: list[dict] | None,
    final_html_body: str | None,
) -> str:
    """Build the attachment/HTML info suffix for send result messages."""
    info = ""
    if resolved_attachments:
        info = f"\nAttachments: {len(resolved_attachments)} file(s)"
    if final_html_body:
        info += "\nHTML body: Yes"
    return info


def send_gmail_impl(
    username: str,
    to: str,
    subject: str,
    body: str,
    cc: str = "",
    bcc: str = "",
    provider: str = "",
    attachments: list[dict] | None = None,
    html_body: str | None = None,
    from_name: str = "",
    session_id: str | None = None,
) -> dict[str, Any]:
    """Send a Gmail email with optional attachments and HTML body."""
    if not from_name:
        from_name = _get_default_from_name()
    result = _check_full_access(username, provider)
    if isinstance(result, dict):
        return result
    creds, client = result

    try:
        final_html_body, resolved_attachments = _prepare_html_and_attachments(
            body, html_body, attachments, username, session_id
        )

        sent = client.send_message(
            to=to, subject=subject, body=body, cc=cc, bcc=bcc,
            attachments=resolved_attachments, html_body=final_html_body,
            from_name=from_name,
        )

        info = _format_send_info(resolved_attachments, final_html_body)
        return make_tool_result(
            f"Email sent successfully from {creds.email_address}.{info}\n"
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
    attachments: list[dict] | None = None,
    html_body: str | None = None,
    from_name: str = "",
    session_id: str | None = None,
) -> dict[str, Any]:
    """Reply to a Gmail message with optional attachments and HTML body."""
    if not from_name:
        from_name = _get_default_from_name()
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

        final_html_body, resolved_attachments = _prepare_html_and_attachments(
            body, html_body, attachments, username, session_id
        )

        sent = client.send_message(
            to=reply_to, subject=subject, body=body,
            thread_id=thread_id, in_reply_to=orig_message_id_header,
            references=references, attachments=resolved_attachments,
            html_body=final_html_body, from_name=from_name,
        )

        info = _format_send_info(resolved_attachments, final_html_body)
        return make_tool_result(
            f"Reply sent successfully from {creds.email_address}.{info}\n"
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
    attachments: list[dict] | None = None,
    html_body: str | None = None,
    from_name: str = "",
    session_id: str | None = None,
) -> dict[str, Any]:
    """Create a Gmail draft with optional attachments and HTML body."""
    if not from_name:
        from_name = _get_default_from_name()
        if not from_name:
            from_name = _get_default_from_name()
    result = _check_full_access(username, provider)
    if isinstance(result, dict):
        return result
    creds, client = result

    try:
        final_html_body, resolved_attachments = _prepare_html_and_attachments(
            body, html_body, attachments, username, session_id
        )

        draft = client.create_draft(
            to=to, subject=subject, body=body, cc=cc, bcc=bcc,
            attachments=resolved_attachments, html_body=final_html_body,
            from_name=from_name,
        )

        info = _format_send_info(resolved_attachments, final_html_body)
        return make_tool_result(
            f"Draft created successfully in {creds.email_address}.{info}\n"
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
