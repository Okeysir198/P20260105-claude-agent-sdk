"""Base platform adapter abstraction.

Defines the interface that all platform adapters must implement, plus
shared data types for normalized inbound/outbound messages.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum


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


class PlatformAdapter(ABC):
    """Abstract base for platform-specific message adapters.

    Each adapter handles parsing inbound webhooks, verifying signatures,
    and sending responses back through the platform's API.
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

    @abstractmethod
    async def send_typing_indicator(self, chat_id: str) -> None:
        """Send a typing/composing indicator to the platform chat."""

    async def aclose(self) -> None:
        """Close underlying resources (HTTP clients, connections).

        Subclasses should override this if they hold resources that need cleanup.
        """
