"""
API test: JWT authentication (TokenService, ws-token, ws-token-refresh).

Run: pytest tests/test_05_auth.py -v
"""
import time
from datetime import timedelta

import pytest
from jose import jwt

from api.services.token_service import TokenService
from core.settings import JWT_CONFIG


pytestmark = pytest.mark.skipif(
    not JWT_CONFIG.get("secret_key"),
    reason="API_KEY not configured (required for JWT)"
)


class TestTokenService:
    """Test cases for TokenService."""

    def test_create_token_pair(self):
        """Test token pair creation."""
        service = TokenService()
        api_key = "test_api_key"

        tokens = service.create_token_pair(api_key)

        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert "token_type" in tokens
        assert "expires_in" in tokens
        assert "user_id" in tokens
        assert tokens["token_type"] == "bearer"
        assert tokens["expires_in"] > 0

    def test_validate_valid_tokens(self):
        """Test validation of valid access and refresh tokens."""
        service = TokenService()
        user_id = "test_user_123"

        access_token, jti, _ = service.create_access_token(user_id)
        refresh_token = service.create_refresh_token(user_id)

        access_payload = service.decode_and_validate_token(access_token, token_type="access")
        refresh_payload = service.decode_and_validate_token(refresh_token, token_type="refresh")

        assert access_payload is not None
        assert access_payload["sub"] == user_id
        assert access_payload["type"] == "access"

        assert refresh_payload is not None
        assert refresh_payload["sub"] == user_id
        assert refresh_payload["type"] == "refresh"

    def test_validate_invalid_token(self):
        """Test validation of an invalid token."""
        service = TokenService()
        invalid_token = "invalid.token.string"

        payload = service.decode_and_validate_token(invalid_token, token_type="access")
        assert payload is None

    def test_token_type_validation(self):
        """Test validation fails when token type doesn't match."""
        service = TokenService()
        user_id = "test_user_123"

        access_token, _, _ = service.create_access_token(user_id)

        # Try to validate access token as refresh token
        payload = service.decode_and_validate_token(access_token, token_type="refresh")
        assert payload is None

    def test_token_revocation(self):
        """Test token revocation."""
        service = TokenService()
        user_id = "test_user_123"

        token, jti, _ = service.create_access_token(user_id)

        # Token should be valid initially
        payload = service.decode_and_validate_token(token, token_type="access")
        assert payload is not None

        # Revoke the token
        service.revoke_token(jti)

        # Token should now be invalid
        payload = service.decode_and_validate_token(token, token_type="access")
        assert payload is None

    def test_token_expiration(self):
        """Test that expired tokens are rejected."""
        service = TokenService()

        # Create an expired token (expired 120 seconds ago, past 60s leeway)
        now = int(time.time())
        expire = now - 120

        payload = {
            "sub": "test_user",
            "jti": "expired_jti",
            "type": "access",
            "iat": now - 180,
            "exp": expire,
            "iss": service.issuer,
            "aud": service.audience,
        }

        expired_token = jwt.encode(payload, service.secret_key, algorithm=service.algorithm)

        result = service.decode_and_validate_token(expired_token, token_type="access")
        assert result is None


class TestWsTokenEndpoint:
    """Test cases for /auth/ws-token endpoint."""

    def test_ws_token_with_valid_api_key(self, client, api_key):
        """Test ws-token endpoint with valid API key."""
        response = client.post(
            "/api/v1/auth/ws-token",
            json={"api_key": api_key}
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"

    def test_ws_token_with_invalid_api_key(self, client):
        """Test ws-token endpoint with invalid API key."""
        response = client.post(
            "/api/v1/auth/ws-token",
            json={"api_key": "invalid_api_key"}
        )

        assert response.status_code == 401


class TestWsTokenRefreshEndpoint:
    """Test cases for /auth/ws-token-refresh endpoint."""

    def test_refresh_with_valid_token(self, client, api_key):
        """Test refresh endpoint with valid refresh token."""
        token_response = client.post(
            "/api/v1/auth/ws-token",
            json={"api_key": api_key}
        )
        assert token_response.status_code == 200
        tokens = token_response.json()

        response = client.post(
            "/api/v1/auth/ws-token-refresh",
            json={"refresh_token": tokens["refresh_token"]}
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["access_token"] != tokens["access_token"]

    def test_refresh_with_invalid_token(self, client):
        """Test refresh endpoint with invalid token."""
        response = client.post(
            "/api/v1/auth/ws-token-refresh",
            json={"refresh_token": "invalid_token"}
        )

        assert response.status_code == 401


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
