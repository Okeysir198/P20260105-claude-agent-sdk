"""Telegram Bot API adapter.

Handles parsing Telegram webhook payloads, signature verification,
and sending responses via the Telegram Bot API.
"""

import hmac
import logging
import os

import httpx

from platforms.base import NormalizedMessage, NormalizedResponse, Platform, PlatformAdapter

logger = logging.getLogger(__name__)

# Telegram message length limit
TELEGRAM_MAX_MESSAGE_LENGTH = 4096

# Telegram Bot API base URL
TELEGRAM_API_BASE = "https://api.telegram.org"


def _split_message(text: str, max_length: int = TELEGRAM_MAX_MESSAGE_LENGTH) -> list[str]:
    """Split a long message into chunks respecting the Telegram limit.

    Tries to split on paragraph boundaries first, then sentence boundaries,
    then falls back to hard wrapping.
    """
    if len(text) <= max_length:
        return [text]

    chunks: list[str] = []
    remaining = text

    while remaining:
        if len(remaining) <= max_length:
            chunks.append(remaining)
            break

        # Try to split on double newline (paragraph)
        split_pos = remaining.rfind("\n\n", 0, max_length)
        if split_pos > max_length // 2:
            chunks.append(remaining[:split_pos])
            remaining = remaining[split_pos + 2:]
            continue

        # Try single newline
        split_pos = remaining.rfind("\n", 0, max_length)
        if split_pos > max_length // 2:
            chunks.append(remaining[:split_pos])
            remaining = remaining[split_pos + 1:]
            continue

        # Try space
        split_pos = remaining.rfind(" ", 0, max_length)
        if split_pos > max_length // 2:
            chunks.append(remaining[:split_pos])
            remaining = remaining[split_pos + 1:]
            continue

        # Hard split
        chunks.append(remaining[:max_length])
        remaining = remaining[max_length:]

    return chunks


def _convert_markdown(text: str) -> str:
    """Convert Claude's markdown to Telegram MarkdownV2 format.

    Uses telegramify-markdown if available, otherwise falls back to
    sending plain text (Telegram renders it fine without formatting).
    """
    try:
        import telegramify_markdown

        return telegramify_markdown.markdownify(text)
    except ImportError:
        logger.debug("telegramify-markdown not installed, sending plain text")
        return text
    except Exception as e:
        logger.warning(f"Markdown conversion failed, sending plain text: {e}")
        return text


class TelegramAdapter(PlatformAdapter):
    """Adapter for the Telegram Bot API."""

    platform = Platform.TELEGRAM

    def __init__(self) -> None:
        self._bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
        self._webhook_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
        self._api_base = f"{TELEGRAM_API_BASE}/bot{self._bot_token}"
        self._client = httpx.AsyncClient(timeout=30.0)
        if not self._webhook_secret:
            logger.warning(
                "TELEGRAM_WEBHOOK_SECRET not set — webhook signature verification disabled. "
                "Set this in production for security."
            )

    async def aclose(self) -> None:
        """Close the underlying HTTP client to release resources."""
        await self._client.aclose()

    def parse_inbound(self, raw_payload: dict) -> NormalizedMessage | None:
        """Parse a Telegram Update object into a NormalizedMessage."""
        message = raw_payload.get("message") or raw_payload.get("edited_message")
        if not message:
            return None

        # Extract user info
        from_user = message.get("from", {})
        user_id = str(from_user.get("id", ""))
        chat_id = str(message.get("chat", {}).get("id", ""))

        if not user_id or not chat_id:
            return None

        # Extract text content
        text = message.get("text", "")
        caption = message.get("caption", "")

        # Handle /start command — send welcome
        if text.startswith("/start"):
            text = "Hello! I'd like to start chatting."

        media: list[dict] = []
        # Extract photo (largest resolution)
        if photos := message.get("photo"):
            largest = max(photos, key=lambda p: p.get("file_size", 0))
            media.append({
                "type": "photo",
                "file_id": largest["file_id"],
                "mime_type": "image/jpeg",
            })

        # Extract document
        if doc := message.get("document"):
            media.append({
                "type": "document",
                "file_id": doc["file_id"],
                "file_name": doc.get("file_name", ""),
                "mime_type": doc.get("mime_type", "application/octet-stream"),
            })

        # Extract voice
        if voice := message.get("voice"):
            media.append({
                "type": "voice",
                "file_id": voice["file_id"],
                "mime_type": voice.get("mime_type", "audio/ogg"),
            })

        # Extract sticker (non-animated, non-video only)
        if sticker := message.get("sticker"):
            if not sticker.get("is_animated") and not sticker.get("is_video"):
                media.append({
                    "type": "sticker",
                    "file_id": sticker["file_id"],
                    "mime_type": "image/webp",
                })

        effective_text = text or caption
        if not effective_text and not media:
            return None

        return NormalizedMessage(
            platform=Platform.TELEGRAM,
            platform_user_id=user_id,
            platform_chat_id=chat_id,
            text=effective_text,
            media=media,
            metadata={
                "message_id": message.get("message_id"),
                "from_username": from_user.get("username", ""),
                "from_first_name": from_user.get("first_name", ""),
            },
        )

    def verify_signature(self, raw_body: bytes, headers: dict[str, str]) -> bool:
        """Verify Telegram webhook using the secret token header."""
        if not self._webhook_secret:
            # No secret configured — accept all (development mode)
            return True

        provided_secret = headers.get("x-telegram-bot-api-secret-token", "")
        return hmac.compare_digest(provided_secret, self._webhook_secret)

    async def send_response(self, chat_id: str, response: NormalizedResponse) -> None:
        """Send a response message to Telegram, splitting if needed."""
        chunks = _split_message(response.text)

        for chunk in chunks:
            # Try sending with MarkdownV2 first, fall back to plain text
            converted = _convert_markdown(chunk)
            payload: dict = {
                "chat_id": chat_id,
                "text": converted,
                "parse_mode": "MarkdownV2",
            }

            resp = await self._client.post(
                f"{self._api_base}/sendMessage", json=payload
            )

            if resp.status_code != 200:
                # Retry without parse_mode if MarkdownV2 fails
                logger.warning(
                    f"Telegram sendMessage with MarkdownV2 failed ({resp.status_code}), "
                    f"retrying plain text"
                )
                payload = {"chat_id": chat_id, "text": chunk}
                resp = await self._client.post(
                    f"{self._api_base}/sendMessage", json=payload
                )
                if resp.status_code != 200:
                    logger.error(
                        f"Telegram sendMessage failed: {resp.status_code} {resp.text}"
                    )

    def get_download_client(self) -> tuple[httpx.AsyncClient, str]:
        """Return (client, bot_token) for media downloads."""
        return self._client, self._bot_token

    async def send_typing_indicator(self, chat_id: str) -> None:
        """Send typing action to Telegram chat."""
        try:
            await self._client.post(
                f"{self._api_base}/sendChatAction",
                json={"chat_id": chat_id, "action": "typing"},
            )
        except Exception as e:
            logger.debug(f"Failed to send typing indicator: {e}")

    async def set_webhook(self, webhook_url: str) -> dict:
        """Register the webhook URL with Telegram.

        Args:
            webhook_url: Full webhook URL (e.g., https://example.com/api/v1/webhooks/telegram).

        Returns:
            Telegram API response dict.
        """
        payload: dict = {"url": webhook_url}
        if self._webhook_secret:
            payload["secret_token"] = self._webhook_secret

        resp = await self._client.post(
            f"{self._api_base}/setWebhook", json=payload
        )
        result = resp.json()
        logger.info(f"setWebhook response: {result}")
        return result

    async def get_webhook_info(self) -> dict:
        """Get current webhook info from Telegram."""
        resp = await self._client.get(f"{self._api_base}/getWebhookInfo")
        return resp.json()

    async def get_me(self) -> dict:
        """Get bot info from Telegram."""
        resp = await self._client.get(f"{self._api_base}/getMe")
        return resp.json()
