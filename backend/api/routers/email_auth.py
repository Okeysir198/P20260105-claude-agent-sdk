"""OAuth authentication router for email providers.

Handles OAuth flow for Gmail and Yahoo Mail email integration.
"""
import logging
import secrets
import time
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from starlette.responses import RedirectResponse

from api.dependencies.auth import get_current_user
from agent.tools.email.credential_store import get_credential_store, OAuthCredentials
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


class DisconnectEmailRequest(BaseModel):
    """Request to disconnect email account."""
    provider: str = Field(..., description="Email provider (gmail or yahoo)")


def get_frontend_url() -> str:
    """Get the frontend URL for redirect after OAuth."""
    return settings.email.frontend_url


# Gmail OAuth flow
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


# Yahoo OAuth flow
@router.get("/yahoo/auth-url", response_model=OAuthUrlResponse)
async def get_yahoo_auth_url(request: Request):
    """Get Yahoo OAuth authorization URL.

    For Yahoo, we use app password approach since OAuth for IMAP is limited.
    This returns a frontend URL for users to enter their credentials.
    """
    # Yahoo doesn't have a straightforward OAuth flow for IMAP
    # We'll use a simpler approach with app passwords
    frontend_url = get_frontend_url()
    auth_url = f"{frontend_url}/profile?connect=yahoo"

    return OAuthUrlResponse(auth_url=auth_url, provider="yahoo")


class YahooCredentialsRequest(BaseModel):
    """Request to connect Yahoo with app password."""
    email: EmailStr = Field(..., description="Yahoo email address")
    app_password: str = Field(..., min_length=1, description="Yahoo app password (generated from Yahoo account settings)")


@router.post("/yahoo/connect")
async def connect_yahoo(
    credentials: YahooCredentialsRequest,
    current_user: dict = Depends(get_current_user)
):
    """Connect Yahoo Mail using app password.

    Yahoo requires app-specific passwords for IMAP access.
    Users can generate these at: https://login.yahoo.com/account/security
    """
    username = current_user.get("username", "admin")
    cred_store = get_credential_store(username)

    # Store credentials (using refresh_token field for app password)
    oauth_creds = OAuthCredentials(
        access_token="",  # Not used for IMAP
        refresh_token=credentials.app_password,  # Store app password here
        token_type="app_password",
        expires_at=None,
        email_address=credentials.email,
        provider="yahoo"
    )
    cred_store.save_credentials(oauth_creds)

    logger.info(f"Successfully connected Yahoo for user {username} ({credentials.email})")

    return {"message": "Yahoo Mail connected successfully"}


@router.post("/yahoo/disconnect")
async def disconnect_yahoo(
    request: DisconnectEmailRequest,
    current_user: dict = Depends(get_current_user)
):
    """Disconnect Yahoo Mail account."""
    username = current_user.get("username", "admin")
    cred_store = get_credential_store(username)

    success = cred_store.delete_credentials("yahoo")

    if success:
        logger.info(f"Disconnected Yahoo for user {username}")
        return {"message": "Yahoo disconnected successfully"}
    else:
        raise HTTPException(status_code=404, detail="Yahoo account not connected")


# Status endpoints
@router.get("/status", response_model=EmailConnectionStatus)
async def get_email_status(current_user: dict = Depends(get_current_user)):
    """Get email connection status for current user."""
    username = current_user.get("username", "admin")
    cred_store = get_credential_store(username)

    gmail_creds = cred_store.load_credentials("gmail")
    yahoo_creds = cred_store.load_credentials("yahoo")

    return EmailConnectionStatus(
        gmail_connected=gmail_creds is not None,
        yahoo_connected=yahoo_creds is not None,
        gmail_email=gmail_creds.email_address if gmail_creds else None,
        yahoo_email=yahoo_creds.email_address if yahoo_creds else None
    )


@router.get("/providers")
async def list_email_providers():
    """List available email providers."""
    return {
        "providers": [
            {
                "id": "gmail",
                "name": "Gmail",
                "description": "Read emails and download attachments from Gmail",
                "auth_type": "oauth"
            },
            {
                "id": "yahoo",
                "name": "Yahoo Mail",
                "description": "Read emails and download attachments from Yahoo Mail",
                "auth_type": "app_password"
            }
        ]
    }
