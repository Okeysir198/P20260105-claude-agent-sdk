"""Email tools package for Gmail and IMAP email integration.

Provides OAuth-based email reading for Gmail and app-password IMAP access
for Yahoo, Outlook, iCloud, Zoho, and custom IMAP providers.
"""
from agent.tools.email.credential_store import (
    get_credential_store,
    CredentialStore,
    EmailCredentials,
    OAuthCredentials,
    detect_provider,
    get_provider_display_name,
    PROVIDER_CONFIG,
    DOMAIN_TO_PROVIDER,
)
from agent.tools.email.attachment_store import (
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
    "get_attachment_store",
    "AttachmentStore",
]
