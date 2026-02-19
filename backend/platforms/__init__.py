"""Multi-platform chat integration for Claude Agent SDK.

Provides adapters for Telegram, WhatsApp, Zalo, and iMessage that reuse
the existing per-user session isolation, history tracking, and agent invocation.
"""

from platforms.base import NormalizedMessage, NormalizedResponse, Platform, PlatformAdapter, split_message

__all__ = [
    "NormalizedMessage",
    "NormalizedResponse",
    "Platform",
    "PlatformAdapter",
    "split_message",
]
