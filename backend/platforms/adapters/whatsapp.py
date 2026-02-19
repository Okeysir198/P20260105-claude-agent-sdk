"""WhatsApp Cloud API adapter.

Handles parsing Meta webhook payloads, HMAC-SHA256 signature verification,
and sending responses via the WhatsApp Cloud API.
"""

import hashlib
import hmac
import logging
import os
import re
import time
from typing import Any

import httpx

from platforms.base import NormalizedMessage, NormalizedResponse, Platform, PlatformAdapter

logger = logging.getLogger(__name__)

# WhatsApp message length limit (approximate safe limit)
WHATSAPP_MAX_MESSAGE_LENGTH = 4096

GRAPH_API_VERSION = "v20.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


class WhatsAppAdapter(PlatformAdapter):
    """Adapter for the WhatsApp Cloud API (Meta)."""

    platform = Platform.WHATSAPP

    def __init__(self) -> None:
        self._phone_number_id = os.environ["WHATSAPP_PHONE_NUMBER_ID"]
        self._access_token = os.environ["WHATSAPP_ACCESS_TOKEN"]
        self._verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
        self._app_secret = os.getenv("WHATSAPP_APP_SECRET", "")
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={"Authorization": f"Bearer {self._access_token}"},
        )
        # Track last message timestamp per chat for 24h window
        self._last_message_ts: dict[str, float] = {}
        # Track last inbound message_id per chat for read receipts
        self._last_message_id: dict[str, str] = {}

    def parse_inbound(self, raw_payload: dict) -> NormalizedMessage | None:
        """Parse a Meta webhook payload into a NormalizedMessage.

        Meta sends a nested structure:
        {
            "object": "whatsapp_business_account",
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{ ... }],
                        "contacts": [{ ... }]
                    }
                }]
            }]
        }
        """
        if raw_payload.get("object") != "whatsapp_business_account":
            return None

        entries = raw_payload.get("entry", [])
        if not entries:
            return None

        for entry in entries:
            for change in entry.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages", [])
                contacts = value.get("contacts", [])

                if not messages:
                    continue

                message = messages[0]
                msg_type = message.get("type")
                from_number = message.get("from", "")
                wa_message_id = message.get("id", "")

                # Extract contact name
                contact_name = ""
                if contacts:
                    profile = contacts[0].get("profile", {})
                    contact_name = profile.get("name", "")

                # Extract text content
                text = ""
                if msg_type == "text":
                    text = message.get("text", {}).get("body", "")
                elif msg_type == "interactive":
                    interactive = message.get("interactive", {})
                    if interactive.get("type") == "button_reply":
                        text = interactive.get("button_reply", {}).get("title", "")
                    elif interactive.get("type") == "list_reply":
                        text = interactive.get("list_reply", {}).get("title", "")

                # Extract media (image, video, audio, document, sticker)
                media: list[dict] = []
                media_types = ("image", "video", "audio", "document", "sticker")
                if msg_type in media_types:
                    media_data = message.get(msg_type, {})
                    media_item: dict = {
                        "type": msg_type,
                        "media_id": media_data.get("id", ""),
                        "mime_type": media_data.get("mime_type", ""),
                    }
                    if msg_type == "document":
                        media_item["file_name"] = media_data.get("filename", "")
                    if not text:
                        # Use caption as text for media messages
                        text = media_data.get("caption", "") or message.get("caption", "")
                    media.append(media_item)

                if not text and not media:
                    return None

                # Track message timestamp and ID for 24h window / read receipts
                self._last_message_ts[from_number] = time.time()
                if wa_message_id:
                    self._last_message_id[from_number] = wa_message_id

                return NormalizedMessage(
                    platform=Platform.WHATSAPP,
                    platform_user_id=from_number,
                    platform_chat_id=from_number,
                    text=text,
                    media=media,
                    metadata={
                        "message_id": wa_message_id,
                        "contact_name": contact_name,
                        "timestamp": message.get("timestamp", ""),
                    },
                )

        return None

    def verify_signature(self, raw_body: bytes, headers: dict[str, str]) -> bool:
        """Verify Meta webhook signature using HMAC-SHA256."""
        if not self._app_secret:
            return True  # Development mode

        signature_header = headers.get("x-hub-signature-256", "")
        if not signature_header.startswith("sha256="):
            return False

        expected_sig = signature_header[7:]  # Strip "sha256=" prefix
        computed_sig = hmac.new(
            self._app_secret.encode(),
            raw_body,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(computed_sig, expected_sig)

    def verify_webhook_challenge(self, params: dict[str, str]) -> str | None:
        """Handle Meta webhook verification handshake.

        Args:
            params: Query parameters from the GET request.

        Returns:
            The challenge string if verification succeeds, None otherwise.
        """
        mode = params.get("hub.mode")
        token = params.get("hub.verify_token")
        challenge = params.get("hub.challenge")

        if mode == "subscribe" and token == self._verify_token:
            logger.info("WhatsApp webhook verified successfully")
            return challenge
        return None

    def is_within_24h_window(self, chat_id: str) -> bool:
        """Check if we're within the 24h messaging window for a chat."""
        last_ts = self._last_message_ts.get(chat_id)
        if not last_ts:
            return False
        return (time.time() - last_ts) < 86400  # 24 hours

    @staticmethod
    def _format_text(text: str) -> str:
        """Convert standard markdown to WhatsApp-compatible formatting.

        WhatsApp supports: *bold*, _italic_, ~strikethrough~, `code`, ```code blocks```.
        This converts Claude's markdown (**, ##, [](), etc.) into those formats.
        """
        # Protect code blocks and inline code from regex mangling
        placeholders: list[str] = []

        def _protect(m: re.Match) -> str:
            placeholders.append(m.group(0))
            return f"\x00PH{len(placeholders) - 1}\x00"

        # Protect fenced code blocks first, then inline code
        text = re.sub(r"```[\s\S]*?```", _protect, text)
        text = re.sub(r"`[^`]+`", _protect, text)

        # Headers → bold (strip # prefix)
        text = re.sub(r"^#{1,6}\s+(.+)$", r"*\1*", text, flags=re.MULTILINE)

        # Bold: **text** or __text__ → *text* (WhatsApp bold)
        text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)
        text = re.sub(r"__(.+?)__", r"*\1*", text)

        # Italic: *text* is already WhatsApp italic — but single _ needs converting
        # _text_ → _text_ (already valid WhatsApp italic, no change needed)

        # Strikethrough: ~~text~~ → ~text~
        text = re.sub(r"~~(.+?)~~", r"~\1~", text)

        # Links: [text](url) → text (url)
        text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)

        # Images: ![alt](url) → alt (url)
        text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r"\1 (\2)", text)

        # Restore protected blocks
        for i, original in enumerate(placeholders):
            text = text.replace(f"\x00PH{i}\x00", original)

        return text

    async def send_response(self, chat_id: str, response: NormalizedResponse) -> None:
        """Send a text message via WhatsApp Cloud API."""
        # Mark the last inbound message as read
        last_msg_id = self._last_message_id.get(chat_id)
        if last_msg_id:
            await self._mark_as_read(last_msg_id)

        text = self._format_text(response.text)
        if len(text) > WHATSAPP_MAX_MESSAGE_LENGTH:
            text = text[:WHATSAPP_MAX_MESSAGE_LENGTH - 3] + "..."

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": chat_id,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }

        resp = await self._client.post(
            f"{GRAPH_API_BASE}/{self._phone_number_id}/messages",
            json=payload,
        )

        if resp.status_code != 200:
            logger.error(f"WhatsApp sendMessage failed: {resp.status_code} {resp.text}")

    async def send_file(
        self,
        chat_id: str,
        file_path: str,
        filename: str,
        mime_type: str = "application/octet-stream",
    ) -> bool:
        """Send a file to WhatsApp via media upload + message send."""
        import os as _os

        try:
            file_size = _os.path.getsize(file_path)
        except OSError:
            logger.warning(f"Cannot stat file for WhatsApp upload: {file_path}")
            return False

        # WhatsApp max 100MB for documents
        if file_size > 100 * 1024 * 1024:
            logger.info(f"File too large for WhatsApp ({file_size} bytes): {filename}")
            return False

        # WhatsApp only accepts specific MIME types for upload.
        # For unsupported types, use application/octet-stream so it's
        # accepted as a generic document.
        _WA_SUPPORTED_MIMES = {
            "audio/aac", "audio/mp4", "audio/mpeg", "audio/amr", "audio/ogg", "audio/opus",
            "image/jpeg", "image/png", "image/webp",
            "video/mp4", "video/3gpp",
            "application/pdf", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/msword", "application/vnd.ms-excel", "application/vnd.ms-powerpoint",
            "text/plain", "application/octet-stream",
        }
        upload_mime = mime_type if mime_type in _WA_SUPPORTED_MIMES else "application/octet-stream"

        try:
            # Step 1: Upload media
            with open(file_path, "rb") as f:
                upload_resp = await self._client.post(
                    f"{GRAPH_API_BASE}/{self._phone_number_id}/media",
                    data={"messaging_product": "whatsapp"},
                    files={"file": (filename, f, upload_mime)},
                    timeout=120.0,
                )

            if upload_resp.status_code != 200:
                logger.error(f"WhatsApp media upload failed: {upload_resp.status_code} {upload_resp.text}")
                return False

            media_id = upload_resp.json().get("id")
            if not media_id:
                logger.error("WhatsApp media upload returned no media ID")
                return False

            # Step 2: Determine message type from MIME
            # Use upload_mime (not original) since that's what WhatsApp accepted
            if upload_mime.startswith("image/"):
                msg_type = "image"
            elif upload_mime.startswith("video/"):
                msg_type = "video"
            elif upload_mime.startswith("audio/"):
                msg_type = "audio"
            else:
                msg_type = "document"

            # Step 3: Send message referencing the uploaded media
            media_payload: dict[str, Any] = {"id": media_id}
            if msg_type == "document":
                media_payload["filename"] = filename

            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": chat_id,
                "type": msg_type,
                msg_type: media_payload,
            }

            send_resp = await self._client.post(
                f"{GRAPH_API_BASE}/{self._phone_number_id}/messages",
                json=payload,
            )

            if send_resp.status_code == 200:
                logger.info(f"Sent file to WhatsApp: {filename}")
                return True
            else:
                logger.error(f"WhatsApp send media message failed: {send_resp.status_code} {send_resp.text}")
                return False

        except Exception as e:
            logger.error(f"WhatsApp file send error: {e}")
            return False

    def get_media_download_kwargs(self) -> dict[str, Any]:
        """Return kwargs for ``process_media_items()``."""
        return {
            "access_token": self._access_token,
            "whatsapp_client": self._client,
            "whatsapp_api_base": GRAPH_API_BASE,
        }

    def get_download_client(self) -> tuple[httpx.AsyncClient, str, str]:
        """Return (client, api_base, access_token) for media downloads."""
        return self._client, GRAPH_API_BASE, self._access_token

    async def _mark_as_read(self, message_id: str) -> None:
        """Mark a WhatsApp message as read by its message ID."""
        try:
            await self._client.post(
                f"{GRAPH_API_BASE}/{self._phone_number_id}/messages",
                json={
                    "messaging_product": "whatsapp",
                    "status": "read",
                    "message_id": message_id,
                },
            )
        except Exception as e:
            logger.debug(f"Failed to mark message as read: {e}")
