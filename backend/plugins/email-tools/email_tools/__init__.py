"""Self-contained email tools plugin (Gmail OAuth + IMAP)."""
from email_tools.credential_store import (
    get_credential_store,
    CredentialStore,
    EmailCredentials,
    OAuthCredentials,
    detect_provider,
    get_provider_display_name,
    PROVIDER_CONFIG,
    DOMAIN_TO_PROVIDER,
    seed_credentials_from_env,
    fill_provider_defaults,
    _make_credential_key,
    _test_imap_connection,
    _sanitize_for_filesystem,
)
from email_tools.attachment_store import (
    get_attachment_store,
    AttachmentStore,
)

__all__ = [
    "get_credential_store",
    "CredentialStore",
    "EmailCredentials",
    "OAuthCredentials",
    "detect_provider",
    "get_provider_display_name",
    "PROVIDER_CONFIG",
    "DOMAIN_TO_PROVIDER",
    "seed_credentials_from_env",
    "fill_provider_defaults",
    "_make_credential_key",
    "_test_imap_connection",
    "_sanitize_for_filesystem",
    "get_attachment_store",
    "AttachmentStore",
]
