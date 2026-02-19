"""Zalo Official Account (OA) adapter.

Handles parsing Zalo webhook events, token management,
and sending responses via the Zalo OA API v3.
"""

import logging
import os
import re

import httpx

from platforms.base import NormalizedMessage, NormalizedResponse, Platform, PlatformAdapter

logger = logging.getLogger(__name__)

ZALO_OA_API_BASE = "https://openapi.zalo.me/v3/oa"


class ZaloAdapter(PlatformAdapter):
    """Adapter for the Zalo Official Account API."""

    platform = Platform.ZALO

    def __init__(self) -> None:
        self._access_token = os.environ["ZALO_OA_ACCESS_TOKEN"]
        self._app_secret = os.getenv("ZALO_APP_SECRET", "")
        self._client = httpx.AsyncClient(timeout=30.0)

    def _auth_headers(self) -> dict[str, str]:
        """Build authorization headers with the current access token."""
        return {"access_token": self._access_token}

    def update_access_token(self, new_token: str) -> None:
        """Update the access token without recreating the HTTP client."""
        self._access_token = new_token
        logger.info("Zalo OA access token updated")

    def parse_inbound(self, raw_payload: dict) -> NormalizedMessage | None:
        """Parse a Zalo webhook event into a NormalizedMessage.

        Zalo sends events like:
        {
            "event_name": "user_send_text",
            "sender": {"id": "user_id"},
            "recipient": {"id": "oa_id"},
            "message": {"text": "Hello", "msg_id": "..."}
        }
        """
        event_name = raw_payload.get("event_name", "")

        # Only handle text messages for now
        if event_name != "user_send_text":
            logger.debug(f"Ignoring Zalo event: {event_name}")
            return None

        sender = raw_payload.get("sender", {})
        user_id = sender.get("id", "")
        message = raw_payload.get("message", {})
        text = message.get("text", "")

        if not user_id or not text:
            return None

        return NormalizedMessage(
            platform=Platform.ZALO,
            platform_user_id=user_id,
            platform_chat_id=user_id,  # Zalo uses user_id as chat_id for 1:1
            text=text,
            metadata={
                "msg_id": message.get("msg_id", ""),
                "event_name": event_name,
            },
        )

    def verify_signature(self, raw_body: bytes, headers: dict[str, str]) -> bool:
        """Zalo uses app secret validation differently — accept all for now.

        Zalo's webhook verification happens at the OA configuration level,
        not per-request HMAC. Can be enhanced later with MAC validation.
        """
        return True

    @staticmethod
    def _format_text(text: str) -> str:
        """Strip all markdown for clean plain text on Zalo.

        Zalo doesn't support any markdown formatting, so we remove all
        syntax markers while preserving the readable content.
        """
        # Remove fenced code block markers, keep content
        text = re.sub(r"```[a-zA-Z]*\n?", "", text)

        # Strip inline backticks
        text = re.sub(r"`([^`]+)`", r"\1", text)

        # Links: [text](url) → text (url)
        text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)

        # Images: ![alt](url) → alt (url)
        text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r"\1 (\2)", text)

        # Headers: strip # prefix
        text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)

        # Bold/italic markers: **text**, __text__, *text*, _text_
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        text = re.sub(r"__(.+?)__", r"\1", text)
        text = re.sub(r"(?<!\w)\*(.+?)\*(?!\w)", r"\1", text)
        text = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r"\1", text)

        # Strikethrough: ~~text~~
        text = re.sub(r"~~(.+?)~~", r"\1", text)

        # Blockquotes: strip > prefix
        text = re.sub(r"^>\s?", "", text, flags=re.MULTILINE)

        # Horizontal rules
        text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)

        return text

    async def send_response(self, chat_id: str, response: NormalizedResponse) -> None:
        """Send a customer service message via Zalo OA API v3."""
        payload = {
            "recipient": {"user_id": chat_id},
            "message": {"text": self._format_text(response.text)},
        }

        resp = await self._client.post(
            f"{ZALO_OA_API_BASE}/message/cs",
            json=payload,
            headers=self._auth_headers(),
        )

        if resp.status_code != 200:
            logger.error(f"Zalo send message failed: {resp.status_code} {resp.text}")
        else:
            result = resp.json()
            if result.get("error") != 0:
                logger.error(f"Zalo API error: {result}")

