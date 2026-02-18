"""Credential store for email provider tokens and app passwords.

Provides per-user storage for Gmail OAuth tokens and IMAP app passwords.
Supports Gmail (OAuth), Yahoo, Outlook, iCloud, Zoho, and custom IMAP providers.
Includes env-var auto-seeding for deployment defaults.
"""
import imaplib
import json
import logging
import os
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Provider auto-detection: email domain -> IMAP/SMTP server config
PROVIDER_CONFIG: dict[str, dict[str, Any]] = {
    "gmail": {
        "name": "Gmail",
        "imap_server": "imap.gmail.com",
        "imap_port": 993,
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
    },
    "yahoo": {
        "name": "Yahoo Mail",
        "imap_server": "imap.mail.yahoo.com",
        "imap_port": 993,
        "smtp_server": "smtp.mail.yahoo.com",
        "smtp_port": 587,
    },
    "outlook": {
        "name": "Outlook",
        "imap_server": "outlook.office365.com",
        "imap_port": 993,
        "smtp_server": "smtp.office365.com",
        "smtp_port": 587,
    },
    "icloud": {
        "name": "iCloud",
        "imap_server": "imap.mail.me.com",
        "imap_port": 993,
        "smtp_server": "smtp.mail.me.com",
        "smtp_port": 587,
    },
    "zoho": {
        "name": "Zoho Mail",
        "imap_server": "imap.zoho.com",
        "imap_port": 993,
        "smtp_server": "smtp.zoho.com",
        "smtp_port": 587,
    },
}

# Email domain -> provider ID mapping
DOMAIN_TO_PROVIDER: dict[str, str] = {
    "gmail.com": "gmail",
    "googlemail.com": "gmail",
    "yahoo.com": "yahoo",
    "yahoo.co.uk": "yahoo",
    "yahoo.co.jp": "yahoo",
    "ymail.com": "yahoo",
    "outlook.com": "outlook",
    "hotmail.com": "outlook",
    "live.com": "outlook",
    "msn.com": "outlook",
    "icloud.com": "icloud",
    "me.com": "icloud",
    "mac.com": "icloud",
    "zoho.com": "zoho",
    "zohomail.com": "zoho",
}


def detect_provider(email_address: str) -> str:
    """Detect email provider from email address domain.

    Args:
        email_address: Email address to detect provider for

    Returns:
        Provider ID (e.g., "gmail", "yahoo", "outlook") or "custom"
    """
    if not email_address or "@" not in email_address:
        return "custom"

    domain = email_address.split("@")[1].lower()
    return DOMAIN_TO_PROVIDER.get(domain, "custom")


def get_provider_display_name(provider: str) -> str:
    """Get human-readable display name for a provider."""
    config = PROVIDER_CONFIG.get(provider)
    if config:
        return config["name"]
    return provider.capitalize()


@dataclass
class EmailCredentials:
    """Credentials for email providers (OAuth or app password)."""
    provider: str = ""  # "gmail", "yahoo", "outlook", "icloud", "zoho", "custom"
    auth_type: str = "app_password"  # "oauth" or "app_password"
    email_address: str | None = None

    # OAuth fields (used by Gmail)
    access_token: str = ""
    refresh_token: str = ""
    token_type: str = "Bearer"
    expires_at: str | None = None  # ISO format timestamp

    # App password fields (used by IMAP providers)
    app_password: str = ""

    # IMAP/SMTP server config (auto-detected or custom)
    imap_server: str = ""
    imap_port: int = 993
    smtp_server: str = ""
    smtp_port: int = 587

    def is_expired(self) -> bool:
        """Check if the access token is expired."""
        if self.auth_type != "oauth" or not self.expires_at:
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
    def from_dict(cls, data: dict[str, Any]) -> "EmailCredentials":
        """Create credentials from dictionary, handling legacy format."""
        # Handle legacy OAuthCredentials format
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known_fields}

        # Migrate legacy Yahoo credentials: app_password stored in refresh_token
        if (filtered.get("provider") == "yahoo"
                and not filtered.get("app_password")
                and filtered.get("refresh_token")):
            filtered["app_password"] = filtered["refresh_token"]
            filtered["auth_type"] = "app_password"

        # Auto-detect auth_type if not set
        if "auth_type" not in filtered:
            if filtered.get("provider") == "gmail" and filtered.get("access_token"):
                filtered["auth_type"] = "oauth"
            else:
                filtered["auth_type"] = "app_password"

        # Auto-fill server config from provider
        provider = filtered.get("provider", "custom")
        if provider in PROVIDER_CONFIG:
            config = PROVIDER_CONFIG[provider]
            if not filtered.get("imap_server"):
                filtered["imap_server"] = config["imap_server"]
            if not filtered.get("imap_port"):
                filtered["imap_port"] = config["imap_port"]
            if not filtered.get("smtp_server"):
                filtered["smtp_server"] = config["smtp_server"]
            if not filtered.get("smtp_port"):
                filtered["smtp_port"] = config["smtp_port"]

        return cls(**filtered)


# Backward compatibility alias
OAuthCredentials = EmailCredentials


class CredentialStore:
    """Per-user credential storage for email provider tokens/passwords.

    Stores credentials in: data/{username}/email_credentials/{provider}.json
    """

    # All supported providers
    SUPPORTED_PROVIDERS = ("gmail", "yahoo", "outlook", "icloud", "zoho", "custom")

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
            provider: Provider name

        Returns:
            Path to the provider's credential file
        """
        # Sanitize provider name for filesystem
        safe_provider = "".join(c for c in provider if c.isalnum() or c in "-_")
        if not safe_provider:
            raise ValueError(f"Invalid provider name: {provider}")
        return self._credentials_dir / f"{safe_provider}.json"

    def save_credentials(self, credentials: EmailCredentials) -> None:
        """Save credentials for a provider.

        Args:
            credentials: EmailCredentials object to save
        """
        provider = credentials.provider
        if not provider:
            raise ValueError("Provider must be specified in credentials")

        cred_file = self._get_provider_file(provider)
        cred_data = credentials.to_dict()

        try:
            with open(cred_file, "w") as f:
                json.dump(cred_data, f, indent=2)
            logger.info(f"Saved {provider} credentials for user {self._username}")
        except IOError as e:
            logger.error(f"Failed to save {provider} credentials: {e}")
            raise

    def load_credentials(self, provider: str) -> EmailCredentials | None:
        """Load credentials for a provider.

        Args:
            provider: Provider name

        Returns:
            EmailCredentials if found, None otherwise
        """
        cred_file = self._get_provider_file(provider)

        if not cred_file.exists():
            return None

        try:
            with open(cred_file, "r") as f:
                cred_data = json.load(f)
            credentials = EmailCredentials.from_dict(cred_data)
            logger.debug(f"Loaded {provider} credentials for user {self._username}")
            return credentials
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load {provider} credentials: {e}")
            return None

    def delete_credentials(self, provider: str) -> bool:
        """Delete credentials for a provider.

        Args:
            provider: Provider name

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
        """Check if credentials exist for a provider."""
        return self._get_provider_file(provider).exists()

    def get_connected_providers(self) -> list[str]:
        """Get list of connected email providers.

        Returns:
            List of provider names that have stored credentials
        """
        providers = []
        if not self._credentials_dir.exists():
            return providers

        for cred_file in self._credentials_dir.glob("*.json"):
            provider = cred_file.stem
            providers.append(provider)
        return sorted(providers)

    def get_all_accounts(self) -> list[dict[str, Any]]:
        """Get summary of all connected email accounts.

        Returns:
            List of account info dicts with provider, email, auth_type
        """
        accounts = []
        for provider in self.get_connected_providers():
            creds = self.load_credentials(provider)
            if creds:
                accounts.append({
                    "provider": provider,
                    "provider_name": get_provider_display_name(provider),
                    "email": creds.email_address or "",
                    "auth_type": creds.auth_type,
                })
        return accounts


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


def _make_credential_key(provider: str, email_address: str, existing_keys: list[str]) -> str:
    """Generate a unique credential key for an email account.

    For the first/only account of a provider: returns provider name (e.g., "yahoo").
    For additional accounts of the same provider: returns "provider-localpart"
    (e.g., "gmail-nthanhtrung198").

    Args:
        provider: Provider ID (e.g., "gmail", "yahoo")
        email_address: Full email address
        existing_keys: List of already-used credential keys

    Returns:
        Unique credential key string
    """
    # If this provider key isn't taken yet, use the simple provider name
    if provider not in existing_keys:
        return provider

    # Otherwise, append the local part of the email address
    local_part = email_address.split("@")[0] if "@" in email_address else email_address
    # Sanitize: keep only alphanumeric, hyphens, underscores
    safe_local = re.sub(r"[^a-zA-Z0-9_-]", "", local_part)
    return f"{provider}-{safe_local}"


def _test_imap_connection(imap_server: str, imap_port: int, email_addr: str, app_password: str) -> bool:
    """Test IMAP connection by logging in and out.

    Args:
        imap_server: IMAP server hostname
        imap_port: IMAP server port
        email_addr: Email address for login
        app_password: App-specific password

    Returns:
        True if connection successful, False otherwise
    """
    try:
        client = imaplib.IMAP4_SSL(imap_server, imap_port)
        client.login(email_addr, app_password)
        client.logout()
        return True
    except Exception as e:
        logger.warning("IMAP connection test failed for %s on %s: %s", email_addr, imap_server, e)
        return False


def seed_credentials_from_env() -> int:
    """Seed email credentials from EMAIL_ACCOUNT_N_* environment variables.

    Scans for: EMAIL_ACCOUNT_1_EMAIL, EMAIL_ACCOUNT_1_PASSWORD, etc.
    Optional: EMAIL_ACCOUNT_N_IMAP_SERVER, EMAIL_ACCOUNT_N_IMAP_PORT

    All auto-seeded accounts are assigned to the admin user only.
    Other users must connect their email accounts via the frontend UI.

    Skips accounts where credential file already exists (won't overwrite
    UI-modified credentials). Tests IMAP connection before saving.

    Returns:
        Number of newly seeded accounts.
    """
    seeded = 0
    n = 1
    username = "admin"

    while True:
        prefix = f"EMAIL_ACCOUNT_{n}_"
        email_addr = os.environ.get(f"{prefix}EMAIL")

        if not email_addr:
            break

        password = os.environ.get(f"{prefix}PASSWORD", "")
        custom_imap_server = os.environ.get(f"{prefix}IMAP_SERVER")
        custom_imap_port = os.environ.get(f"{prefix}IMAP_PORT")

        n += 1

        if not password:
            logger.warning("EMAIL_ACCOUNT_%d: no PASSWORD set, skipping %s", n - 1, email_addr)
            continue

        # Detect provider from email domain
        provider = detect_provider(email_addr)

        # Resolve IMAP server config
        if custom_imap_server:
            imap_server = custom_imap_server
        elif provider in PROVIDER_CONFIG:
            imap_server = PROVIDER_CONFIG[provider]["imap_server"]
        else:
            logger.warning(
                "EMAIL_ACCOUNT_%d: unknown provider for %s and no IMAP_SERVER set, skipping",
                n - 1, email_addr,
            )
            continue

        imap_port = int(custom_imap_port) if custom_imap_port else (
            PROVIDER_CONFIG[provider]["imap_port"] if provider in PROVIDER_CONFIG else 993
        )

        # Get credential store for this user
        cred_store = get_credential_store(username)

        # Determine credential key (supports multiple accounts per provider)
        existing_keys = cred_store.get_connected_providers()
        cred_key = _make_credential_key(provider, email_addr, existing_keys)

        # Skip if credentials already exist (don't overwrite UI-modified ones)
        if cred_store.has_credentials(cred_key):
            logger.info(
                "Email account %s already configured (key: %s), skipping",
                email_addr, cred_key,
            )
            continue

        # Also check if this exact email is already saved under a different key
        already_exists = False
        for key in existing_keys:
            existing_creds = cred_store.load_credentials(key)
            if existing_creds and existing_creds.email_address == email_addr:
                logger.info(
                    "Email account %s already configured under key '%s', skipping",
                    email_addr, key,
                )
                already_exists = True
                break
        if already_exists:
            continue

        # Test IMAP connection before saving
        logger.info("Testing IMAP connection for %s (%s:%d)...", email_addr, imap_server, imap_port)
        if not _test_imap_connection(imap_server, imap_port, email_addr, password):
            logger.error(
                "EMAIL_ACCOUNT_%d: IMAP connection test failed for %s, skipping",
                n - 1, email_addr,
            )
            continue

        # Build SMTP config from provider if available
        smtp_server = ""
        smtp_port = 587
        if provider in PROVIDER_CONFIG:
            smtp_server = PROVIDER_CONFIG[provider].get("smtp_server", "")
            smtp_port = PROVIDER_CONFIG[provider].get("smtp_port", 587)

        # Save credentials
        credentials = EmailCredentials(
            provider=cred_key,
            auth_type="app_password",
            email_address=email_addr,
            app_password=password,
            imap_server=imap_server,
            imap_port=imap_port,
            smtp_server=smtp_server,
            smtp_port=smtp_port,
        )
        cred_store.save_credentials(credentials)
        seeded += 1
        logger.info("Auto-seeded email account: %s (key: %s, user: %s)", email_addr, cred_key, username)

    return seeded
