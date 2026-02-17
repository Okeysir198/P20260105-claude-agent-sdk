"""Telegram webhook setup helper.

Provides a function and CLI integration for registering the webhook URL
with the Telegram Bot API.
"""

import asyncio
import logging

logger = logging.getLogger(__name__)


async def setup_telegram_webhook(webhook_url: str) -> dict:
    """Register the webhook URL with Telegram.

    Args:
        webhook_url: Full URL for the webhook endpoint,
            e.g. ``https://example.com/api/v1/webhooks/telegram``.

    Returns:
        Telegram API response dict.
    """
    from platforms.adapters.telegram import TelegramAdapter

    adapter = TelegramAdapter()

    # Get bot info
    me = await adapter.get_me()
    bot_info = me.get("result", {})
    logger.info(
        f"Bot: @{bot_info.get('username', 'unknown')} "
        f"(id: {bot_info.get('id', 'unknown')})"
    )

    # Set webhook
    result = await adapter.set_webhook(webhook_url)

    # Get current webhook info
    info = await adapter.get_webhook_info()
    webhook_info = info.get("result", {})
    logger.info(f"Webhook URL: {webhook_info.get('url', 'not set')}")
    logger.info(
        f"Pending updates: {webhook_info.get('pending_update_count', 0)}"
    )

    return result


def run_setup(webhook_url: str) -> None:
    """Synchronous entry point for CLI usage."""
    result = asyncio.run(setup_telegram_webhook(webhook_url))
    if result.get("ok"):
        print(f"Webhook set successfully: {webhook_url}")
    else:
        print(f"Failed to set webhook: {result}")
