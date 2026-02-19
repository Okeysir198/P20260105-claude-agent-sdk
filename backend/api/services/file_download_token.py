import base64
import hashlib
import hmac as hmac_mod
import json
import os
import secrets
import time
from dataclasses import dataclass

from core.settings import JWT_CONFIG

# Backend public URL for generating download links
BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "https://claude-agent-sdk-api.leanwise.ai")

# Token expiry default (hours)
DEFAULT_EXPIRE_HOURS = 24


@dataclass
class FileDownloadClaim:
    username: str
    cwd_id: str
    relative_path: str
    expires_at: float
    nonce: str


def _signing_key() -> bytes:
    secret = JWT_CONFIG.get("secret_key", "")
    return hmac_mod.new(b"file-download-v1", secret.encode(), hashlib.sha256).digest()


def create_download_token(username: str, cwd_id: str, relative_path: str, expire_hours: int = DEFAULT_EXPIRE_HOURS) -> str:
    payload = {
        "u": username,
        "c": cwd_id,
        "p": relative_path,
        "x": int(time.time()) + expire_hours * 3600,
        "n": secrets.token_hex(3),  # 6-char nonce
    }
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode()
    b64 = base64.urlsafe_b64encode(payload_bytes).rstrip(b"=").decode()
    sig = hmac_mod.new(_signing_key(), b64.encode(), hashlib.sha256).hexdigest()
    return f"{b64}.{sig}"


def validate_download_token(token: str) -> FileDownloadClaim | None:
    # Split into payload and signature
    parts = token.rsplit(".", 1)
    if len(parts) != 2:
        return None
    b64, sig = parts
    # Verify signature
    expected = hmac_mod.new(_signing_key(), b64.encode(), hashlib.sha256).hexdigest()
    if not hmac_mod.compare_digest(sig, expected):
        return None
    # Decode payload
    try:
        padding = 4 - len(b64) % 4
        if padding != 4:
            b64_padded = b64 + "=" * padding
        else:
            b64_padded = b64
        payload = json.loads(base64.urlsafe_b64decode(b64_padded))
    except Exception:
        return None
    # Check expiry
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
    return f"{BACKEND_PUBLIC_URL}/api/v1/files/dl/{token}"
