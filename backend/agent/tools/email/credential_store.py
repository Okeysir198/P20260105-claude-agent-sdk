"""Credential store for email OAuth tokens.

Provides per-user encrypted storage for Gmail and Yahoo OAuth tokens.
"""
import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class OAuthCredentials:
    """OAuth credentials for email providers."""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_at: str | None = None  # ISO format timestamp
    email_address: str | None = None
    provider: str = ""  # "gmail" or "yahoo"

    def is_expired(self) -> bool:
        """Check if the access token is expired."""
        if not self.expires_at:
            return False
        try:
            expire_time = datetime.fromisoformat(self.expires_at)
            return datetime.now() >= expire_time
        except (ValueError, TypeError):
            return False

    def to_dict(self) -> dict[str, Any]:
        """Convert credentials to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OAuthCredentials":
        """Create credentials from dictionary."""
        return cls(**data)


class CredentialStore:
    """Per-user credential storage for email OAuth tokens.

    Stores credentials in: data/{username}/email_credentials/{provider}.json
    """

    def __init__(self, username: str, data_dir: Path | None = None):
        """Initialize credential store for a user.

        Args:
            username: Username for data isolation
            data_dir: Optional data directory path
        """
        if not username:
            raise ValueError("Username is required for credential storage")

        if data_dir is None:
            from agent.core.storage import get_data_dir
            data_dir = get_data_dir()

        self._username = username
        self._user_dir = data_dir / username
        self._credentials_dir = self._user_dir / "email_credentials"
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        """Create credential directories if they don't exist."""
        self._credentials_dir.mkdir(parents=True, exist_ok=True)

    def _get_provider_file(self, provider: str) -> Path:
        """Get the credential file path for a provider.

        Args:
            provider: Provider name ("gmail" or "yahoo")

        Returns:
            Path to the provider's credential file
        """
        if provider not in ("gmail", "yahoo"):
            raise ValueError(f"Unsupported provider: {provider}")
        return self._credentials_dir / f"{provider}.json"

    def save_credentials(self, credentials: OAuthCredentials) -> None:
        """Save OAuth credentials for a provider.

        Args:
            credentials: OAuthCredentials object to save
        """
        provider = credentials.provider
        if not provider:
            raise ValueError("Provider must be specified in credentials")

        cred_file = self._get_provider_file(provider)

        # Add provider to dict if not present
        cred_data = credentials.to_dict()

        try:
            with open(cred_file, "w") as f:
                json.dump(cred_data, f, indent=2)
            logger.info(f"Saved {provider} credentials for user {self._username}")
        except IOError as e:
            logger.error(f"Failed to save {provider} credentials: {e}")
            raise

    def load_credentials(self, provider: str) -> OAuthCredentials | None:
        """Load OAuth credentials for a provider.

        Args:
            provider: Provider name ("gmail" or "yahoo")

        Returns:
            OAuthCredentials if found, None otherwise
        """
        cred_file = self._get_provider_file(provider)

        if not cred_file.exists():
            return None

        try:
            with open(cred_file, "r") as f:
                cred_data = json.load(f)
            credentials = OAuthCredentials.from_dict(cred_data)
            logger.debug(f"Loaded {provider} credentials for user {self._username}")
            return credentials
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load {provider} credentials: {e}")
            return None

    def delete_credentials(self, provider: str) -> bool:
        """Delete OAuth credentials for a provider.

        Args:
            provider: Provider name ("gmail" or "yahoo")

        Returns:
            True if credentials were deleted, False if not found
        """
        cred_file = self._get_provider_file(provider)

        if not cred_file.exists():
            return False

        try:
            cred_file.unlink()
            logger.info(f"Deleted {provider} credentials for user {self._username}")
            return True
        except IOError as e:
            logger.error(f"Failed to delete {provider} credentials: {e}")
            return False

    def has_credentials(self, provider: str) -> bool:
        """Check if credentials exist for a provider.

        Args:
            provider: Provider name ("gmail" or "yahoo")

        Returns:
            True if credentials exist, False otherwise
        """
        return self._get_provider_file(provider).exists()

    def get_connected_providers(self) -> list[str]:
        """Get list of connected email providers.

        Returns:
            List of provider names ("gmail", "yahoo") that have credentials
        """
        providers = []
        for provider in ("gmail", "yahoo"):
            if self.has_credentials(provider):
                providers.append(provider)
        return providers


def get_credential_store(username: str, data_dir: Path | None = None) -> CredentialStore:
    """Get a credential store for a user.

    Args:
        username: Username for data isolation
        data_dir: Optional data directory path

    Returns:
        CredentialStore instance for the user

    Raises:
        ValueError: If username is empty or None
    """
    return CredentialStore(username, data_dir)
