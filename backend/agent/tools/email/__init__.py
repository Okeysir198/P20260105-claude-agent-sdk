"""Email tools package for Gmail and Yahoo Mail integration.

Provides OAuth-based email reading and attachment downloading for Gmail and Yahoo Mail.
"""
from agent.tools.email.credential_store import (
    get_credential_store,
    CredentialStore,
    OAuthCredentials
)
from agent.tools.email.attachment_store import (
    get_attachment_store,
    AttachmentStore
)

__all__ = [
    "get_credential_store",
    "CredentialStore",
    "OAuthCredentials",
    "get_attachment_store",
    "AttachmentStore",
]
