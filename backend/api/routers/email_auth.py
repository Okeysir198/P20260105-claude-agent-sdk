"""OAuth and IMAP authentication router for email providers.

Handles OAuth flow for Gmail and generic IMAP app-password connections
for Yahoo, Outlook, iCloud, Zoho, and custom IMAP providers.
"""
import imaplib
import logging
import secrets
import time
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from starlette.responses import RedirectResponse

from api.dependencies.auth import get_current_user
from agent.tools.email.credential_store import (
    get_credential_store,
    OAuthCredentials,
    EmailCredentials,
    detect_provider,
    PROVIDER_CONFIG,
    get_provider_display_name,
)
from core.settings import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

router = APIRouter()

# Environment variables for OAuth
GMAIL_CLIENT_ID = settings.email.gmail_client_id
GMAIL_CLIENT_SECRET = settings.email.gmail_client_secret
GMAIL_REDIRECT_URI = settings.email.gmail_redirect_uri

# In-memory OAuth state store: {state_token: {"username": str, "expires_at": float}}
_oauth_state_store: dict[str, dict[str, Any]] = {}
_OAUTH_STATE_TTL = 600  # 10 minutes


def _create_oauth_state(username: str) -> str:
    """Create a signed OAuth state token that embeds the username."""
    state_token = secrets.token_urlsafe(32)
    _oauth_state_store[state_token] = {
        "username": username,
        "expires_at": time.time() + _OAUTH_STATE_TTL,
    }
    # Cleanup expired states
    now = time.time()
    expired = [k for k, v in _oauth_state_store.items() if v["expires_at"] < now]
    for k in expired:
        del _oauth_state_store[k]
    return state_token


def _validate_oauth_state(state_token: str) -> str | None:
    """Validate OAuth state and return username. Returns None if invalid/expired."""
    entry = _oauth_state_store.pop(state_token, None)
    if entry is None:
        return None
    if time.time() > entry["expires_at"]:
        return None
    return entry["username"]


# Request/Response models
class OAuthUrlResponse(BaseModel):
    """Response with OAuth URL."""
    auth_url: str
    provider: str


class EmailConnectionStatus(BaseModel):
    """Email connection status."""
    gmail_connected: bool = False
    yahoo_connected: bool = False
    gmail_email: str | None = None
    yahoo_email: str | None = None
    accounts: list[dict[str, Any]] = Field(default_factory=list)


class DisconnectEmailRequest(BaseModel):
    """Request to disconnect email account."""
    provider: str = Field(..., description="Email provider (gmail or yahoo)")


class ImapConnectRequest(BaseModel):
    """Request to connect an email account via IMAP with app password."""
    email: str = Field(..., description="Email address")
    app_password: str = Field(..., min_length=1, description="App-specific password for IMAP access")
    provider: str | None = Field(None, description="Provider ID (auto-detected from email if not specified)")
    imap_server: str | None = Field(None, description="Custom IMAP server hostname (auto-filled for known providers)")
    imap_port: int | None = Field(None, description="Custom IMAP port (default: 993)")


class ImapDisconnectRequest(BaseModel):
    """Request to disconnect an IMAP email account."""
    provider: str = Field(..., description="Provider ID to disconnect")


def get_frontend_url() -> str:
    """Get the frontend URL for redirect after OAuth."""
    return settings.email.frontend_url


def _test_imap_connection(imap_server: str, imap_port: int, email: str, app_password: str) -> None:
    """Test IMAP connection by logging in and out.

    Raises:
        HTTPException: If the connection or login fails
    """
    try:
        client = imaplib.IMAP4_SSL(imap_server, imap_port)
        client.login(email, app_password)
        client.logout()
    except imaplib.IMAP4.error as e:
        logger.warning(f"IMAP login failed for {email} on {imap_server}: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"IMAP login failed. Please check your email and app password. Error: {e}",
        )
    except Exception as e:
        logger.error(f"IMAP connection error for {email} on {imap_server}: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Could not connect to IMAP server {imap_server}:{imap_port}. Error: {e}",
        )


# ─── Generic IMAP Connect/Disconnect ─────────────────────────────────────────

@router.post("/imap/connect")
async def imap_connect(
    request: ImapConnectRequest,
    current_user: dict = Depends(get_current_user),
):
    """Connect an email account via IMAP with app password.

    Auto-detects provider from email domain if not specified.
    Tests the IMAP connection before saving credentials.
    For Gmail, OAuth is recommended but IMAP with app password is allowed as fallback.
    """
    username = current_user.get("username", "admin")
    email = request.email
    app_password = request.app_password

    # Determine provider
    provider = request.provider or detect_provider(email)

    if provider == "gmail":
        logger.info(
            f"Gmail IMAP connection requested for {email} by user {username}. "
            "Note: Gmail OAuth is recommended for better security."
        )

    # Resolve IMAP server config
    if request.imap_server:
        imap_server = request.imap_server
    elif provider in PROVIDER_CONFIG:
        imap_server = PROVIDER_CONFIG[provider]["imap_server"]
    else:
        raise HTTPException(
            status_code=400,
            detail="Unknown provider. Please specify imap_server and imap_port for custom providers.",
        )

    imap_port = request.imap_port or (
        PROVIDER_CONFIG[provider]["imap_port"] if provider in PROVIDER_CONFIG else 993
    )

    # Test the connection before saving
    _test_imap_connection(imap_server, imap_port, email, app_password)

    # Build and save credentials
    cred_store = get_credential_store(username)

    # Auto-fill SMTP config from provider if available
    smtp_server = ""
    smtp_port = 587
    if provider in PROVIDER_CONFIG:
        smtp_server = PROVIDER_CONFIG[provider].get("smtp_server", "")
        smtp_port = PROVIDER_CONFIG[provider].get("smtp_port", 587)

    credentials = EmailCredentials(
        provider=provider,
        auth_type="app_password",
        email_address=email,
        app_password=app_password,
        imap_server=imap_server,
        imap_port=imap_port,
        smtp_server=smtp_server,
        smtp_port=smtp_port,
    )
    cred_store.save_credentials(credentials)

    provider_name = get_provider_display_name(provider)
    logger.info(f"Successfully connected {provider_name} IMAP for user {username} ({email})")

    return {
        "message": f"{provider_name} connected successfully via IMAP",
        "provider": provider,
        "provider_name": provider_name,
    }


@router.post("/imap/disconnect")
async def imap_disconnect(
    request: ImapDisconnectRequest,
    current_user: dict = Depends(get_current_user),
):
    """Disconnect an IMAP email account."""
    username = current_user.get("username", "admin")
    cred_store = get_credential_store(username)

    provider = request.provider
    provider_name = get_provider_display_name(provider)

    success = cred_store.delete_credentials(provider)

    if success:
        logger.info(f"Disconnected {provider_name} for user {username}")
        return {"message": f"{provider_name} disconnected successfully"}
    else:
        raise HTTPException(status_code=404, detail=f"{provider_name} account not connected")


# ─── Accounts ────────────────────────────────────────────────────────────────

@router.get("/accounts")
async def list_accounts(current_user: dict = Depends(get_current_user)):
    """List all connected email accounts for the current user."""
    username = current_user.get("username", "admin")
    cred_store = get_credential_store(username)

    accounts = cred_store.get_all_accounts()
    return {"accounts": accounts}


# ─── Gmail OAuth flow ────────────────────────────────────────────────────────

@router.get("/gmail/auth-url", response_model=OAuthUrlResponse)
async def get_gmail_auth_url(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Get Gmail OAuth authorization URL.

    Redirects user to Google OAuth consent screen.
    """
    if not GMAIL_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Gmail client ID not configured")

    username = current_user.get("username", "")
    if not username:
        raise HTTPException(status_code=401, detail="User not authenticated")

    # Create CSRF-protected state token that embeds the username
    state = _create_oauth_state(username)

    # Google OAuth URL
    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={GMAIL_CLIENT_ID}"
        f"&redirect_uri={quote(GMAIL_REDIRECT_URI, safe='')}"
        "&response_type=code"
        "&scope=https://www.googleapis.com/auth/gmail.readonly"
        f"&state={state}"
        "&access_type=offline"
        "&prompt=consent"
    )

    return OAuthUrlResponse(auth_url=auth_url, provider="gmail")


@router.get("/gmail/callback")
async def gmail_callback(code: str, state: str | None = None):
    """Handle Gmail OAuth callback.

    Exchanges authorization code for access token and stores credentials.
    """
    if not GMAIL_CLIENT_ID or not GMAIL_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Gmail credentials not configured")

    # Validate CSRF state and extract username
    if not state:
        raise HTTPException(status_code=400, detail="Missing OAuth state parameter")

    username = _validate_oauth_state(state)
    if not username:
        logger.warning("Invalid or expired OAuth state received")
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired OAuth state. Please try connecting again.",
        )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Exchange code for token
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": GMAIL_CLIENT_ID,
                    "client_secret": GMAIL_CLIENT_SECRET,
                    "redirect_uri": GMAIL_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
            )
            token_data = token_response.json()

            if "error" in token_data:
                logger.error(f"Gmail token error: {token_data}")
                raise HTTPException(
                    status_code=400,
                    detail=token_data.get("error_description", "Authentication failed"),
                )

            # Verify we got a refresh token (needed for long-term access)
            if not token_data.get("refresh_token"):
                logger.warning(f"No refresh token in Gmail response for user {username}")

            # Get user info
            access_token = token_data["access_token"]
            userinfo_response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            userinfo = userinfo_response.json()
            email_address = userinfo.get("email", "")

            # Calculate expiration
            expires_in = token_data.get("expires_in", 3600)
            expires_at = (datetime.now() + timedelta(seconds=expires_in)).isoformat()

            # Store credentials for the authenticated user
            cred_store = get_credential_store(username)
            credentials = OAuthCredentials(
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token", ""),
                token_type=token_data.get("token_type", "Bearer"),
                expires_at=expires_at,
                email_address=email_address,
                provider="gmail",
            )
            cred_store.save_credentials(credentials)

            logger.info(f"Successfully connected Gmail for user {username} ({email_address})")

            # Redirect to frontend
            frontend_url = get_frontend_url()
            return RedirectResponse(url=f"{frontend_url}/profile?email=gmail&status=connected")

    except httpx.HTTPError as e:
        logger.error(f"Gmail OAuth HTTP error: {e}")
        raise HTTPException(status_code=500, detail="Failed to connect to Gmail")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Gmail OAuth error: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred during Gmail authentication")


@router.post("/gmail/disconnect")
async def disconnect_gmail(
    request: DisconnectEmailRequest,
    current_user: dict = Depends(get_current_user)
):
    """Disconnect Gmail account."""
    username = current_user.get("username", "admin")
    cred_store = get_credential_store(username)

    success = cred_store.delete_credentials("gmail")

    if success:
        logger.info(f"Disconnected Gmail for user {username}")
        return {"message": "Gmail disconnected successfully"}
    else:
        raise HTTPException(status_code=404, detail="Gmail account not connected")


# ─── Yahoo (backward-compatible, delegates to generic IMAP logic) ────────────

@router.get("/yahoo/auth-url", response_model=OAuthUrlResponse)
async def get_yahoo_auth_url(request: Request):
    """Get Yahoo OAuth authorization URL.

    For Yahoo, we use app password approach since OAuth for IMAP is limited.
    This returns a frontend URL for users to enter their credentials.
    """
    frontend_url = get_frontend_url()
    auth_url = f"{frontend_url}/profile?connect=yahoo"

    return OAuthUrlResponse(auth_url=auth_url, provider="yahoo")


class YahooCredentialsRequest(BaseModel):
    """Request to connect Yahoo with app password."""
    email: str = Field(..., description="Yahoo email address")
    app_password: str = Field(..., min_length=1, description="Yahoo app password (generated from Yahoo account settings)")


@router.post("/yahoo/connect")
async def connect_yahoo(
    credentials: YahooCredentialsRequest,
    current_user: dict = Depends(get_current_user)
):
    """Connect Yahoo Mail using app password.

    Yahoo requires app-specific passwords for IMAP access.
    Users can generate these at: https://login.yahoo.com/account/security

    Internally delegates to the generic IMAP connect logic.
    """
    imap_request = ImapConnectRequest(
        email=credentials.email,
        app_password=credentials.app_password,
        provider="yahoo",
    )
    return await imap_connect(imap_request, current_user)


@router.post("/yahoo/disconnect")
async def disconnect_yahoo(
    request: DisconnectEmailRequest,
    current_user: dict = Depends(get_current_user)
):
    """Disconnect Yahoo Mail account.

    Internally delegates to the generic IMAP disconnect logic.
    """
    imap_request = ImapDisconnectRequest(provider="yahoo")
    return await imap_disconnect(imap_request, current_user)


# ─── Status & Providers ─────────────────────────────────────────────────────

@router.get("/status", response_model=EmailConnectionStatus)
async def get_email_status(current_user: dict = Depends(get_current_user)):
    """Get email connection status for current user.

    Returns backward-compatible gmail/yahoo fields plus a full accounts list.
    """
    username = current_user.get("username", "admin")
    cred_store = get_credential_store(username)

    gmail_creds = cred_store.load_credentials("gmail")
    yahoo_creds = cred_store.load_credentials("yahoo")
    accounts = cred_store.get_all_accounts()

    return EmailConnectionStatus(
        gmail_connected=gmail_creds is not None,
        yahoo_connected=yahoo_creds is not None,
        gmail_email=gmail_creds.email_address if gmail_creds else None,
        yahoo_email=yahoo_creds.email_address if yahoo_creds else None,
        accounts=accounts,
    )


@router.get("/providers")
async def list_email_providers():
    """List available email providers with their configuration and auth types."""
    providers = []

    for provider_id, config in PROVIDER_CONFIG.items():
        auth_type = "oauth" if provider_id == "gmail" else "app_password"
        providers.append({
            "id": provider_id,
            "name": config["name"],
            "description": f"Read emails and download attachments from {config['name']}",
            "auth_type": auth_type,
            "imap_server": config["imap_server"],
            "imap_port": config["imap_port"],
        })

    # Add generic custom provider option
    providers.append({
        "id": "custom",
        "name": "Custom IMAP",
        "description": "Connect any IMAP-compatible email provider",
        "auth_type": "app_password",
        "imap_server": None,
        "imap_port": 993,
    })

    return {"providers": providers}
