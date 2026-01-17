"""API configuration settings."""

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    app_name: str = "Claude Agent SDK API"
    api_v1_prefix: str = "/api/v1"
    host: str = "0.0.0.0"
    port: int = 7001
    debug: bool = False
    client_pool_size: int = Field(default=3, description="Size of the Claude SDK client pool")


settings = Settings()
