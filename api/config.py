"""API configuration settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    app_name: str = "Claude Agent SDK API"
    api_v1_prefix: str = "/api/v1"
    host: str = "0.0.0.0"
    port: int = 19830
    debug: bool = False


settings = Settings()
