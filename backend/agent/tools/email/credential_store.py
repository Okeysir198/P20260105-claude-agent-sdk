"""Credential store for email provider tokens and app passwords.

Provides per-user storage for Gmail OAuth tokens and IMAP app passwords.
Supports Gmail (OAuth), Yahoo, Outlook, iCloud, Zoho, and custom IMAP providers.
Includes env-var auto-seeding for deployment defaults.
"""
import imaplib
import json
import logging
import os
from dataclasses import dataclass, asdict, fields
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


def _sanitize_for_filesystem(name: str, allowed_extra: str = "-_") -> str:
    """Sanitize a string for safe filesystem use.

    Args:
        name: String to sanitize
        allowed_extra: Additional characters to allow beyond alphanumeric

    Returns:
        Sanitized string with only alphanumeric chars and allowed_extra
    """
    return "".join(c for c in name if c.isalnum() or c in allowed_extra)


def fill_provider_defaults(provider: str, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """Fill IMAP/SMTP server config from provider defaults.

    Args:
        provider: Provider ID (e.g., "gmail", "yahoo", "outlook")
        overrides: Optional dict with custom values that take precedence

    Returns:
        Dict with imap_server, imap_port, smtp_server, smtp_port filled in
    """
    overrides = overrides or {}
    result: dict[str, Any] = {}
    config = PROVIDER_CONFIG.get(provider, {})

    for key in ("imap_server", "imap_port", "smtp_server", "smtp_port"):
        result[key] = overrides.get(key) or config.get(key, "")

    # Ensure port defaults
    if not result["imap_port"]:
        result["imap_port"] = 993
    if not result["smtp_port"]:
        result["smtp_port"] = 587

    return result


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

    # Access level: "full_access", "read_only", or "" (unknown/non-Gmail)
    access_level: str = ""

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
        known_fields = {f.name for f in fields(cls)}
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
        defaults = fill_provider_defaults(provider, filtered)
        for key in ("imap_server", "imap_port", "smtp_server", "smtp_port"):
            if not filtered.get(key):
                filtered[key] = defaults[key]

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
        safe_provider = _sanitize_for_filesystem(provider)
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
                    "access_level": creds.access_level,
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
    (e.g., "gmail-johndoe").

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
    safe_local = _sanitize_for_filesystem(local_part)
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


def _parse_env_account(n: int) -> dict[str, Any] | None:
    """Parse email account config from EMAIL_ACCOUNT_N_* env vars.

    Returns:
        Dict with email, password, provider, imap_server, imap_port or None if invalid.
    """
    prefix = f"EMAIL_ACCOUNT_{n}_"
    email_addr = os.environ.get(f"{prefix}EMAIL")
    if not email_addr:
        return None

    password = os.environ.get(f"{prefix}PASSWORD", "")
    if not password:
        logger.warning("EMAIL_ACCOUNT_%d: no PASSWORD set, skipping %s", n, email_addr)
        return None

    provider = detect_provider(email_addr)
    custom_imap_server = os.environ.get(f"{prefix}IMAP_SERVER")
    custom_imap_port = os.environ.get(f"{prefix}IMAP_PORT")

    defaults = fill_provider_defaults(provider, {
        "imap_server": custom_imap_server or "",
        "imap_port": int(custom_imap_port) if custom_imap_port else 0,
    })

    if not defaults["imap_server"]:
        logger.warning(
            "EMAIL_ACCOUNT_%d: unknown provider for %s and no IMAP_SERVER set, skipping",
            n, email_addr,
        )
        return None

    return {
        "email": email_addr,
        "password": password,
        "provider": provider,
        "imap_server": defaults["imap_server"],
        "imap_port": defaults["imap_port"],
        "n": n,
    }


def _account_already_exists(cred_store: CredentialStore, cred_key: str, email_addr: str) -> bool:
    """Check if an email account already exists in the credential store."""
    if cred_store.has_credentials(cred_key):
        logger.info("Email account %s already configured (key: %s), skipping", email_addr, cred_key)
        return True

    for key in cred_store.get_connected_providers():
        existing_creds = cred_store.load_credentials(key)
        if existing_creds and existing_creds.email_address == email_addr:
            logger.info("Email account %s already configured under key '%s', skipping", email_addr, key)
            return True

    return False


def seed_credentials_from_env() -> int:
    """Seed email credentials from EMAIL_ACCOUNT_N_* environment variables.

    All auto-seeded accounts are assigned to the admin user only.
    Env-based accounts act as defaults that are always available for admin.
    If admin disconnects an account from UI, the env-based account is restored on restart.
    If admin modifies account settings via UI, those changes are preserved (not overwritten).

    Returns:
        Number of newly seeded accounts.
    """
    seeded = 0
    username = "admin"
    cred_store = get_credential_store(username)

    for n in range(1, 100):
        account = _parse_env_account(n)
        if account is None:
            if not os.environ.get(f"EMAIL_ACCOUNT_{n}_EMAIL"):
                break
            continue

        existing_keys = cred_store.get_connected_providers()
        cred_key = _make_credential_key(account["provider"], account["email"], existing_keys)

        # Check if this email account already exists (under this key or any other key)
        if _account_already_exists(cred_store, cred_key, account["email"]):
            # Account already exists - skip to preserve UI changes
            # If admin disconnected the account, the file would be deleted and this would return False
            continue

        logger.info("Testing IMAP connection for %s (%s:%d)...",
                     account["email"], account["imap_server"], account["imap_port"])
        if not _test_imap_connection(account["imap_server"], account["imap_port"],
                                      account["email"], account["password"]):
            logger.error("EMAIL_ACCOUNT_%d: IMAP connection test failed for %s, skipping",
                         account["n"], account["email"])
            continue

        server_config = fill_provider_defaults(account["provider"])
        credentials = EmailCredentials(
            provider=cred_key,
            auth_type="app_password",
            email_address=account["email"],
            app_password=account["password"],
            imap_server=account["imap_server"],
            imap_port=account["imap_port"],
            smtp_server=server_config.get("smtp_server", ""),
            smtp_port=server_config.get("smtp_port", 587),
        )
        cred_store.save_credentials(credentials)
        seeded += 1
        logger.info("Auto-seeded email account: %s (key: %s, user: %s)",
                     account["email"], cred_key, username)

    return seeded
