"""Signed download token creation and validation for platform file delivery.

Tokens are HMAC-signed, URL-safe, and time-limited. They encode the username,
session working directory ID, and relative file path so the download endpoint
can serve files without requiring JWT authentication.
"""
import base64
import hashlib
import hmac as hmac_mod
import json
import os
import secrets
import time
from dataclasses import dataclass

from core.settings import JWT_CONFIG

BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "https://localhost:7001")
DEFAULT_EXPIRE_HOURS = 24


@dataclass
class FileDownloadClaim:
    """Decoded and validated download token payload."""
    username: str
    cwd_id: str
    relative_path: str
    expires_at: float
    nonce: str


def _signing_key() -> bytes:
    """Derive HMAC signing key from the JWT secret."""
    secret = JWT_CONFIG.get("secret_key", "")
    return hmac_mod.new(b"file-download-v1", secret.encode(), hashlib.sha256).digest()


def _sign(data: str) -> str:
    """Compute HMAC-SHA256 hex signature for the given data."""
    return hmac_mod.new(_signing_key(), data.encode(), hashlib.sha256).hexdigest()


def create_download_token(
    username: str,
    cwd_id: str,
    relative_path: str,
    expire_hours: int = DEFAULT_EXPIRE_HOURS,
) -> str:
    """Create a signed, URL-safe download token."""
    payload = {
        "u": username,
        "c": cwd_id,
        "p": relative_path,
        "x": int(time.time()) + expire_hours * 3600,
        "n": secrets.token_hex(3),
    }
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode()
    b64 = base64.urlsafe_b64encode(payload_bytes).rstrip(b"=").decode()
    return f"{b64}.{_sign(b64)}"


def validate_download_token(token: str) -> FileDownloadClaim | None:
    """Validate a download token and return its claim, or None if invalid."""
    parts = token.rsplit(".", 1)
    if len(parts) != 2:
        return None

    b64, sig = parts
    if not hmac_mod.compare_digest(sig, _sign(b64)):
        return None

    try:
        # Restore base64 padding
        padded = b64 + "=" * (-len(b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))
    except Exception:
        return None

    if time.time() > payload.get("x", 0):
        return None

    return FileDownloadClaim(
        username=payload["u"],
        cwd_id=payload["c"],
        relative_path=payload["p"],
        expires_at=payload["x"],
        nonce=payload["n"],
    )


def build_download_url(token: str) -> str:
    """Build a full download URL for the given token."""
    return f"{BACKEND_PUBLIC_URL}/api/v1/files/dl/{token}"
