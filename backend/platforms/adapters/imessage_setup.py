"""BlueBubbles iMessage webhook setup helper.

Provides a function and CLI integration for registering the webhook URL
with the BlueBubbles server.
"""

import asyncio
import logging

logger = logging.getLogger(__name__)


async def setup_imessage_webhook(webhook_url: str) -> dict:
    """Register the webhook URL with BlueBubbles.

    Args:
        webhook_url: Full URL for the webhook endpoint,
            e.g. ``https://example.com/api/v1/webhooks/imessage``.

    Returns:
        BlueBubbles API response dict.
    """
    from platforms.adapters.imessage import IMessageAdapter

    adapter = IMessageAdapter()

    # Get server info
    info = await adapter.get_server_info()
    server_data = info.get("data", {})
    logger.info(
        f"BlueBubbles server: v{server_data.get('server_version', 'unknown')} "
        f"(macOS {server_data.get('os_version', 'unknown')})"
    )

    # Register webhook
    result = await adapter.register_webhook(webhook_url)

    await adapter.aclose()
    return result


def run_setup(webhook_url: str) -> None:
    """Synchronous entry point for CLI usage."""
    result = asyncio.run(setup_imessage_webhook(webhook_url))
    status = result.get("status", "")
    if status == "already_registered":
        print(f"Webhook already registered: {webhook_url}")
    elif result.get("data"):
        print(f"Webhook registered successfully: {webhook_url}")
    else:
        print(f"Failed to register webhook: {result}")
