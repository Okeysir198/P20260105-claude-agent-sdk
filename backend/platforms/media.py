"""Platform media download and processing.

Downloads media files from Telegram and WhatsApp, then processes them into:
- Base64 content blocks for images (Claude can "see" them)
- Filesystem files via FileStorage for documents (agent accesses via tools)
"""

import base64
import logging
import mimetypes
from dataclasses import dataclass, field

import httpx

from agent.core.file_storage import FileStorage, FileStorageError

logger = logging.getLogger(__name__)

# Limits
MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024  # 50MB
DOWNLOAD_TIMEOUT = 60.0  # seconds

# MIME types that Claude can process as vision content blocks
VISION_MIME_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}


@dataclass
class ProcessedMedia:
    """Result of processing media items from a platform message."""

    content_blocks: list[dict] = field(default_factory=list)
    """Base64 image content blocks for inline vision."""

    file_annotations: list[str] = field(default_factory=list)
    """Text annotations for files saved to filesystem."""

    errors: list[str] = field(default_factory=list)
    """Per-item error descriptions (non-fatal)."""


async def download_telegram_file(
    file_id: str,
    bot_token: str,
    client: httpx.AsyncClient,
) -> tuple[bytes, str, str]:
    """Download a file from Telegram by file_id.

    Args:
        file_id: Telegram file_id from the message.
        bot_token: Bot token for API authentication.
        client: httpx client to use for requests.

    Returns:
        Tuple of (file_bytes, file_path, mime_type).

    Raises:
        httpx.HTTPStatusError: If API calls fail.
        ValueError: If file is too large.
    """
    api_base = f"https://api.telegram.org/bot{bot_token}"

    # Step 1: Get file path from Telegram API
    resp = await client.get(
        f"{api_base}/getFile",
        params={"file_id": file_id},
        timeout=DOWNLOAD_TIMEOUT,
    )
    resp.raise_for_status()
    result = resp.json().get("result", {})
    file_path = result.get("file_path", "")
    file_size = result.get("file_size", 0)

    if not file_path:
        raise ValueError(f"Telegram getFile returned no file_path for {file_id}")

    if file_size > MAX_DOWNLOAD_BYTES:
        raise ValueError(
            f"File too large: {file_size} bytes (max {MAX_DOWNLOAD_BYTES})"
        )

    # Step 2: Download the actual file
    download_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
    file_resp = await client.get(download_url, timeout=DOWNLOAD_TIMEOUT)
    file_resp.raise_for_status()
    content = file_resp.content

    if len(content) > MAX_DOWNLOAD_BYTES:
        raise ValueError(
            f"Downloaded file too large: {len(content)} bytes (max {MAX_DOWNLOAD_BYTES})"
        )

    # Guess MIME type from file path
    mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"

    return content, file_path, mime_type


async def download_whatsapp_file(
    media_id: str,
    access_token: str,
    client: httpx.AsyncClient,
    api_base: str = "https://graph.facebook.com/v20.0",
) -> tuple[bytes, str]:
    """Download a file from WhatsApp by media_id.

    Args:
        media_id: WhatsApp media ID from the message.
        access_token: Access token for API authentication.
        client: httpx client to use for requests.
        api_base: Graph API base URL.

    Returns:
        Tuple of (file_bytes, mime_type).

    Raises:
        httpx.HTTPStatusError: If API calls fail.
        ValueError: If file is too large.
    """
    # Step 1: Get the download URL
    resp = await client.get(
        f"{api_base}/{media_id}",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=DOWNLOAD_TIMEOUT,
    )
    resp.raise_for_status()
    media_info = resp.json()
    download_url = media_info.get("url", "")
    mime_type = media_info.get("mime_type", "application/octet-stream")
    file_size = media_info.get("file_size", 0)

    if not download_url:
        raise ValueError(f"WhatsApp media API returned no URL for {media_id}")

    if file_size > MAX_DOWNLOAD_BYTES:
        raise ValueError(
            f"File too large: {file_size} bytes (max {MAX_DOWNLOAD_BYTES})"
        )

    # Step 2: Download the binary content
    file_resp = await client.get(
        download_url,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=DOWNLOAD_TIMEOUT,
    )
    file_resp.raise_for_status()
    content = file_resp.content

    if len(content) > MAX_DOWNLOAD_BYTES:
        raise ValueError(
            f"Downloaded file too large: {len(content)} bytes (max {MAX_DOWNLOAD_BYTES})"
        )

    return content, mime_type


async def download_bluebubbles_file(
    attachment_guid: str,
    server_url: str,
    password: str,
    client: httpx.AsyncClient,
) -> tuple[bytes, str]:
    """Download a file from BlueBubbles by attachment GUID.

    Args:
        attachment_guid: BlueBubbles attachment GUID.
        server_url: BlueBubbles server base URL.
        password: Server password for authentication.
        client: httpx client to use for requests.

    Returns:
        Tuple of (file_bytes, mime_type).

    Raises:
        httpx.HTTPStatusError: If API calls fail.
        ValueError: If file is too large.
    """
    resp = await client.get(
        f"{server_url}/api/v1/attachment/{attachment_guid}/download",
        params={"password": password},
        timeout=DOWNLOAD_TIMEOUT,
    )
    resp.raise_for_status()

    content = resp.content
    if len(content) > MAX_DOWNLOAD_BYTES:
        raise ValueError(
            f"Downloaded file too large: {len(content)} bytes (max {MAX_DOWNLOAD_BYTES})"
        )

    # Get MIME type from content-type header, fall back to octet-stream
    content_type = resp.headers.get("content-type", "application/octet-stream")
    mime_type = content_type.split(";")[0].strip()

    return content, mime_type


def _guess_filename(media_item: dict, mime_type: str) -> str:
    """Generate a filename for a media item if none is provided."""
    file_name = media_item.get("file_name", "")
    if file_name:
        return file_name

    # Generate from type + extension
    media_type = media_item.get("type", "file")

    # Strip MIME parameters (e.g. "audio/ogg; codecs=opus" → "audio/ogg")
    # mimetypes.guess_extension() can't handle params
    base_mime = mime_type.split(";")[0].strip()
    ext = mimetypes.guess_extension(base_mime) or ""

    # Override obscure extensions with common ones
    # (mimetypes returns .oga for audio/ogg, but .ogg is universally expected)
    _EXT_OVERRIDES = {
        ".oga": ".ogg",
        ".ogx": ".ogg",
    }
    ext = _EXT_OVERRIDES.get(ext, ext)

    return f"{media_type}{ext}"


async def process_media_items(
    media_list: list[dict],
    platform: str,
    file_storage: FileStorage,
    *,
    # Telegram kwargs
    bot_token: str = "",
    telegram_client: httpx.AsyncClient | None = None,
    # WhatsApp kwargs
    access_token: str = "",
    whatsapp_client: httpx.AsyncClient | None = None,
    whatsapp_api_base: str = "https://graph.facebook.com/v20.0",
    # BlueBubbles (iMessage) kwargs
    bluebubbles_server_url: str = "",
    bluebubbles_password: str = "",
    bluebubbles_client: httpx.AsyncClient | None = None,
) -> ProcessedMedia:
    """Download and process media items from a platform message.

    Images (jpeg/png/gif/webp) are converted to base64 content blocks for
    inline vision. Other files are saved to FileStorage for agent tool access.

    Args:
        media_list: List of media dicts from NormalizedMessage.media.
        platform: Platform name ("telegram" or "whatsapp").
        file_storage: FileStorage instance for saving non-image files.
        bot_token: Telegram bot token (required for telegram).
        telegram_client: httpx client for Telegram API calls.
        access_token: WhatsApp access token (required for whatsapp).
        whatsapp_client: httpx client for WhatsApp API calls.
        whatsapp_api_base: WhatsApp Graph API base URL.

    Returns:
        ProcessedMedia with content blocks, file annotations, and errors.
    """
    result = ProcessedMedia()

    for item in media_list:
        try:
            # Download the file
            if platform == "telegram":
                file_id = item.get("file_id", "")
                if not file_id or not bot_token or not telegram_client:
                    result.errors.append(
                        f"Missing Telegram download params for {item.get('type')}"
                    )
                    continue

                content, _, detected_mime = await download_telegram_file(
                    file_id, bot_token, telegram_client
                )
                # Prefer item's mime_type if set, else use detected
                mime_type = item.get("mime_type") or detected_mime

            elif platform == "whatsapp":
                media_id = item.get("media_id", "")
                if not media_id or not access_token or not whatsapp_client:
                    result.errors.append(
                        f"Missing WhatsApp download params for {item.get('type')}"
                    )
                    continue

                content, detected_mime = await download_whatsapp_file(
                    media_id, access_token, whatsapp_client, whatsapp_api_base
                )
                mime_type = item.get("mime_type") or detected_mime

            elif platform == "imessage":
                attachment_guid = item.get("attachment_guid", "")
                if not attachment_guid or not bluebubbles_server_url or not bluebubbles_client:
                    result.errors.append(
                        f"Missing BlueBubbles download params for {item.get('type')}"
                    )
                    continue

                content, detected_mime = await download_bluebubbles_file(
                    attachment_guid, bluebubbles_server_url,
                    bluebubbles_password, bluebubbles_client
                )
                mime_type = item.get("mime_type") or detected_mime

            else:
                result.errors.append(f"Unsupported platform for media: {platform}")
                continue

            # Process based on MIME type
            if mime_type in VISION_MIME_TYPES:
                # Image → base64 content block for Claude vision
                b64_data = base64.standard_b64encode(content).decode("ascii")
                result.content_blocks.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": mime_type,
                        "data": b64_data,
                    },
                })
                logger.info(
                    f"Processed {platform} image: {mime_type}, "
                    f"{len(content)} bytes → base64 content block"
                )
            else:
                # Document/file → save to FileStorage
                file_name = _guess_filename(item, mime_type)
                try:
                    metadata = await file_storage.save_input_file(
                        content=content,
                        filename=file_name,
                        content_type=mime_type,
                    )
                    result.file_annotations.append(
                        f"[File received: {file_name} — "
                        f"saved to input/{metadata.safe_name}]"
                    )
                    logger.info(
                        f"Saved {platform} file: {file_name} → "
                        f"input/{metadata.safe_name} ({len(content)} bytes)"
                    )
                except FileStorageError as e:
                    result.errors.append(f"Failed to save file {file_name}: {e}")
                    logger.warning(f"FileStorage error for {file_name}: {e}")

        except Exception as e:
            media_type = item.get("type", "unknown")
            error_msg = f"Failed to download {platform} {media_type}: {e}"
            result.errors.append(error_msg)
            logger.warning(error_msg, exc_info=True)

    return result
