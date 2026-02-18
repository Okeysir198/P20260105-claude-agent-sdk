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
        """Extract user ID from API key.

        In production, this would validate against a database.
        For now, use a hash of the API key as the user ID.
        """
        return hashlib.sha256(api_key.encode()).hexdigest()[:32]

    def create_access_token(
        self,
        user_id: str,
        additional_claims: dict[str, str] | None = None,
    ) -> tuple[str, str, int]:
        """Create an access token.

        Args:
            user_id: User identifier
            additional_claims: Optional additional claims to include

        Returns:
            Tuple of (encoded_token, jti, expires_in_seconds)
        """
        jti = self._generate_jti()
        now = int(time.time())
        expires_in = int(timedelta(minutes=self.access_token_expire_minutes).total_seconds())
        exp_timestamp = now + expires_in

        payload = {
            "sub": user_id,
            "jti": jti,
            "type": "access",
            "iat": now,
            "exp": exp_timestamp,
            "iss": self.issuer,
            "aud": self.audience,
        }

        if additional_claims:
            payload.update(additional_claims)

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

        logger.debug(f"Created access token for user {user_id}, jti={jti}")
        return token, jti, expires_in

    def create_refresh_token(self, user_id: str) -> str:
        """Create a refresh token.

        Args:
            user_id: User identifier

        Returns:
            Encoded refresh token
        """
        jti = self._generate_jti()
        now = int(time.time())
        exp_timestamp = now + int(timedelta(days=self.refresh_token_expire_days).total_seconds())

        payload = {
            "sub": user_id,
            "jti": jti,
            "type": "refresh",
            "iat": now,
            "exp": exp_timestamp,
            "iss": self.issuer,
            "aud": self.audience,
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        logger.debug(f"Created refresh token for user {user_id}, jti={jti}")
        return token

    def create_token_pair(
        self,
        api_key: str,
        additional_claims: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Create an access and refresh token pair.

        Args:
            api_key: API key for authentication
            additional_claims: Optional additional claims for access token

        Returns:
            Dictionary with access_token, refresh_token, expires_in, user_id
        """
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
        """Core JWT decoding with signature, expiry, and blacklist validation.

        Args:
            token: JWT token string
            check_type: Expected token type to validate, or None to skip type check
            log_type_mismatch: Whether to log warning on type mismatch (default True)

        Returns:
            Decoded token payload if valid, None otherwise
        """
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
        """Decode and validate a JWT token.

        Args:
            token: JWT token string
            token_type: Expected token type ("access" or "refresh")
            log_type_mismatch: Whether to log warning on type mismatch (default True)

        Returns:
            Decoded token payload if valid, None otherwise
        """
        return self._decode_jwt(token, check_type=token_type, log_type_mismatch=log_type_mismatch)

    def revoke_token(self, jti: str) -> None:
        """Revoke a token by adding its JTI to the blacklist.

        Args:
            jti: JWT ID to revoke
        """
        self._blacklist.add(jti)
        logger.info(f"Revoked token {jti}")

    def revoke_user_tokens(self, user_id: str) -> None:
        """Revoke all tokens for a user.

        Note: This only works for tokens we can validate.
        In production, use a database to track all user tokens.

        Args:
            user_id: User identifier
        """
        logger.warning(f"Revoking all tokens for user {user_id}")
        # In production, this would query a database for all user tokens
        # For now, we rely on token expiration

    def is_token_revoked(self, jti: str) -> bool:
        """Check if a token has been revoked.

        Args:
            jti: JWT ID to check

        Returns:
            True if token is revoked, False otherwise
        """
        return jti in self._blacklist

    def create_user_identity_token(
        self,
        user_id: str,
        username: str,
        role: str,
        full_name: str | None = None,
    ) -> tuple[str, str, int]:
        """Create a user identity token for WebSocket and API user identification.

        This token contains user information and is separate from the API key auth.
        It's used to identify which user is making requests.

        Args:
            user_id: User's unique ID
            username: User's username
            role: User's role (admin/user)
            full_name: User's full name (optional)

        Returns:
            Tuple of (encoded_token, jti, expires_in_seconds)
        """
        jti = self._generate_jti()
        now = int(time.time())
        expires_in = int(timedelta(minutes=self.access_token_expire_minutes).total_seconds())
        exp_timestamp = now + expires_in

        payload = {
            "sub": user_id,
            "jti": jti,
            "type": "user_identity",
            "iat": now,
            "exp": exp_timestamp,
            "iss": self.issuer,
            "aud": self.audience,
            # User-specific claims
            "user_id": user_id,
            "username": username,
            "role": role,
            "full_name": full_name or "",
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

        logger.debug(f"Created user identity token for {username}, jti={jti}")
        return token, jti, expires_in

    def decode_user_identity_token(self, token: str) -> dict[str, Any] | None:
        """Decode and validate a user identity token.

        Args:
            token: JWT token string

        Returns:
            Decoded token payload with user info if valid, None otherwise
        """
        return self.decode_and_validate_token(token, token_type="user_identity")

    def decode_token_any_type(self, token: str) -> dict[str, Any] | None:
        """Decode and validate a JWT token without checking type.

        Only verifies signature, expiry, issuer, audience, and blacklist.
        Use this for user authentication where token type doesn't matter.

        Args:
            token: JWT token string

        Returns:
            Decoded token payload if valid, None otherwise
        """
        return self._decode_jwt(token, check_type=None)


# Global token service instance
token_service = TokenService() if JWT_CONFIG["secret_key"] else None
