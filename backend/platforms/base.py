"""Base platform adapter abstraction.

Defines the interface that all platform adapters must implement, plus
shared data types and utilities for normalized inbound/outbound messages.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import httpx


class Platform(StrEnum):
    """Supported messaging platforms."""

    WEB = "web"
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    ZALO = "zalo"
    IMESSAGE = "imessage"


@dataclass
class NormalizedMessage:
    """Platform-agnostic inbound message representation.

    Media dict fields (varies by platform):
        type: str       — "photo", "document", "voice", "image", "video",
                          "audio", "sticker"
        file_id: str    — Telegram file_id (Telegram only)
        media_id: str   — WhatsApp media ID (WhatsApp only)
        file_name: str  — Original filename (documents)
        mime_type: str   — MIME type (e.g. "image/jpeg", "application/pdf")
    """

    platform: Platform
    platform_user_id: str
    platform_chat_id: str
    text: str = ""
    media: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class NormalizedResponse:
    """Platform-agnostic outbound response representation."""

    text: str
    media: list[dict] = field(default_factory=list)


def split_message(text: str, max_length: int) -> list[str]:
    """Split a long message into chunks respecting a character limit.

    Tries to split on paragraph boundaries first, then line boundaries,
    then word boundaries, and falls back to hard wrapping.
    """
    if len(text) <= max_length:
        return [text]

    chunks: list[str] = []
    remaining = text

    while remaining:
        if len(remaining) <= max_length:
            chunks.append(remaining)
            break

        # Try progressively less-ideal split points
        for separator, skip_len in [("\n\n", 2), ("\n", 1), (" ", 1)]:
            split_pos = remaining.rfind(separator, 0, max_length)
            if split_pos > max_length // 2:
                chunks.append(remaining[:split_pos])
                remaining = remaining[split_pos + skip_len:]
                break
        else:
            # Hard split as last resort
            chunks.append(remaining[:max_length])
            remaining = remaining[max_length:]

    return chunks


class PlatformAdapter(ABC):
    """Abstract base for platform-specific message adapters.

    Each adapter handles parsing inbound webhooks, verifying signatures,
    and sending responses back through the platform's API.

    Subclasses that hold an httpx.AsyncClient should store it as
    ``self._client`` so the default ``aclose()`` can clean it up.
    """

    platform: Platform

    @abstractmethod
    def parse_inbound(self, raw_payload: dict) -> NormalizedMessage | None:
        """Parse a raw webhook payload into a NormalizedMessage.

        Returns None if the payload is not a user message (e.g., status update).
        """

    @abstractmethod
    def verify_signature(self, raw_body: bytes, headers: dict[str, str]) -> bool:
        """Verify the webhook signature for authenticity."""

    @abstractmethod
    async def send_response(self, chat_id: str, response: NormalizedResponse) -> None:
        """Send a response message back to the platform chat."""

    async def send_typing_indicator(self, chat_id: str) -> None:
        """Send a typing/composing indicator to the platform chat.

        Default is a no-op. Override in adapters that support typing indicators.
        """

    def get_media_download_kwargs(self) -> dict[str, Any]:
        """Return platform-specific kwargs for ``process_media_items()``.

        Override in adapters that support media downloads. Returns an empty
        dict by default (no media download support).
        """
        return {}

    async def send_file(
        self,
        chat_id: str,
        file_path: str,
        filename: str,
        mime_type: str = "application/octet-stream",
    ) -> bool:
        """Send a file to the platform chat.

        Override in adapters that support file sending (e.g. Telegram, WhatsApp).
        Returns True if the file was sent successfully, False otherwise.
        """
        return False

    async def aclose(self) -> None:
        """Close underlying HTTP client if present."""
        client: httpx.AsyncClient | None = getattr(self, "_client", None)
        if client is not None:
            await client.aclose()
