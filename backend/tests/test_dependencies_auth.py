"""Tests for authentication dependencies."""
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from api.dependencies.auth import (
    get_current_user,
    get_current_user_optional,
    get_current_user_ws,
)
from api.models.user_auth import UserTokenPayload


class TestGetCurrentUser:
    """Test cases for get_current_user dependency."""

    @pytest.mark.asyncio
    async def test_returns_user_from_request_state(self):
        """Test that user is correctly extracted from request.state."""
        mock_request = MagicMock()
        mock_request.state.user = {
            "user_id": "user-123",
            "username": "testuser",
            "role": "user",
        }

        result = await get_current_user(mock_request)

        assert isinstance(result, UserTokenPayload)
        assert result.user_id == "user-123"
        assert result.username == "testuser"
        assert result.role == "user"

    @pytest.mark.asyncio
    async def test_returns_user_from_request_state_admin(self):
        """Test that admin role is correctly extracted."""
        mock_request = MagicMock()
        mock_request.state.user = {
            "user_id": "admin-456",
            "username": "admin",
            "role": "admin",
        }

        result = await get_current_user(mock_request)

        assert result.user_id == "admin-456"
        assert result.username == "admin"
        assert result.role == "admin"

    @pytest.mark.asyncio
    async def test_defaults_to_user_role_when_missing(self):
        """Test that missing role defaults to 'user'."""
        mock_request = MagicMock()
        mock_request.state.user = {
            "user_id": "user-789",
            "username": "norole",
        }

        result = await get_current_user(mock_request)

        assert result.role == "user"

    @pytest.mark.asyncio
    async def test_raises_401_when_user_context_is_empty_dict(self):
        """Test that empty dict is treated as no authentication (falsy value)."""
        mock_request = MagicMock()
        mock_request.state.user = {}

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request)

        assert exc_info.value.status_code == 401
        assert "authentication required" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_raises_401_when_no_user_context(self):
        """Test that missing user context raises 401 error."""
        mock_request = MagicMock()
        mock_request.state.user = None

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request)

        assert exc_info.value.status_code == 401
        assert "authentication required" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_raises_401_when_user_attribute_missing(self):
        """Test that missing user attribute on state raises 401."""
        mock_request = MagicMock()
        # Simulate getattr returning None for missing attribute
        del mock_request.state.user

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request)

        assert exc_info.value.status_code == 401
        assert "authentication required" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_succeeds_with_at_least_one_field(self):
        """Test that context with at least username field passes."""
        # Empty dict is falsy, but dict with content works
        mock_request = MagicMock()
        mock_request.state.user = {"username": "test"}

        result = await get_current_user(mock_request)

        assert result.username == "test"
        assert result.user_id == ""
        assert result.role == "user"


class TestGetCurrentUserOptional:
    """Test cases for get_current_user_optional dependency."""

    @pytest.mark.asyncio
    async def test_returns_user_from_request_state(self):
        """Test that user is correctly extracted when present."""
        mock_request = MagicMock()
        mock_request.state.user = {
            "user_id": "user-123",
            "username": "testuser",
            "role": "admin",
        }

        result = await get_current_user_optional(mock_request)

        assert isinstance(result, UserTokenPayload)
        assert result.user_id == "user-123"
        assert result.username == "testuser"
        assert result.role == "admin"

    @pytest.mark.asyncio
    async def test_returns_none_when_no_user_context(self):
        """Test that missing user context returns None."""
        mock_request = MagicMock()
        mock_request.state.user = None

        result = await get_current_user_optional(mock_request)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_user_attribute_missing(self):
        """Test that missing user attribute returns None."""
        mock_request = MagicMock()
        del mock_request.state.user

        result = await get_current_user_optional(mock_request)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_user_context_is_falsy(self):
        """Test that falsy user context values return None."""
        mock_request = MagicMock()
        mock_request.state.user = False

        result = await get_current_user_optional(mock_request)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_user_with_defaults_for_missing_fields(self):
        """Test that defaults are applied when fields are missing."""
        mock_request = MagicMock()
        mock_request.state.user = {"username": "partial"}

        result = await get_current_user_optional(mock_request)

        assert isinstance(result, UserTokenPayload)
        assert result.user_id == ""
        assert result.username == "partial"
        assert result.role == "user"


class TestGetCurrentUserWs:
    """Test cases for get_current_user_ws WebSocket dependency."""

    @pytest.mark.asyncio
    async def test_returns_user_from_valid_token(self):
        """Test that valid token returns UserTokenPayload."""
        mock_service = MagicMock()
        mock_service.decode_token_any_type.return_value = {
            "user_id": "ws-user-123",
            "username": "wsuser",
            "role": "user",
            "sub": "sub-123",
            "jti": "jti-abc",
            "exp": 9999999999,
        }

        with patch('api.dependencies.auth.token_service', mock_service):
            result = await get_current_user_ws("valid-token")

            assert isinstance(result, UserTokenPayload)
            assert result.user_id == "ws-user-123"
            assert result.username == "wsuser"
            assert result.role == "user"
            mock_service.decode_token_any_type.assert_called_once_with("valid-token")

    @pytest.mark.asyncio
    async def test_returns_user_with_sub_fallback(self):
        """Test that user_id falls back to 'sub' claim when 'user_id' missing."""
        mock_service = MagicMock()
        mock_service.decode_token_any_type.return_value = {
            "sub": "fallback-user-456",
            "username": "fallback",
            "role": "admin",
        }

        with patch('api.dependencies.auth.token_service', mock_service):
            result = await get_current_user_ws("valid-token")

            assert result.user_id == "fallback-user-456"
            assert result.username == "fallback"
            assert result.role == "admin"

    @pytest.mark.asyncio
    async def test_returns_user_with_role_default(self):
        """Test that missing role defaults to 'user'."""
        mock_service = MagicMock()
        mock_service.decode_token_any_type.return_value = {
            "user_id": "user-no-role",
            "username": "norole",
        }

        with patch('api.dependencies.auth.token_service', mock_service):
            result = await get_current_user_ws("valid-token")

            assert result.role == "user"

    @pytest.mark.asyncio
    async def test_raises_500_when_token_service_not_configured(self):
        """Test that missing token_service raises 500 error."""
        with patch('api.dependencies.auth.token_service', None):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user_ws("any-token")

            assert exc_info.value.status_code == 500
            assert "not configured" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_raises_401_when_token_decode_returns_none(self):
        """Test that invalid/expired token raises 401."""
        mock_service = MagicMock()
        mock_service.decode_token_any_type.return_value = None

        with patch('api.dependencies.auth.token_service', mock_service):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user_ws("invalid-token")

            assert exc_info.value.status_code == 401
            assert "invalid or expired" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_raises_401_when_username_missing(self):
        """Test that token without username raises 401."""
        mock_service = MagicMock()
        mock_service.decode_token_any_type.return_value = {
            "user_id": "no-username",
            "role": "user",
        }

        with patch('api.dependencies.auth.token_service', mock_service):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user_ws("token-without-username")

            assert exc_info.value.status_code == 401
            assert "missing user identity" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_raises_401_when_username_empty(self):
        """Test that empty username raises 401."""
        mock_service = MagicMock()
        mock_service.decode_token_any_type.return_value = {
            "user_id": "empty-username",
            "username": "",
        }

        with patch('api.dependencies.auth.token_service', mock_service):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user_ws("token-with-empty-username")

            assert exc_info.value.status_code == 401
            assert "missing user identity" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_user_id_fallback_to_empty_string(self):
        """Test that user_id defaults to empty string when both user_id and sub missing."""
        mock_service = MagicMock()
        mock_service.decode_token_any_type.return_value = {
            "username": "minimal",
        }

        with patch('api.dependencies.auth.token_service', mock_service):
            result = await get_current_user_ws("minimal-token")

            assert result.user_id == ""
            assert result.username == "minimal"
            assert result.role == "user"

    @pytest.mark.asyncio
    async def test_all_claims_present(self):
        """Test with all possible claims present."""
        mock_service = MagicMock()
        mock_service.decode_token_any_type.return_value = {
            "user_id": "full-user-789",
            "sub": "sub-backup",
            "username": "fulluser",
            "role": "admin",
            "full_name": "Full User Name",
            "email": "user@example.com",
        }

        with patch('api.dependencies.auth.token_service', mock_service):
            result = await get_current_user_ws("full-token")

            assert result.user_id == "full-user-789"  # user_id takes precedence
            assert result.username == "fulluser"
            assert result.role == "admin"


class TestUserTokenPayloadConstruction:
    """Test UserTokenPayload model validation."""

    def test_valid_user_payload(self):
        """Test creating a valid UserTokenPayload."""
        payload = UserTokenPayload(
            user_id="test-id",
            username="testuser",
            role="user"
        )

        assert payload.user_id == "test-id"
        assert payload.username == "testuser"
        assert payload.role == "user"

    def test_admin_role_validation(self):
        """Test that admin role is valid."""
        payload = UserTokenPayload(
            user_id="admin-id",
            username="admin",
            role="admin"
        )

        assert payload.role == "admin"

    def test_invalid_role_raises_error(self):
        """Test that invalid role raises validation error."""
        with pytest.raises(ValueError):
            UserTokenPayload(
                user_id="test-id",
                username="testuser",
                role="superuser"  # Invalid role
            )

    def test_model_dump(self):
        """Test that model can be serialized."""
        payload = UserTokenPayload(
            user_id="test-id",
            username="testuser",
            role="user"
        )

        data = payload.model_dump()

        assert data == {
            "user_id": "test-id",
            "username": "testuser",
            "role": "user"
        }
