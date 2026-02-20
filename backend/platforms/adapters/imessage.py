"""BlueBubbles iMessage adapter.

Bridges iMessage via a BlueBubbles server running on macOS.
The BlueBubbles server exposes a REST API and sends webhooks
for incoming messages.

Requires:
    BLUEBUBBLES_SERVER_URL: Base URL of the BlueBubbles server (e.g. http://mac-ip:1234)
    BLUEBUBBLES_PASSWORD: Server password for API authentication
"""

import hashlib
import hmac
import logging
import os
from typing import Any

import httpx

from platforms.base import NormalizedMessage, NormalizedResponse, Platform, PlatformAdapter, split_message

logger = logging.getLogger(__name__)

# iMessage has no hard character limit, but we cap for readability
IMESSAGE_MAX_MESSAGE_LENGTH = 8000


class IMessageAdapter(PlatformAdapter):
    """Adapter for iMessage via BlueBubbles REST API."""

    platform = Platform.IMESSAGE

    def __init__(self) -> None:
        self._server_url = os.environ["BLUEBUBBLES_SERVER_URL"].rstrip("/")
        self._password = os.environ["BLUEBUBBLES_PASSWORD"]
        self._webhook_secret = os.getenv("BLUEBUBBLES_WEBHOOK_SECRET", "")
        self._client = httpx.AsyncClient(timeout=30.0)
        if not self._webhook_secret:
            logger.warning(
                "BLUEBUBBLES_WEBHOOK_SECRET not set — webhook signature verification disabled. "
                "Set this in production for security."
            )

    def parse_inbound(self, raw_payload: dict) -> NormalizedMessage | None:
        """Parse a BlueBubbles webhook payload into a NormalizedMessage.

        BlueBubbles webhook payload structure:
        {
            "type": "new-message",
            "data": {
                "guid": "message-guid",
                "text": "message text",
                "isFromMe": false,
                "handle": {
                    "address": "+1234567890",
                    "id": 123
                },
                "chats": [{
                    "guid": "iMessage;-;+1234567890",
                    "chatIdentifier": "+1234567890",
                    "displayName": "..."
                }],
                "attachments": [{
                    "guid": "attachment-guid",
                    "mimeType": "image/jpeg",
                    "transferName": "photo.jpg",
                    "totalBytes": 12345
                }],
                "dateCreated": 1234567890000,
                "associatedMessageGuid": null,
                "associatedMessageType": null
            }
        }
        """
        event_type = raw_payload.get("type", "")
        if event_type != "new-message":
            return None

        data = raw_payload.get("data", {})
        if not data:
            return None

        # Skip outgoing messages
        if data.get("isFromMe", False):
            return None

        # Skip tapback / reaction messages (associatedMessageType != null)
        if data.get("associatedMessageType") is not None:
            return None

        # Extract sender
        handle = data.get("handle") or {}
        sender_address = handle.get("address", "")
        if not sender_address:
            return None

        # Extract chat ID from first chat
        chats = data.get("chats", [])
        if not chats:
            return None
        chat_guid = chats[0].get("guid", "")
        if not chat_guid:
            return None

        # Extract text
        text = data.get("text") or ""

        # Extract media attachments
        media: list[dict] = []
        for attachment in data.get("attachments", []):
            attachment_guid = attachment.get("guid", "")
            mime_type = attachment.get("mimeType", "application/octet-stream")
            transfer_name = attachment.get("transferName", "")
            total_bytes = attachment.get("totalBytes", 0)

            if attachment_guid:
                media.append({
                    "type": _media_type_from_mime(mime_type),
                    "attachment_guid": attachment_guid,
                    "file_name": transfer_name,
                    "mime_type": mime_type,
                    "total_bytes": total_bytes,
                })

        if not text and not media:
            return None

        # Build metadata
        message_guid = data.get("guid", "")
        chat_display_name = chats[0].get("displayName", "")
        is_group = len(chats[0].get("participants", [])) > 2 if chats else False

        return NormalizedMessage(
            platform=Platform.IMESSAGE,
            platform_user_id=sender_address,
            platform_chat_id=chat_guid,
            text=text,
            media=media,
            metadata={
                "message_id": message_guid,
                "chat_display_name": chat_display_name,
                "is_group": is_group,
                "handle_address": sender_address,
            },
        )

    def verify_signature(self, raw_body: bytes, headers: dict[str, str]) -> bool:
        """Verify BlueBubbles webhook signature.

        If BLUEBUBBLES_WEBHOOK_SECRET is set, validates HMAC-SHA256 signature
        from the x-bluebubbles-signature header. Otherwise accepts all
        webhooks (development mode).
        """
        if not self._webhook_secret:
            return True

        signature_header = headers.get("x-bluebubbles-signature", "")
        if not signature_header:
            return False

        computed_sig = hmac.new(
            self._webhook_secret.encode(),
            raw_body,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(computed_sig, signature_header)

    async def send_response(self, chat_id: str, response: NormalizedResponse) -> None:
        """Send a text message via BlueBubbles API.

        Args:
            chat_id: The chat GUID (e.g. "iMessage;-;+1234567890").
            response: The response to send.
        """
        chunks = split_message(response.text, IMESSAGE_MAX_MESSAGE_LENGTH)

        for chunk in chunks:
            payload = {
                "chatGuid": chat_id,
                "message": chunk,
                "method": "private-api",
            }

            resp = await self._client.post(
                f"{self._server_url}/api/v1/message/text",
                json=payload,
                params={"password": self._password},
            )

            if resp.status_code != 200:
                # Fall back to AppleScript method
                logger.warning(
                    f"BlueBubbles private-api send failed ({resp.status_code}), "
                    f"retrying with apple-script method"
                )
                payload["method"] = "apple-script"
                resp = await self._client.post(
                    f"{self._server_url}/api/v1/message/text",
                    json=payload,
                    params={"password": self._password},
                )
                if resp.status_code != 200:
                    logger.error(
                        f"BlueBubbles sendMessage failed: {resp.status_code} {resp.text}"
                    )

    async def send_typing_indicator(self, chat_id: str) -> None:
        """Send typing indicator via BlueBubbles private API."""
        try:
            await self._client.post(
                f"{self._server_url}/api/v1/chat/{chat_id}/typing",
                params={"password": self._password},
                json={"status": "typing"},
            )
        except Exception as e:
            logger.debug(f"Failed to send typing indicator: {e}")

    def get_media_download_kwargs(self) -> dict[str, Any]:
        """Return kwargs for ``process_media_items()``."""
        return {
            "bluebubbles_client": self._client,
            "bluebubbles_server_url": self._server_url,
            "bluebubbles_password": self._password,
        }

    def get_download_client(self) -> tuple[httpx.AsyncClient, str, str]:
        """Return (client, server_url, password) for media downloads."""
        return self._client, self._server_url, self._password

    async def register_webhook(self, webhook_url: str) -> dict:
        """Register a webhook URL with the BlueBubbles server.

        Args:
            webhook_url: Full webhook URL (e.g. https://example.com/api/v1/webhooks/imessage).

        Returns:
            BlueBubbles API response dict.
        """
        # First, list existing webhooks to avoid duplicates
        list_resp = await self._client.get(
            f"{self._server_url}/api/v1/server/webhooks",
            params={"password": self._password},
        )

        if list_resp.status_code == 200:
            existing = list_resp.json().get("data", [])
            for hook in existing:
                if hook.get("url") == webhook_url:
                    logger.info(f"Webhook already registered: {webhook_url}")
                    return {"status": "already_registered", "data": hook}

        # Register new webhook
        payload = {
            "url": webhook_url,
            "events": [
                "new-message",
                "updated-message",
                "message-send-error",
                "typing-indicator",
            ],
        }

        resp = await self._client.post(
            f"{self._server_url}/api/v1/server/webhooks",
            json=payload,
            params={"password": self._password},
        )

        result = resp.json()
        if resp.status_code == 200:
            logger.info(f"Webhook registered: {webhook_url}")
        else:
            logger.error(f"Failed to register webhook: {resp.status_code} {resp.text}")

        return result

    async def get_server_info(self) -> dict:
        """Get BlueBubbles server info."""
        resp = await self._client.get(
            f"{self._server_url}/api/v1/server/info",
            params={"password": self._password},
        )
        return resp.json()


def _media_type_from_mime(mime_type: str) -> str:
    """Map MIME type to a generic media type string."""
    if mime_type.startswith("image/"):
        return "image"
    if mime_type.startswith("video/"):
        return "video"
    if mime_type.startswith("audio/"):
        return "audio"
    return "document"
