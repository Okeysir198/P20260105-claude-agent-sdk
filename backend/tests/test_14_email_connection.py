"""Real email connection tests — no mocks.

Verifies the agent can connect to configured email accounts and read emails.
Requires EMAIL_ACCOUNT_N_* env vars and/or Gmail OAuth credentials in admin data dir.

Run:
    pytest tests/test_14_email_connection.py -v
"""
import pytest

from agent.tools.email.credential_store import get_credential_store
from agent.tools.email.gmail_tools import list_gmail_impl, read_gmail_impl
from agent.tools.email.imap_client import (
    list_imap_impl,
    read_imap_impl,
    search_imap_impl,
    list_imap_folders_impl,
)

USERNAME = "admin"


@pytest.fixture(scope="module")
def cred_store():
    return get_credential_store(USERNAME)


@pytest.fixture(scope="module")
def connected_providers(cred_store):
    providers = cred_store.get_connected_providers()
    if not providers:
        pytest.skip("No email accounts configured for admin user")
    return providers


def _has_provider(connected_providers, key):
    return key in connected_providers


def _extract_text(result: dict) -> str:
    """Extract text from MCP tool result."""
    return result["content"][0]["text"]


def _is_error(result: dict) -> bool:
    text = _extract_text(result)
    return text.startswith("Failed") or "not connected" in text


# ─── Credential store: real accounts ─────────────────────────────────────────


class TestCredentialStoreReal:
    """Verify credential store loads real accounts."""

    def test_has_connected_providers(self, connected_providers):
        assert len(connected_providers) >= 1

    def test_credentials_have_email_address(self, cred_store, connected_providers):
        for provider in connected_providers:
            creds = cred_store.load_credentials(provider)
            assert creds is not None, f"Failed to load credentials for {provider}"
            assert creds.email_address, f"No email_address for {provider}"

    def test_accounts_summary(self, cred_store, connected_providers):
        accounts = cred_store.get_all_accounts()
        assert len(accounts) == len(connected_providers)
        for acc in accounts:
            assert acc["email"]
            assert acc["auth_type"] in ("oauth", "app_password")


# ─── Gmail OAuth: list + read ────────────────────────────────────────────────


class TestGmailConnection:
    """Test real Gmail OAuth connection — list and read emails."""

    @pytest.fixture(autouse=True)
    def require_gmail(self, connected_providers):
        if not _has_provider(connected_providers, "gmail"):
            pytest.skip("Gmail OAuth not configured")

    def test_list_gmail(self):
        result = list_gmail_impl(USERNAME, max_results=3)
        assert not _is_error(result), _extract_text(result)
        text = _extract_text(result)
        assert "Found" in text or "No emails" in text

    def test_list_gmail_unread(self):
        result = list_gmail_impl(USERNAME, max_results=3, label="UNREAD")
        assert not _is_error(result), _extract_text(result)

    def test_read_gmail(self):
        """List then read the first email."""
        listing = list_gmail_impl(USERNAME, max_results=1)
        text = _extract_text(listing)
        if "No emails" in text:
            pytest.skip("Gmail inbox is empty")

        # Extract message ID from listing
        assert "**ID:**" in text
        msg_id = text.split("**ID:** ")[1].split("\n")[0].strip()

        result = read_gmail_impl(USERNAME, msg_id)
        assert not _is_error(result), _extract_text(result)
        body = _extract_text(result)
        assert "**Subject:**" in body
        assert "**From:**" in body


# ─── IMAP (app password): list + read + search + folders ─────────────────────


class TestImapConnection:
    """Test real IMAP connections — any app-password provider."""

    @pytest.fixture(scope="class")
    def imap_provider(self, cred_store, connected_providers):
        """Find first IMAP (app_password) provider."""
        for p in connected_providers:
            creds = cred_store.load_credentials(p)
            if creds and creds.auth_type == "app_password":
                return p
        pytest.skip("No IMAP app-password account configured")

    def test_list_folders(self, imap_provider):
        result = list_imap_folders_impl(USERNAME, imap_provider)
        assert not _is_error(result), _extract_text(result)
        text = _extract_text(result)
        assert "folder" in text.lower()

    def test_list_emails(self, imap_provider):
        result = list_imap_impl(USERNAME, imap_provider, max_results=3)
        assert not _is_error(result), _extract_text(result)
        text = _extract_text(result)
        assert "Found" in text or "No emails" in text

    def test_read_email(self, imap_provider):
        """List then read the first email."""
        listing = list_imap_impl(USERNAME, imap_provider, max_results=1)
        text = _extract_text(listing)
        if "No emails" in text:
            pytest.skip("IMAP inbox is empty")

        assert "**ID:**" in text
        msg_id = text.split("**ID:** ")[1].split("\n")[0].strip()

        result = read_imap_impl(USERNAME, imap_provider, msg_id)
        assert not _is_error(result), _extract_text(result)
        body = _extract_text(result)
        assert "**Subject:**" in body
        assert "**From:**" in body

    def test_search_emails(self, imap_provider):
        result = search_imap_impl(USERNAME, imap_provider, query="from:@", max_results=3)
        assert not _is_error(result), _extract_text(result)


# ─── API endpoints: real status ──────────────────────────────────────────────


class TestEmailApiReal:
    """Test email API endpoints with real auth."""

    def test_status_shows_connected(self, client, auth_headers, user_token):
        if not user_token:
            pytest.skip("User token not available")
        headers = {**auth_headers, "X-User-Token": user_token}
        response = client.get("/api/v1/email/status", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["gmail_connected"] or data["yahoo_connected"]

    def test_accounts_list(self, client, auth_headers, user_token):
        if not user_token:
            pytest.skip("User token not available")
        headers = {**auth_headers, "X-User-Token": user_token}
        response = client.get("/api/v1/email/accounts", headers=headers)
        assert response.status_code == 200
        accounts = response.json()["accounts"]
        assert len(accounts) >= 1
        for acc in accounts:
            assert acc["email"]
            assert acc["provider"]
