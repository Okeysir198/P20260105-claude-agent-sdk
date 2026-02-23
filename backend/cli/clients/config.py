"""Client configuration for CLI clients."""
import os
from dataclasses import dataclass, field


@dataclass
class ClientConfig:
    """Configuration for CLI clients.

    All settings can be overridden via environment variables or constructor arguments.
    """

    api_url: str = field(default_factory=lambda: os.getenv("API_URL", "http://localhost:7001"))
    api_key: str | None = field(default_factory=lambda: os.getenv("API_KEY"))
    username: str = field(default_factory=lambda: os.getenv("CLI_USERNAME", "admin"))
    password: str | None = field(default_factory=lambda: os.getenv("CLI_ADMIN_PASSWORD"))

    ws_chat_endpoint: str = "/api/v1/ws/chat"
    sessions_endpoint: str = "/api/v1/sessions"
    conversations_endpoint: str = "/api/v1/conversations"
    config_endpoint: str = "/api/v1/config"

    ws_ping_interval: int = 300
    ws_ping_timeout: int | None = None
    ws_close_timeout: int = 10
    http_timeout: float = 300.0

    @property
    def ws_url(self) -> str:
        """Convert HTTP URL to WebSocket URL."""
        return self.api_url.replace("https://", "wss://").replace("http://", "ws://").rstrip("/")

    @property
    def http_url(self) -> str:
        """Get normalized HTTP URL."""
        return self.api_url.rstrip("/")


def get_default_config() -> ClientConfig:
    """Get default client configuration from environment."""
    return ClientConfig()
