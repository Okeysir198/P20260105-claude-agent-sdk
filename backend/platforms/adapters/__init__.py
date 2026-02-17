"""Platform adapter registry.

Provides a centralized registry for looking up platform adapters by name.
"""

import logging
import os

from platforms.base import Platform, PlatformAdapter

logger = logging.getLogger(__name__)

# Registry of available adapters (populated lazily)
_registry: dict[str, PlatformAdapter] = {}
_initialized = False


def _init_registry() -> None:
    """Initialize the adapter registry from environment variables."""
    global _initialized
    if _initialized:
        return
    _initialized = True

    # Telegram
    if os.getenv("TELEGRAM_BOT_TOKEN"):
        try:
            from platforms.adapters.telegram import TelegramAdapter

            _registry[Platform.TELEGRAM] = TelegramAdapter()
            logger.info("Telegram adapter registered")
        except Exception as e:
            logger.warning(f"Failed to initialize Telegram adapter: {e}")

    # WhatsApp
    if os.getenv("WHATSAPP_ACCESS_TOKEN"):
        try:
            from platforms.adapters.whatsapp import WhatsAppAdapter

            _registry[Platform.WHATSAPP] = WhatsAppAdapter()
            logger.info("WhatsApp adapter registered")
        except Exception as e:
            logger.warning(f"Failed to initialize WhatsApp adapter: {e}")

    # Zalo
    if os.getenv("ZALO_OA_ACCESS_TOKEN"):
        try:
            from platforms.adapters.zalo import ZaloAdapter

            _registry[Platform.ZALO] = ZaloAdapter()
            logger.info("Zalo adapter registered")
        except Exception as e:
            logger.warning(f"Failed to initialize Zalo adapter: {e}")


def get_adapter(platform_name: str) -> PlatformAdapter | None:
    """Look up a platform adapter by name.

    Args:
        platform_name: Platform name string (e.g., "telegram", "whatsapp").

    Returns:
        The adapter instance, or None if not configured.
    """
    _init_registry()
    return _registry.get(platform_name)


def get_all_adapters() -> dict[str, PlatformAdapter]:
    """Get all registered adapters.

    Returns:
        Dict mapping platform name to adapter instance.
    """
    _init_registry()
    return dict(_registry)
