"""Multi-platform chat integration for Claude Agent SDK.

Provides adapters for Telegram, WhatsApp, and Zalo that reuse
the existing per-user session isolation, history tracking, and agent invocation.
"""

from platforms.base import NormalizedMessage, NormalizedResponse, Platform, PlatformAdapter

__all__ = [
    "NormalizedMessage",
    "NormalizedResponse",
    "Platform",
    "PlatformAdapter",
]
