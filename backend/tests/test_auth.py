"""
Tests for JWT authentication functionality.
"""
import os
from datetime import datetime, timedelta

import pytest
from jose import jwt

from api.services.token_service import TokenService, token_service
from api.config import JWT_CONFIG


# Skip tests if JWT is not configured
pytestmark = pytest.mark.skipif(
    not JWT_CONFIG.get("secret_key"),
    reason="JWT_SECRET_KEY not configured"
)


class TestTokenService:
    """Test cases for TokenService."""

    def test_create_access_token(self):
        """Test access token creation."""
        service = TokenService()
        user_id = "test_user_123"

        token, jti, expires_in = service.create_access_token(user_id)

        assert token is not None
        assert jti is not None
        assert expires_in > 0
        # Check expiration is approximately 30 minutes (1800 seconds)
        assert 1750 <= expires_in <= 1850

    def test_create_refresh_token(self):
        """Test refresh token creation."""
        service = TokenService()
        user_id = "test_user_123"

        token = service.create_refresh_token(user_id)

        assert token is not None

        # Decode and check type
        payload = jwt.decode(
            token,
            service.secret_key,
            algorithms=[service.algorithm],
            audience=service.audience,
            issuer=service.issuer,
        )

        assert payload["type"] == "refresh"
        assert payload["sub"] == user_id

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

    def test_validate_valid_access_token(self):
        """Test validation of a valid access token."""
        service = TokenService()
        user_id = "test_user_123"

        token, jti, expires_in = service.create_access_token(user_id)

        # Validate the token
        payload = service.decode_and_validate_token(token, token_type="access")

        assert payload is not None
        assert payload["sub"] == user_id
        assert payload["jti"] == jti
        assert payload["type"] == "access"

    def test_validate_valid_refresh_token(self):
        """Test validation of a valid refresh token."""
        service = TokenService()
        user_id = "test_user_123"

        token = service.create_refresh_token(user_id)

        # Validate the token
        payload = service.decode_and_validate_token(token, token_type="refresh")

        assert payload is not None
        assert payload["sub"] == user_id
        assert payload["type"] == "refresh"

    def test_validate_invalid_token(self):
        """Test validation of an invalid token."""
        service = TokenService()

        # Use a completely invalid token
        invalid_token = "invalid.token.string"

        payload = service.decode_and_validate_token(invalid_token, token_type="access")

        assert payload is None

    def test_validate_token_with_wrong_type(self):
        """Test validation fails when token type doesn't match."""
        service = TokenService()
        user_id = "test_user_123"

        # Create an access token
        token, _, _ = service.create_access_token(user_id)

        # Try to validate it as a refresh token
        payload = service.decode_and_validate_token(token, token_type="refresh")

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

    def test_is_token_revoked(self):
        """Test is_token_revoked method."""
        service = TokenService()

        # Token not revoked initially
        assert not service.is_token_revoked("some_jti")

        # Revoke token
        service.revoke_token("some_jti")

        # Now it should be revoked
        assert service.is_token_revoked("some_jti")

    def test_token_expiration(self):
        """Test that expired tokens are rejected."""
        service = TokenService()

        # Create an expired token manually
        now = datetime.utcnow()
        expire = now - timedelta(seconds=60)  # Expired 60 seconds ago

        payload = {
            "sub": "test_user",
            "jti": "expired_jti",
            "type": "access",
            "iat": int((now - timedelta(seconds=120)).timestamp()),
            "exp": int(expire.timestamp()),
            "iss": service.issuer,
            "aud": service.audience,
        }

        expired_token = jwt.encode(payload, service.secret_key, algorithm=service.algorithm)

        # Should fail validation
        result = service.decode_and_validate_token(expired_token, token_type="access")
        assert result is None

    def test_token_claims(self):
        """Test that token claims are correctly set."""
        service = TokenService()
        user_id = "test_user_123"

        token, jti, _ = service.create_access_token(user_id)

        payload = jwt.decode(
            token,
            service.secret_key,
            algorithms=[service.algorithm],
            audience=service.audience,
            issuer=service.issuer,
        )

        # Check all expected claims
        assert payload["sub"] == user_id
        assert payload["jti"] == jti
        assert payload["type"] == "access"
        assert "iat" in payload
        assert "exp" in payload
        assert payload["iss"] == service.issuer
        assert payload["aud"] == service.audience

    def test_user_id_from_api_key(self):
        """Test user ID generation from API key."""
        service = TokenService()
        api_key = "test_api_key_12345"

        user_id = service._get_user_id_from_api_key(api_key)

        assert user_id is not None
        assert isinstance(user_id, str)
        assert len(user_id) == 32  # SHA256 hash truncated to 32 chars

        # Same API key should produce same user ID
        user_id2 = service._get_user_id_from_api_key(api_key)
        assert user_id == user_id2

        # Different API key should produce different user ID
        user_id3 = service._get_user_id_from_api_key("different_api_key")
        assert user_id != user_id3


class TestAuthEndpoints:
    """Test cases for authentication endpoints."""

    def test_auth_status_no_jwt(self, client):
        """Test auth status endpoint when JWT is not configured."""
        # This test should pass even without JWT configured
        response = client.get("/api/v1/auth/status")

        assert response.status_code == 200
        data = response.json()
        assert "jwt_enabled" in data

    @pytest.mark.skipif(
        not JWT_CONFIG.get("secret_key"),
        reason="JWT_SECRET_KEY not configured"
    )
    def test_login_with_invalid_api_key(self, client):
        """Test login endpoint with invalid API key."""
        response = client.post(
            "/api/v1/auth/login",
            json={"api_key": "invalid_api_key"}
        )

        assert response.status_code == 401

    @pytest.mark.skipif(
        not JWT_CONFIG.get("secret_key"),
        reason="JWT_SECRET_KEY not configured"
    )
    def test_login_without_api_key(self, client):
        """Test login endpoint without API key."""
        response = client.post(
            "/api/v1/auth/login",
            json={}
        )

        assert response.status_code == 422  # Validation error


class TestTokenRefresh:
    """Test cases for token refresh functionality."""

    def test_refresh_with_invalid_token(self, client):
        """Test refresh endpoint with invalid token."""
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid_token"}
        )

        # Should return 401 or 501 depending on JWT configuration
        assert response.status_code in [401, 501]

    def test_refresh_without_token(self, client):
        """Test refresh endpoint without token."""
        response = client.post(
            "/api/v1/auth/refresh",
            json={}
        )

        assert response.status_code == 422  # Validation error


class TestTokenLogout:
    """Test cases for token logout functionality."""

    def test_logout_with_invalid_token(self, client):
        """Test logout endpoint with invalid token."""
        response = client.post(
            "/api/v1/auth/logout",
            json={"token": "invalid_token"}
        )

        # Should return 401 or 501 depending on JWT configuration
        assert response.status_code in [401, 501]

    def test_logout_without_token(self, client):
        """Test logout endpoint without token."""
        response = client.post(
            "/api/v1/auth/logout",
            json={}
        )

        assert response.status_code == 422  # Validation error
