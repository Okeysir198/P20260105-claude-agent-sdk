"""Unified webhook router for messaging platform integrations.

Provides a single entry point for all platform webhooks:
- POST /api/v1/webhooks/{platform_name} — receive inbound messages
- GET  /api/v1/webhooks/{platform_name} — handle platform verification handshakes

Webhooks ACK immediately (200) and process messages in background tasks.
"""

import asyncio
import json
import logging
import time

from fastapi import APIRouter, BackgroundTasks, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse

from platforms.adapters import get_adapter
from platforms.worker import process_platform_message

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhooks"])

# Thread-safe in-memory deduplication (message_id → timestamp).
# Prevents duplicate processing from webhook retries.
_dedup_lock = asyncio.Lock()
_processed_messages: dict[str, float] = {}
_MAX_DEDUP_ENTRIES = 10000
_DEDUP_TTL_SECONDS = 3600  # 1 hour


async def _is_duplicate(platform: str, message_id: str) -> bool:
    """Check if a message has already been processed (thread-safe)."""
    key = f"{platform}:{message_id}"

    async with _dedup_lock:
        if key in _processed_messages:
            return True

        # Evict stale entries when dict grows too large
        if len(_processed_messages) > _MAX_DEDUP_ENTRIES:
            cutoff = time.time() - _DEDUP_TTL_SECONDS
            stale_keys = [k for k, ts in _processed_messages.items() if ts < cutoff]
            for k in stale_keys:
                del _processed_messages[k]

        _processed_messages[key] = time.time()
        return False


@router.get("/webhooks/{platform_name}")
async def webhook_verify(platform_name: str, request: Request) -> Response:
    """Handle platform webhook verification (GET).

    Used by:
    - WhatsApp: Meta verification handshake (hub.mode, hub.verify_token, hub.challenge)
    - Telegram: Not required (uses setWebhook API call)
    """
    platform_key = platform_name.lower()
    adapter = get_adapter(platform_key)
    if not adapter:
        return JSONResponse(
            status_code=404,
            content={"error": f"Platform '{platform_name}' not configured"},
        )

    # WhatsApp verification handshake
    if platform_key == "whatsapp":
        from platforms.adapters.whatsapp import WhatsAppAdapter

        if isinstance(adapter, WhatsAppAdapter):
            params = dict(request.query_params)
            challenge = adapter.verify_webhook_challenge(params)
            if challenge:
                return PlainTextResponse(content=challenge)
            return JSONResponse(status_code=403, content={"error": "Verification failed"})

    return JSONResponse(content={"status": "ok"})


@router.post("/webhooks/{platform_name}")
async def webhook_receive(
    platform_name: str,
    request: Request,
    background_tasks: BackgroundTasks,
) -> JSONResponse:
    """Receive inbound webhook from a messaging platform.

    1. Verify signature (per-platform HMAC)
    2. Parse payload into NormalizedMessage
    3. ACK 200 immediately
    4. Process message in background task
    """
    platform_key = platform_name.lower()
    adapter = get_adapter(platform_key)
    if not adapter:
        return JSONResponse(
            status_code=404,
            content={"error": f"Platform '{platform_name}' not configured"},
        )

    # Read raw body for signature verification
    raw_body = await request.body()
    headers = {k.lower(): v for k, v in request.headers.items()}

    # Verify signature
    if not adapter.verify_signature(raw_body, headers):
        logger.warning(f"Webhook signature verification failed for {platform_key}")
        return JSONResponse(status_code=403, content={"error": "Invalid signature"})

    # Parse payload
    try:
        payload = json.loads(raw_body)
    except (json.JSONDecodeError, ValueError):
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})

    # Parse into normalized message
    normalized = adapter.parse_inbound(payload)
    if not normalized:
        # Not a user message (e.g., status update, delivery receipt)
        return JSONResponse(content={"status": "ignored"})

    # Whitelist check — block non-whitelisted numbers before any processing
    from api.services.whitelist_service import get_whitelist_service
    whitelist = get_whitelist_service()
    if not whitelist.is_allowed(platform_key, normalized.platform_user_id):
        logger.info(
            f"Blocked by whitelist: platform={platform_key}, "
            f"user={normalized.platform_user_id}"
        )
        return JSONResponse(content={"status": "ok"})

    # Deduplication
    message_id = normalized.metadata.get("message_id", "")
    if message_id and await _is_duplicate(platform_key, str(message_id)):
        logger.debug(f"Duplicate message ignored: {platform_key}:{message_id}")
        return JSONResponse(content={"status": "duplicate"})

    # Process in background — ACK immediately
    logger.info(
        f"Webhook received: platform={platform_key}, "
        f"user={normalized.platform_user_id}, "
        f"text_len={len(normalized.text)}"
    )
    background_tasks.add_task(process_platform_message, normalized, adapter)

    return JSONResponse(content={"status": "ok"})
