"""Self-contained signed download token creation for media tools.

Derives signing key from API_KEY env var, matching the backend's token chain.
"""
import base64
import hashlib
import hmac as hmac_mod
import json
import os
import secrets
import time
from dataclasses import dataclass

BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "https://localhost:7001")
DEFAULT_EXPIRE_HOURS = 24


@dataclass
class FileDownloadClaim:
    username: str
    cwd_id: str
    relative_path: str
    expires_at: float
    nonce: str


def _signing_key() -> bytes:
    """Derive HMAC signing key from API_KEY env var.

    Matches the chain: API_KEY -> HMAC(salt) -> jwt_secret -> HMAC("file-download-v1") -> key
    """
    api_key = os.environ.get("API_KEY", "")
    salt = "claude-agent-sdk-jwt-v1"
    jwt_secret = hmac_mod.new(salt.encode(), api_key.encode(), hashlib.sha256).hexdigest()
    return hmac_mod.new(b"file-download-v1", jwt_secret.encode(), hashlib.sha256).digest()


def _sign(data: str) -> str:
    return hmac_mod.new(_signing_key(), data.encode(), hashlib.sha256).hexdigest()


def create_download_token(
    username: str,
    cwd_id: str,
    relative_path: str,
    expire_hours: int = DEFAULT_EXPIRE_HOURS,
) -> str:
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


def build_download_url(token: str) -> str:
    return f"{BACKEND_PUBLIC_URL}/api/v1/files/dl/{token}"
