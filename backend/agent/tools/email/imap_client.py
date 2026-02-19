"""Universal IMAP client for any email provider.

Provides a generic IMAP client and MCP tool implementation functions for listing,
reading, searching emails, downloading attachments, and listing folders via IMAP.
Works with Yahoo, Outlook, iCloud, Zoho, and any custom IMAP server.
"""
import email
import email.header
import imaplib
import logging
import re
from email import policy
from email.message import EmailMessage
from typing import Any

from agent.tools.email.credential_store import (
    EmailCredentials,
    get_credential_store,
    get_provider_display_name,
)
from agent.tools.email.attachment_store import get_attachment_store
from agent.tools.email.formatting import format_email_preview, format_email_detail

logger = logging.getLogger(__name__)

# MIME types that are always considered attachments (maintype match)
_ATTACHMENT_MAIN_TYPES = frozenset({"application", "image", "audio", "video", "model"})

# Specific subtypes that are attachments even though their maintype is text/message
_ATTACHMENT_SPECIFIC_TYPES = frozenset({
    "text/csv",
    "text/calendar",
    "message/rfc822",
})


class UniversalIMAPClient:
    """IMAP client that works with any provider using app-password authentication.

    Uses ``EmailCredentials`` to determine the IMAP server, port, email address,
    and app password.  Supports context-manager usage for automatic cleanup.
    """

    def __init__(self, credentials: EmailCredentials):
        """Initialize IMAP client.

        Args:
            credentials: EmailCredentials with imap_server, imap_port,
                         email_address, and app_password populated.
        """
        self._credentials = credentials
        self._client: imaplib.IMAP4_SSL | None = None
        self._authenticated = False

    # ------------------------------------------------------------------
    # Connection helpers
    # ------------------------------------------------------------------

    def _authenticate(self) -> None:
        """Connect and authenticate with the IMAP server."""
        if self._authenticated and self._client:
            return

        imap_server = self._credentials.imap_server
        imap_port = self._credentials.imap_port or 993

        if not imap_server:
            raise ValueError(
                "IMAP server not configured. Please provide imap_server in credentials."
            )

        try:
            self._client = imaplib.IMAP4_SSL(imap_server, imap_port)

            email_address = self._credentials.email_address or ""
            app_password = self._credentials.app_password

            if not app_password:
                raise ValueError(
                    "App password not configured. Please set an app-specific password."
                )

            self._client.login(email_address, app_password)
            self._authenticated = True

            provider = self._credentials.provider or "unknown"
            logger.info("Authenticated with IMAP server %s (provider: %s)", imap_server, provider)

        except Exception as e:
            logger.error("Failed to authenticate with IMAP server %s: %s", imap_server, e)
            self._client = None
            raise

    def close(self) -> None:
        """Explicitly close the IMAP connection."""
        if self._client:
            try:
                self._client.logout()
            except Exception:
                pass
            finally:
                self._client = None
                self._authenticated = False

    def __enter__(self) -> "UniversalIMAPClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self.close()
        return False

    # ------------------------------------------------------------------
    # Header / body decoding utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _decode_header(header: str) -> str:
        """Decode an email header, handling encoded words and charset fallbacks.

        Args:
            header: Raw header value.

        Returns:
            Decoded string.
        """
        if not header:
            return ""
        try:
            decoded_parts = email.header.decode_header(header)
            result_parts: list[str] = []
            for content, charset in decoded_parts:
                if isinstance(content, bytes):
                    # Try charsets in order of preference
                    for enc in (charset, "utf-8", "latin-1", "ascii"):
                        if enc is None:
                            continue
                        try:
                            result_parts.append(content.decode(enc))
                            break
                        except (UnicodeDecodeError, LookupError):
                            continue
                    else:
                        # Final fallback
                        result_parts.append(content.decode("ascii", errors="replace"))
                else:
                    result_parts.append(content)
            return "".join(result_parts)
        except Exception:
            return header

    @staticmethod
    def is_attachment_part(part: EmailMessage) -> bool:
        """Determine whether an email MIME part is an attachment.

        Checks Content-Disposition and MIME type to decide.

        Args:
            part: A single MIME part from ``msg.walk()``.

        Returns:
            True if the part should be treated as an attachment.
        """
        if part.get_content_maintype() == "multipart":
            return False

        content_disposition = str(part.get("Content-Disposition", "")).lower()
        content_type = part.get_content_type().lower()
        maintype = part.get_content_maintype()
        filename = part.get_filename()

        # Explicit attachment disposition
        if "attachment" in content_disposition:
            return True

        # Inline with a filename (embedded image, etc.)
        if "inline" in content_disposition and filename:
            return True

        # Known attachment MIME main-types
        if maintype in _ATTACHMENT_MAIN_TYPES:
            return True

        # Specific sub-types that are attachments
        if content_type in _ATTACHMENT_SPECIFIC_TYPES:
            return True

        return False

    @staticmethod
    def extract_email_body(msg: EmailMessage) -> str:
        """Extract the readable body text from an email message.

        Handles multipart/alternative (prefers text/plain), nested multipart,
        and falls back to HTML with basic tag stripping.

        Args:
            msg: EmailMessage object.

        Returns:
            Plain-text body string.
        """
        if not msg.is_multipart():
            payload = msg.get_payload(decode=True)
            if payload:
                content_type = msg.get_content_type()
                text = payload.decode("utf-8", errors="replace")
                if content_type == "text/html":
                    return UniversalIMAPClient._strip_html(text)
                return text
            return ""

        plain_body: str | None = None
        html_body: str | None = None

        for part in msg.walk():
            if part.get_content_maintype() == "multipart":
                continue
            if UniversalIMAPClient.is_attachment_part(part):
                continue

            content_type = part.get_content_type()
            payload = part.get_payload(decode=True)
            if not payload:
                continue

            text = payload.decode("utf-8", errors="replace")

            if content_type == "text/plain" and plain_body is None:
                plain_body = text
            elif content_type == "text/html" and html_body is None:
                html_body = text

        if plain_body is not None:
            return plain_body

        if html_body is not None:
            return UniversalIMAPClient._strip_html(html_body)

        return ""

    @staticmethod
    def _strip_html(html: str) -> str:
        """Perform basic HTML tag stripping.

        Args:
            html: Raw HTML string.

        Returns:
            Text with tags removed.
        """
        # Remove style and script blocks
        text = re.sub(r"<(style|script)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
        # Replace <br> and </p> with newlines
        text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"</p>", "\n", text, flags=re.IGNORECASE)
        # Strip remaining tags
        text = re.sub(r"<[^>]+>", "", text)
        # Collapse whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    # ------------------------------------------------------------------
    # IMAP operations
    # ------------------------------------------------------------------

    def list_messages(
        self,
        folder: str = "INBOX",
        criteria: str = "ALL",
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """List messages in a folder.

        Args:
            folder: IMAP folder name.
            criteria: IMAP SEARCH criteria string.
            limit: Maximum number of messages to return.

        Returns:
            List of message summary dicts (id, subject, from, date, snippet).
        """
        self._authenticate()

        try:
            self._client.select(folder)
            status, messages = self._client.search(None, criteria)
            if status != "OK":
                return []

            msg_ids = messages[0].split()
            msg_ids = msg_ids[-limit:] if len(msg_ids) > limit else msg_ids

            result: list[dict[str, Any]] = []
            for msg_id in reversed(msg_ids):
                status, msg_data = self._client.fetch(msg_id, "(RFC822.HEADER)")
                if status == "OK":
                    raw_header = msg_data[0][1]
                    msg = email.message_from_bytes(raw_header, policy=policy.default)
                    result.append({
                        "id": msg_id.decode(),
                        "subject": self._decode_header(msg.get("Subject", "(No subject)")),
                        "from": self._decode_header(msg.get("From", "")),
                        "date": msg.get("Date", ""),
                        "snippet": "[Full content available when reading message]",
                    })

            logger.info("Listed %d messages from folder %s", len(result), folder)
            return result

        except Exception as e:
            logger.error("Failed to list messages: %s", e)
            raise
        finally:
            try:
                self._client.close()
            except Exception:
                pass

    def get_message(self, msg_id: str, folder: str = "INBOX") -> EmailMessage:
        """Fetch a full message by IMAP ID.

        Args:
            msg_id: IMAP message ID string.
            folder: IMAP folder name.

        Returns:
            Parsed EmailMessage object.
        """
        self._authenticate()

        try:
            self._client.select(folder)
            status, msg_data = self._client.fetch(msg_id, "(RFC822)")
            if status != "OK":
                raise ValueError(f"Failed to fetch message {msg_id}")

            raw_email = msg_data[0][1]
            return email.message_from_bytes(raw_email, policy=policy.default)

        except Exception as e:
            logger.error("Failed to get message %s: %s", msg_id, e)
            raise
        finally:
            try:
                self._client.close()
            except Exception:
                pass

    def get_attachments(self, msg: EmailMessage) -> list[dict[str, Any]]:
        """Get attachment metadata from a message.

        Args:
            msg: EmailMessage object.

        Returns:
            List of dicts with filename, content_type, size.
        """
        attachments: list[dict[str, Any]] = []
        for part in msg.walk():
            if not self.is_attachment_part(part):
                continue
            filename = part.get_filename()
            if filename:
                attachments.append({
                    "filename": self._decode_header(filename),
                    "content_type": part.get_content_type(),
                    "size": len(part.get_payload(decode=True) or b""),
                })
        return attachments

    def download_attachment(self, msg: EmailMessage, filename: str) -> bytes:
        """Download attachment content by filename.

        Args:
            msg: EmailMessage object.
            filename: Attachment filename to download.

        Returns:
            Attachment content bytes.

        Raises:
            ValueError: If attachment not found.
        """
        for part in msg.walk():
            if not self.is_attachment_part(part):
                continue
            part_filename = part.get_filename()
            if part_filename and self._decode_header(part_filename) == filename:
                content = part.get_payload(decode=True)
                if content:
                    return content

        raise ValueError(f"Attachment not found: {filename}")

    def parse_message(self, msg: EmailMessage) -> dict[str, Any]:
        """Parse an email message into a readable dict.

        Args:
            msg: EmailMessage object.

        Returns:
            Dict with subject, from, to, date, body, has_attachments, attachments.
        """
        body = self.extract_email_body(msg)
        attachments = self.get_attachments(msg)

        return {
            "subject": self._decode_header(msg.get("Subject", "(No subject)")),
            "from": self._decode_header(msg.get("From", "")),
            "to": self._decode_header(msg.get("To", "")),
            "date": msg.get("Date", ""),
            "body": body,
            "has_attachments": len(attachments) > 0,
            "attachments": attachments,
        }

    def list_folders(self) -> list[str]:
        """List available IMAP folders.

        Returns:
            List of folder name strings.
        """
        self._authenticate()

        try:
            status, folder_data = self._client.list()
            if status != "OK":
                return []

            folders: list[str] = []
            for item in folder_data:
                if isinstance(item, bytes):
                    # Parse IMAP LIST response: (\\flags) "delimiter" "name"
                    match = re.search(rb'"([^"]*)"$|(\S+)$', item)
                    if match:
                        folder_name = (match.group(1) or match.group(2)).decode(
                            "utf-8", errors="replace"
                        )
                        folders.append(folder_name)
            return folders

        except Exception as e:
            logger.error("Failed to list folders: %s", e)
            raise

    def search_messages(
        self,
        query: str,
        folder: str = "INBOX",
        max_results: int = 10,
    ) -> list[dict[str, Any]]:
        """Search messages using IMAP SEARCH.

        Builds IMAP SEARCH criteria from a human-readable query string.
        Supports ``subject:``, ``from:``, ``since:``, ``before:`` prefixes,
        or falls back to SUBJECT search.

        Args:
            query: Search query string.
            folder: IMAP folder to search in.
            max_results: Maximum results to return.

        Returns:
            List of message summary dicts.
        """
        self._authenticate()

        try:
            self._client.select(folder)

            # Build IMAP search criteria from query
            criteria = self._build_search_criteria(query)

            # Use UTF-8 charset for non-ASCII queries (e.g., Vietnamese characters)
            has_non_ascii = any(
                ord(c) > 127 for token in criteria for c in token
            )
            if has_non_ascii:
                # IMAP4rev1 UTF-8 search: charset must be specified
                search_criteria = " ".join(criteria)
                status, messages = self._client.search(
                    "UTF-8", search_criteria.encode("utf-8")
                )
            else:
                status, messages = self._client.search(None, *criteria)
            if status != "OK":
                return []

            msg_ids = messages[0].split()
            msg_ids = msg_ids[-max_results:] if len(msg_ids) > max_results else msg_ids

            result: list[dict[str, Any]] = []
            for msg_id in reversed(msg_ids):
                status, msg_data = self._client.fetch(msg_id, "(RFC822.HEADER)")
                if status == "OK":
                    raw_header = msg_data[0][1]
                    msg = email.message_from_bytes(raw_header, policy=policy.default)
                    result.append({
                        "id": msg_id.decode(),
                        "subject": self._decode_header(msg.get("Subject", "(No subject)")),
                        "from": self._decode_header(msg.get("From", "")),
                        "date": msg.get("Date", ""),
                        "snippet": "[Full content available when reading message]",
                    })

            logger.info("Search found %d messages for query '%s'", len(result), query)
            return result

        except Exception as e:
            logger.error("Failed to search messages: %s", e)
            raise
        finally:
            try:
                self._client.close()
            except Exception:
                pass

    @staticmethod
    def _normalize_imap_date(value: str) -> str:
        """Convert various date formats to IMAP date format (DD-Mon-YYYY).

        Accepts: YYYY/MM/DD, YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY, or
        already-correct DD-Mon-YYYY. Returns the IMAP-compatible string.
        """
        import calendar

        value = value.strip()
        months = {i: calendar.month_abbr[i] for i in range(1, 13)}

        # Already in IMAP format (e.g. 01-Feb-2026)
        imap_pat = re.match(r"^(\d{1,2})-([A-Za-z]{3})-(\d{4})$", value)
        if imap_pat:
            return value

        # YYYY/MM/DD or YYYY-MM-DD
        m = re.match(r"^(\d{4})[/-](\d{1,2})[/-](\d{1,2})$", value)
        if m:
            year, month, day = m.group(1), int(m.group(2)), m.group(3)
            return f"{int(day):02d}-{months[month]}-{year}"

        # DD/MM/YYYY or DD-MM-YYYY
        m = re.match(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$", value)
        if m:
            day, month, year = m.group(1), int(m.group(2)), m.group(3)
            return f"{int(day):02d}-{months[month]}-{year}"

        # Return as-is if unrecognized
        return value

    @staticmethod
    def _build_search_criteria(query: str) -> list[str]:
        """Convert a query string into IMAP SEARCH criteria tokens.

        Supports prefixes: ``subject:``, ``from:``, ``to:``, ``since:``, ``before:``.
        Multiple criteria are combined with AND (default IMAP behavior).
        Unprefixed words become OR'd SUBJECT searches.

        Args:
            query: Human-readable search query.

        Returns:
            List of IMAP SEARCH criteria strings.
        """
        criteria: list[str] = []
        query = query.strip()

        if not query:
            return ["ALL"]

        # Check for structured prefixes
        date_keys = {"SINCE", "BEFORE"}
        prefix_map = {
            "subject:": "SUBJECT",
            "from:": "FROM",
            "to:": "TO",
            "since:": "SINCE",
            "before:": "BEFORE",
        }

        remaining = query

        for prefix, imap_key in prefix_map.items():
            pattern = re.compile(
                re.escape(prefix) + r'\s*"([^"]+)"|'
                + re.escape(prefix) + r"\s*(\S+)",
                re.IGNORECASE,
            )
            for match in pattern.finditer(remaining):
                value = match.group(1) or match.group(2)
                if imap_key in date_keys:
                    value = UniversalIMAPClient._normalize_imap_date(value)
                criteria.extend([imap_key, value])
            # Remove matched tokens from remaining string
            remaining = pattern.sub("", remaining)

        # Handle leftover unprefixed words as SUBJECT or OR'd SUBJECT searches
        leftover = remaining.strip()
        if leftover:
            words = leftover.split()
            if len(words) == 1:
                criteria.extend(["SUBJECT", words[0]])
            else:
                # OR SUBJECT word1 SUBJECT word2 ... (IMAP OR is binary prefix)
                # Build: OR (SUBJECT w1) (OR (SUBJECT w2) (SUBJECT w3))
                # For simplicity, search each word as SUBJECT (AND logic)
                for word in words:
                    criteria.extend(["SUBJECT", word])

        if not criteria:
            return ["ALL"]

        return criteria


# ======================================================================
# Tool implementation functions
# ======================================================================

def _make_result(text: str) -> dict[str, Any]:
    """Create a standard MCP tool result."""
    return {"content": [{"type": "text", "text": text}]}


def _with_imap_credentials(
    username: str,
    provider: str,
) -> tuple[EmailCredentials, str] | dict[str, Any]:
    """Load IMAP credentials and display name.

    Returns:
        Tuple of (credentials, display_name) on success, or MCP error result dict on failure.
    """
    cred_store = get_credential_store(username)
    credentials = cred_store.load_credentials(provider)
    display_name = get_provider_display_name(provider)

    if credentials is None:
        return _make_result(
            f"{display_name} account not connected. "
            f"Please connect your {display_name} account first."
        )

    return credentials, display_name


def list_imap_impl(
    username: str,
    provider: str,
    max_results: int = 10,
    folder: str = "INBOX",
) -> dict[str, Any]:
    """List emails from any IMAP account."""
    result = _with_imap_credentials(username, provider)
    if isinstance(result, dict):
        return result
    credentials, display_name = result

    try:
        with UniversalIMAPClient(credentials) as client:
            messages = client.list_messages(folder=folder, limit=max_results)

            if not messages:
                return _make_result(f"No emails found in {folder}")

            previews = [format_email_preview(msg) for msg in messages]
            return _make_result(
                f"Found {len(previews)} emails:\n\n" + "\n".join(previews)
            )

    except Exception as e:
        logger.error("Failed to list %s mail: %s", display_name, e)
        return _make_result(f"Failed to list {display_name} mail: {e}")


def read_imap_impl(
    username: str,
    provider: str,
    message_id: str,
    folder: str = "INBOX",
) -> dict[str, Any]:
    """Read a full email from any IMAP account."""
    result = _with_imap_credentials(username, provider)
    if isinstance(result, dict):
        return result
    credentials, display_name = result

    try:
        with UniversalIMAPClient(credentials) as client:
            msg = client.get_message(message_id, folder=folder)
            parsed = client.parse_message(msg)
            return _make_result(format_email_detail(parsed))

    except Exception as e:
        logger.error("Failed to read %s message %s: %s", display_name, message_id, e)
        return _make_result(f"Failed to read email: {e}")


def download_imap_attachments_impl(
    username: str,
    provider: str,
    message_id: str,
    filenames: list[str] | None = None,
    folder: str = "INBOX",
) -> dict[str, Any]:
    """Download attachments from any IMAP email."""
    result = _with_imap_credentials(username, provider)
    if isinstance(result, dict):
        return result
    credentials, display_name = result
    attachment_store = get_attachment_store(username)

    try:
        with UniversalIMAPClient(credentials) as client:
            msg = client.get_message(message_id, folder=folder)

            attachments = client.get_attachments(msg)
            if filenames is None:
                filenames = [a["filename"] for a in attachments]

            if not filenames:
                return _make_result("No attachments found in this email.")

            downloaded: list[str] = []
            for filename in filenames:
                try:
                    content = client.download_attachment(msg, filename)
                    filepath = attachment_store.save_attachment(
                        provider, message_id, filename, content
                    )
                    downloaded.append(str(filepath))
                except Exception as e:
                    logger.warning("Failed to download attachment %s: %s", filename, e)
                    downloaded.append(f"Failed: {filename}")

            return _make_result(
                f"Downloaded {len(downloaded)} attachment(s):\n\n"
                + "\n".join(downloaded)
            )

    except Exception as e:
        logger.error("Failed to download attachments: %s", e)
        return _make_result(f"Failed to download attachments: {e}")


def search_imap_impl(
    username: str,
    provider: str,
    query: str,
    max_results: int = 10,
    folder: str = "INBOX",
) -> dict[str, Any]:
    """Search emails in any IMAP account."""
    result = _with_imap_credentials(username, provider)
    if isinstance(result, dict):
        return result
    credentials, display_name = result

    try:
        with UniversalIMAPClient(credentials) as client:
            messages = client.search_messages(
                query=query, folder=folder, max_results=max_results
            )

            if not messages:
                return _make_result(
                    f"No emails found matching '{query}'. "
                    "Try broadening your search: use fewer prefixes, remove date filters, "
                    "use shorter keywords, or try from: alone. "
                    "You can also use list_imap_emails to browse recent emails."
                )

            previews = [format_email_preview(msg) for msg in messages]
            return _make_result(
                f"Found {len(previews)} emails matching '{query}':\n\n"
                + "\n".join(previews)
            )

    except Exception as e:
        logger.error("Failed to search %s mail: %s", display_name, e)
        error_msg = str(e)
        hint = ""
        if "SEARCH" in error_msg.upper() and ("BAD" in error_msg or "parse" in error_msg.lower()):
            hint = (
                " Hint: simplify your query. Use 1-2 prefixes max "
                "(e.g., 'from:sender since:2026-02-01'). "
                "Dates must be in format like 2026-02-01. "
                "Avoid combining too many search terms."
            )
        return _make_result(f"Failed to search {display_name} mail: {e}.{hint}")


def list_imap_folders_impl(
    username: str,
    provider: str,
) -> dict[str, Any]:
    """List IMAP folders for an email account."""
    result = _with_imap_credentials(username, provider)
    if isinstance(result, dict):
        return result
    credentials, display_name = result

    try:
        with UniversalIMAPClient(credentials) as client:
            folders = client.list_folders()

            if not folders:
                return _make_result("No folders found.")

            folder_list = "\n".join(f"- {f}" for f in folders)
            return _make_result(
                f"Found {len(folders)} folder(s):\n\n{folder_list}"
            )

    except Exception as e:
        logger.error("Failed to list %s folders: %s", display_name, e)
        return _make_result(f"Failed to list folders: {e}")


def list_email_accounts_impl(username: str) -> dict[str, Any]:
    """List all connected email accounts (Gmail + IMAP providers).

    Args:
        username: Username for credential lookup.

    Returns:
        MCP tool result dict.
    """
    cred_store = get_credential_store(username)
    accounts = cred_store.get_all_accounts()

    if not accounts:
        return _make_result(
            "No email accounts connected. "
            "Use the profile page to connect Gmail (OAuth) or IMAP accounts."
        )

    lines: list[str] = []
    for acct in accounts:
        line = (
            f"- **{acct['provider_name']}** ({acct['email']}) "
            f"[{acct['auth_type']}]"
        )
        access_level = acct.get("access_level", "")
        if access_level == "full_access":
            line += " — Full Access"
        elif access_level == "read_only":
            line += " — Read Only"
        lines.append(line)

    return _make_result(
        f"Connected email accounts ({len(accounts)}):\n\n" + "\n".join(lines)
    )
