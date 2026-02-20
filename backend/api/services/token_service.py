"""JWT Token service for authentication and authorization."""
import hashlib
import logging
import time
import uuid
from datetime import timedelta
from typing import Any

from jose import JWTError, jwt

from core.settings import JWT_CONFIG

logger = logging.getLogger(__name__)


class TokenService:
    """Service for creating, validating, and revoking JWT tokens."""

    def __init__(self):
        self.secret_key = JWT_CONFIG["secret_key"]
        self.algorithm = JWT_CONFIG["algorithm"]
        self.access_token_expire_minutes = JWT_CONFIG["access_token_expire_minutes"]
        self.refresh_token_expire_days = JWT_CONFIG["refresh_token_expire_days"]
        self.issuer = JWT_CONFIG["issuer"]
        self.audience = JWT_CONFIG["audience"]

        # In-memory token blacklist (use Redis in production)
        self._blacklist: set[str] = set()

    def _generate_jti(self) -> str:
        """Generate a unique JWT ID (jti)."""
        return str(uuid.uuid4())

    def _get_user_id_from_api_key(self, api_key: str) -> str:
        """Derive a user ID from an API key using SHA-256."""
        return hashlib.sha256(api_key.encode()).hexdigest()[:32]

    def _build_token(
        self,
        user_id: str,
        token_type: str,
        expire_seconds: int,
        extra_claims: dict[str, Any] | None = None,
    ) -> tuple[str, str, int]:
        """Build and sign a JWT token with standard claims.

        Returns:
            Tuple of (encoded_token, jti, expires_in_seconds).
        """
        jti = self._generate_jti()
        now = int(time.time())

        payload = {
            "sub": user_id,
            "jti": jti,
            "type": token_type,
            "iat": now,
            "exp": now + expire_seconds,
            "iss": self.issuer,
            "aud": self.audience,
        }
        if extra_claims:
            payload.update(extra_claims)

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        logger.debug(f"Created {token_type} token for user {user_id}, jti={jti}")
        return token, jti, expire_seconds

    def create_access_token(
        self,
        user_id: str,
        additional_claims: dict[str, str] | None = None,
    ) -> tuple[str, str, int]:
        """Create an access token.

        Returns:
            Tuple of (encoded_token, jti, expires_in_seconds).
        """
        expires_in = int(timedelta(minutes=self.access_token_expire_minutes).total_seconds())
        return self._build_token(user_id, "access", expires_in, additional_claims)

    def create_refresh_token(self, user_id: str) -> str:
        """Create a refresh token.

        Returns:
            Encoded refresh token.
        """
        expires_in = int(timedelta(days=self.refresh_token_expire_days).total_seconds())
        token, _, _ = self._build_token(user_id, "refresh", expires_in)
        return token

    def create_token_pair(
        self,
        api_key: str,
        additional_claims: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Create an access and refresh token pair from an API key."""
        user_id = self._get_user_id_from_api_key(api_key)

        access_token, jti, expires_in = self.create_access_token(
            user_id, additional_claims
        )
        refresh_token = self.create_refresh_token(user_id)

        logger.info(f"Created token pair for user {user_id}")

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": expires_in,
            "user_id": user_id,
        }

    def _decode_jwt(
        self,
        token: str,
        check_type: str | None = None,
        log_type_mismatch: bool = True,
    ) -> dict[str, Any] | None:
        """Decode and validate a JWT, checking signature, expiry, and blacklist."""
        try:
            # Add leeway to handle clock skew between systems
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                audience=self.audience,
                issuer=self.issuer,
                options={"leeway": 60},  # Allow 60 seconds clock skew
            )

            # Check token type if specified
            if check_type and payload.get("type") != check_type:
                if log_type_mismatch:
                    logger.warning(f"Token type mismatch: expected {check_type}, got {payload.get('type')}")
                return None

            # Check if token is revoked
            jti = payload.get("jti")
            if jti in self._blacklist:
                logger.warning(f"Token {jti} has been revoked")
                return None

            return payload

        except JWTError as e:
            logger.warning(f"Token validation failed: {e}")
            return None

    def decode_and_validate_token(
        self,
        token: str,
        token_type: str = "access",
        log_type_mismatch: bool = True,
    ) -> dict[str, Any] | None:
        """Decode and validate a JWT token, enforcing the expected type."""
        return self._decode_jwt(token, check_type=token_type, log_type_mismatch=log_type_mismatch)

    def revoke_token(self, jti: str) -> None:
        """Revoke a token by adding its JTI to the blacklist."""
        self._blacklist.add(jti)
        logger.info(f"Revoked token {jti}")

    def revoke_user_tokens(self, user_id: str) -> None:
        """Revoke all tokens for a user. Currently relies on token expiration."""
        logger.warning(f"Revoking all tokens for user {user_id}")
        # In production, this would query a database for all user tokens
        # For now, we rely on token expiration

    def is_token_revoked(self, jti: str) -> bool:
        """Check if a token has been revoked."""
        return jti in self._blacklist

    def create_user_identity_token(
        self,
        user_id: str,
        username: str,
        role: str,
        full_name: str | None = None,
    ) -> tuple[str, str, int]:
        """Create a user identity token for WebSocket and API user identification.

        Contains user information for per-request user identification,
        separate from API key authentication.

        Returns:
            Tuple of (encoded_token, jti, expires_in_seconds).
        """
        expires_in = int(timedelta(minutes=self.access_token_expire_minutes).total_seconds())
        return self._build_token(
            user_id,
            "user_identity",
            expires_in,
            extra_claims={
                "user_id": user_id,
                "username": username,
                "role": role,
                "full_name": full_name or "",
            },
        )

    def decode_user_identity_token(self, token: str) -> dict[str, Any] | None:
        """Decode and validate a user identity token."""
        return self.decode_and_validate_token(token, token_type="user_identity")

    def decode_token_any_type(self, token: str) -> dict[str, Any] | None:
        """Decode and validate a JWT token without checking type."""
        return self._decode_jwt(token, check_type=None)


# Global token service instance
token_service = TokenService() if JWT_CONFIG["secret_key"] else None
