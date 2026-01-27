"""
JWT Token service for authentication and authorization.
"""
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, Set
import logging

from jose import JWTError, jwt

from api.config import JWT_CONFIG

logger = logging.getLogger(__name__)


class TokenService:
    """
    Service for creating, validating, and revoking JWT tokens.
    """

    def __init__(self):
        self.secret_key = JWT_CONFIG["secret_key"]
        self.algorithm = JWT_CONFIG["algorithm"]
        self.access_token_expire_minutes = JWT_CONFIG["access_token_expire_minutes"]
        self.refresh_token_expire_days = JWT_CONFIG["refresh_token_expire_days"]
        self.issuer = JWT_CONFIG["issuer"]
        self.audience = JWT_CONFIG["audience"]

        # In-memory token blacklist (use Redis in production)
        self._blacklist: Set[str] = set()

    def _generate_jti(self) -> str:
        """Generate a unique JWT ID (jti)."""
        return str(uuid.uuid4())

    def _get_user_id_from_api_key(self, api_key: str) -> str:
        """
        Extract user ID from API key.
        In production, this would validate against a database.
        For now, use a hash of the API key as the user ID.
        """
        # Simple hash-based user ID generation
        # In production, this would look up the user in a database
        import hashlib
        return hashlib.sha256(api_key.encode()).hexdigest()[:32]

    def create_access_token(
        self,
        user_id: str,
        additional_claims: Optional[Dict[str, str]] = None,
    ) -> tuple[str, str, int]:
        """
        Create an access token.

        Args:
            user_id: User identifier
            additional_claims: Optional additional claims to include

        Returns:
            Tuple of (encoded_token, jti, expires_in_seconds)
        """
        jti = self._generate_jti()
        now = datetime.utcnow()
        expire = now + timedelta(minutes=self.access_token_expire_minutes)
        exp_timestamp = int(expire.timestamp())

        payload = {
            "sub": user_id,
            "jti": jti,
            "type": "access",
            "iat": int(now.timestamp()),
            "exp": exp_timestamp,
            "iss": self.issuer,
            "aud": self.audience,
        }

        if additional_claims:
            payload.update(additional_claims)

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        expires_in = exp_timestamp - int(now.timestamp())

        logger.debug(f"Created access token for user {user_id}, jti={jti}")
        return token, jti, expires_in

    def create_refresh_token(
        self,
        user_id: str,
    ) -> str:
        """
        Create a refresh token.

        Args:
            user_id: User identifier

        Returns:
            Encoded refresh token
        """
        jti = self._generate_jti()
        now = datetime.utcnow()
        expire = now + timedelta(days=self.refresh_token_expire_days)

        payload = {
            "sub": user_id,
            "jti": jti,
            "type": "refresh",
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
            "iss": self.issuer,
            "aud": self.audience,
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        logger.debug(f"Created refresh token for user {user_id}, jti={jti}")
        return token

    def create_token_pair(
        self,
        api_key: str,
        additional_claims: Optional[Dict[str, str]] = None,
    ) -> Dict[str, any]:
        """
        Create an access and refresh token pair.

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

    def decode_and_validate_token(
        self,
        token: str,
        token_type: str = "access",
    ) -> Optional[Dict[str, any]]:
        """
        Decode and validate a JWT token.

        Args:
            token: JWT token string
            token_type: Expected token type ("access" or "refresh")

        Returns:
            Decoded token payload if valid, None otherwise

        Raises:
            JWTError: If token is invalid or verification fails
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

            # Check token type
            if payload.get("type") != token_type:
                logger.warning(f"Token type mismatch: expected {token_type}, got {payload.get('type')}")
                return None

            # Check if token is revoked
            jti = payload.get("jti")
            if jti in self._blacklist:
                logger.warning(f"Token {jti} has been revoked")
                return None

            return payload

        except JWTError as e:
            # Log current time for debugging clock issues
            import time
            now = int(time.time())
            logger.warning(f"Token validation failed: {e}")
            logger.warning(f"Current server time (epoch): {now}, UTC: {datetime.utcnow().isoformat()}")
            return None

    def revoke_token(self, jti: str) -> None:
        """
        Revoke a token by adding its JTI to the blacklist.

        Args:
            jti: JWT ID to revoke
        """
        self._blacklist.add(jti)
        logger.info(f"Revoked token {jti}")

    def revoke_user_tokens(self, user_id: str) -> None:
        """
        Revoke all tokens for a user.
        Note: This only works for tokens we can validate.
        In production, use a database to track all user tokens.

        Args:
            user_id: User identifier
        """
        logger.warning(f"Revoking all tokens for user {user_id}")
        # In production, this would query a database for all user tokens
        # For now, we rely on token expiration

    def is_token_revoked(self, jti: str) -> bool:
        """
        Check if a token has been revoked.

        Args:
            jti: JWT ID to check

        Returns:
            True if token is revoked, False otherwise
        """
        return jti in self._blacklist


# Global token service instance
token_service = TokenService() if JWT_CONFIG["secret_key"] else None
