"""Tests for JWT authentication middleware for WebSocket connections."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status, WebSocket
from starlette.websockets import WebSocketDisconnect

from api.middleware.jwt_auth import validate_websocket_token


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket connection."""
    websocket = MagicMock(spec=WebSocket)
    websocket.client = MagicMock()
    websocket.client.host = "127.0.0.1"
    websocket.close = AsyncMock()
    return websocket


@pytest.fixture
def mock_token_service():
    """Create a mock token service."""
    return MagicMock()


@pytest.fixture
def valid_token_payload():
    """Return a valid JWT payload."""
    return {
        "sub": "user-123",
        "jti": "token-uuid-456",
        "type": "access",
        "iat": 1234567890,
        "exp": 9999999999,
        "iss": "claude-agent-sdk",
        "aud": "claude-agent-sdk-users",
    }


class TestValidateWebSocketTokenWithTokenService:
    """Test cases for validate_websocket_token when token_service is configured."""

    @pytest.mark.asyncio
    async def test_valid_token_returns_user_id_and_jti(
        self, mock_websocket, mock_token_service, valid_token_payload
    ):
        """Test that valid token returns user_id and jti."""
        token = "valid.jwt.token"
        mock_token_service.decode_token_any_type.return_value = valid_token_payload

        with patch("api.middleware.jwt_auth.token_service", mock_token_service):
            user_id, jti = await validate_websocket_token(mock_websocket, token)

            assert user_id == "user-123"
            assert jti == "token-uuid-456"
            mock_websocket.close.assert_not_called()

    @pytest.mark.asyncio
    async def test_valid_token_with_missing_optional_fields(
        self, mock_websocket, mock_token_service
    ):
        """Test valid token with only required fields (sub and jti)."""
        token = "valid.jwt.token"
        minimal_payload = {"sub": "user-123", "jti": "token-456"}
        mock_token_service.decode_token_any_type.return_value = minimal_payload

        with patch("api.middleware.jwt_auth.token_service", mock_token_service):
            user_id, jti = await validate_websocket_token(mock_websocket, token)

            assert user_id == "user-123"
            assert jti == "token-456"
            mock_websocket.close.assert_not_called()

    @pytest.mark.asyncio
    async def test_missing_token_closes_connection(
        self, mock_websocket, mock_token_service
    ):
        """Test that missing token closes connection with policy violation."""
        mock_token_service.decode_token_any_type.return_value = None

        with patch("api.middleware.jwt_auth.token_service", mock_token_service):
            with pytest.raises(WebSocketDisconnect) as exc_info:
                await validate_websocket_token(mock_websocket, token=None)

            assert exc_info.value.code == status.WS_1008_POLICY_VIOLATION
            assert exc_info.value.reason == "Authentication token required"
            mock_websocket.close.assert_called_once_with(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Authentication token required",
            )

    @pytest.mark.asyncio
    async def test_empty_token_closes_connection(
        self, mock_websocket, mock_token_service
    ):
        """Test that empty string token closes connection with policy violation."""
        mock_token_service.decode_token_any_type.return_value = None

        with patch("api.middleware.jwt_auth.token_service", mock_token_service):
            with pytest.raises(WebSocketDisconnect) as exc_info:
                await validate_websocket_token(mock_websocket, token="")

            assert exc_info.value.code == status.WS_1008_POLICY_VIOLATION
            assert exc_info.value.reason == "Authentication token required"
            mock_websocket.close.assert_called_once_with(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Authentication token required",
            )

    @pytest.mark.asyncio
    async def test_invalid_token_closes_connection(
        self, mock_websocket, mock_token_service
    ):
        """Test that invalid token closes connection with policy violation."""
        token = "invalid.jwt.token"
        mock_token_service.decode_token_any_type.return_value = None

        with patch("api.middleware.jwt_auth.token_service", mock_token_service):
            with pytest.raises(WebSocketDisconnect) as exc_info:
                await validate_websocket_token(mock_websocket, token)

            assert exc_info.value.code == status.WS_1008_POLICY_VIOLATION
            assert exc_info.value.reason == "Invalid or expired JWT token"
            mock_websocket.close.assert_called_once_with(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Invalid or expired JWT token",
            )

    @pytest.mark.asyncio
    async def test_expired_token_closes_connection(
        self, mock_websocket, mock_token_service
    ):
        """Test that expired token closes connection with policy violation."""
        token = "expired.jwt.token"
        mock_token_service.decode_token_any_type.return_value = None

        with patch("api.middleware.jwt_auth.token_service", mock_token_service):
            with pytest.raises(WebSocketDisconnect) as exc_info:
                await validate_websocket_token(mock_websocket, token)

            assert exc_info.value.code == status.WS_1008_POLICY_VIOLATION
            assert exc_info.value.reason == "Invalid or expired JWT token"
            mock_websocket.close.assert_called_once_with(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Invalid or expired JWT token",
            )

    @pytest.mark.asyncio
    async def test_token_without_sub_field_returns_none(
        self, mock_websocket, mock_token_service
    ):
        """Test that token without 'sub' field returns None for user_id."""
        token = "valid.jwt.token"
        payload_without_sub = {"jti": "token-456"}
        mock_token_service.decode_token_any_type.return_value = payload_without_sub

        with patch("api.middleware.jwt_auth.token_service", mock_token_service):
            user_id, jti = await validate_websocket_token(mock_websocket, token)

            assert user_id is None
            assert jti == "token-456"

    @pytest.mark.asyncio
    async def test_token_without_jti_field_returns_none(
        self, mock_websocket, mock_token_service
    ):
        """Test that token without 'jti' field returns None for jti."""
        token = "valid.jwt.token"
        payload_without_jti = {"sub": "user-123"}
        mock_token_service.decode_token_any_type.return_value = payload_without_jti

        with patch("api.middleware.jwt_auth.token_service", mock_token_service):
            user_id, jti = await validate_websocket_token(mock_websocket, token)

            assert user_id == "user-123"
            assert jti is None

    @pytest.mark.asyncio
    async def test_token_service_decode_called_with_correct_token(
        self, mock_websocket, mock_token_service, valid_token_payload
    ):
        """Test that decode_token_any_type is called with the provided token."""
        token = "specific.jwt.token"
        mock_token_service.decode_token_any_type.return_value = valid_token_payload

        with patch("api.middleware.jwt_auth.token_service", mock_token_service):
            await validate_websocket_token(mock_websocket, token)

            mock_token_service.decode_token_any_type.assert_called_once_with(token)


class TestValidateWebSocketTokenWithoutTokenService:
    """Test cases for validate_websocket_token when token_service is not configured."""

    @pytest.mark.asyncio
    async def test_no_token_service_closes_connection(self, mock_websocket):
        """Test that missing token_service closes connection with internal error."""
        with patch("api.middleware.jwt_auth.token_service", None):
            with pytest.raises(WebSocketDisconnect) as exc_info:
                await validate_websocket_token(mock_websocket, token="any.token")

            assert exc_info.value.code == status.WS_1011_INTERNAL_ERROR
            assert exc_info.value.reason == "JWT authentication not configured"
            mock_websocket.close.assert_called_once_with(
                code=status.WS_1011_INTERNAL_ERROR,
                reason="JWT authentication not configured",
            )

    @pytest.mark.asyncio
    async def test_no_token_service_with_valid_token_still_fails(
        self, mock_websocket
    ):
        """Test that even a valid token fails when token_service is None."""
        with patch("api.middleware.jwt_auth.token_service", None):
            with pytest.raises(WebSocketDisconnect) as exc_info:
                await validate_websocket_token(
                    mock_websocket, token="valid.jwt.token"
                )

            assert exc_info.value.code == status.WS_1011_INTERNAL_ERROR
            mock_websocket.close.assert_called_once()


class TestValidateWebSocketTokenWebSocketClientInfo:
    """Test cases for WebSocket client information handling."""

    @pytest.mark.asyncio
    async def test_missing_token_logs_client_host(
        self, mock_websocket, mock_token_service, caplog
    ):
        """Test that missing token logs the client host for debugging."""
        mock_websocket.client.host = "192.168.1.100"
        mock_token_service.decode_token_any_type.return_value = None

        with patch("api.middleware.jwt_auth.token_service", mock_token_service):
            with pytest.raises(WebSocketDisconnect):
                await validate_websocket_token(mock_websocket, token=None)

        # Check that warning was logged with client info
        assert any(
            "client=192.168.1.100" in record.message
            for record in caplog.records
        )

    @pytest.mark.asyncio
    async def test_invalid_token_logs_client_host(
        self, mock_websocket, mock_token_service, caplog
    ):
        """Test that invalid token logs the client host for debugging."""
        mock_websocket.client.host = "10.0.0.50"
        mock_token_service.decode_token_any_type.return_value = None

        with patch("api.middleware.jwt_auth.token_service", mock_token_service):
            with pytest.raises(WebSocketDisconnect):
                await validate_websocket_token(mock_websocket, token="bad.token")

        # Check that warning was logged with client info
        assert any(
            "client=10.0.0.50" in record.message
            for record in caplog.records
        )

    @pytest.mark.asyncio
    async def test_logs_unknown_when_client_is_none(
        self, mock_websocket, mock_token_service, caplog
    ):
        """Test that 'unknown' is logged when websocket.client is None."""
        mock_websocket.client = None
        mock_token_service.decode_token_any_type.return_value = None

        with patch("api.middleware.jwt_auth.token_service", mock_token_service):
            with pytest.raises(WebSocketDisconnect):
                await validate_websocket_token(mock_websocket, token=None)

        # Check that 'unknown' is logged instead of crashing
        assert any(
            "client=unknown" in record.message
            for record in caplog.records
        )


class TestValidateWebSocketTokenDebugLogging:
    """Test cases for debug logging behavior."""

    @pytest.mark.asyncio
    async def test_successful_authentication_logs_debug(
        self, mock_websocket, mock_token_service, valid_token_payload, caplog
    ):
        """Test that successful authentication logs user info at debug level."""
        token = "valid.jwt.token"
        mock_token_service.decode_token_any_type.return_value = valid_token_payload

        with caplog.at_level("DEBUG"):
            with patch("api.middleware.jwt_auth.token_service", mock_token_service):
                user_id, jti = await validate_websocket_token(mock_websocket, token)

                assert user_id == "user-123"
                # Verify debug log contains user info
                assert any(
                    f"user={user_id}" in record.message
                    for record in caplog.records
                )

    @pytest.mark.asyncio
    async def test_no_token_service_logs_error(
        self, mock_websocket, caplog
    ):
        """Test that missing token_service logs error message."""
        with patch("api.middleware.jwt_auth.token_service", None):
            with pytest.raises(WebSocketDisconnect):
                await validate_websocket_token(mock_websocket, token="any.token")

        # Check that error was logged
        assert any(
            "JWT authentication not configured" in record.message
            for record in caplog.records
            if record.levelname == "ERROR"
        )


class TestValidateWebSocketTokenDifferentTokenTypes:
    """Test cases for different JWT token types."""

    @pytest.mark.asyncio
    async def test_accepts_access_token(
        self, mock_websocket, mock_token_service
    ):
        """Test that access type tokens are accepted."""
        access_token_payload = {
            "sub": "user-123",
            "jti": "access-456",
            "type": "access",
        }
        mock_token_service.decode_token_any_type.return_value = access_token_payload

        with patch("api.middleware.jwt_auth.token_service", mock_token_service):
            user_id, jti = await validate_websocket_token(
                mock_websocket, token="access.token"
            )

            assert user_id == "user-123"
            assert jti == "access-456"
            mock_websocket.close.assert_not_called()

    @pytest.mark.asyncio
    async def test_accepts_refresh_token(
        self, mock_websocket, mock_token_service
    ):
        """Test that refresh type tokens are accepted."""
        refresh_token_payload = {
            "sub": "user-123",
            "jti": "refresh-789",
            "type": "refresh",
        }
        mock_token_service.decode_token_any_type.return_value = refresh_token_payload

        with patch("api.middleware.jwt_auth.token_service", mock_token_service):
            user_id, jti = await validate_websocket_token(
                mock_websocket, token="refresh.token"
            )

            assert user_id == "user-123"
            assert jti == "refresh-789"
            mock_websocket.close.assert_not_called()

    @pytest.mark.asyncio
    async def test_accepts_user_identity_token(
        self, mock_websocket, mock_token_service
    ):
        """Test that user_identity type tokens are accepted."""
        user_identity_payload = {
            "sub": "user-123",
            "jti": "identity-101",
            "type": "user_identity",
        }
        mock_token_service.decode_token_any_type.return_value = user_identity_payload

        with patch("api.middleware.jwt_auth.token_service", mock_token_service):
            user_id, jti = await validate_websocket_token(
                mock_websocket, token="identity.token"
            )

            assert user_id == "user-123"
            assert jti == "identity-101"
            mock_websocket.close.assert_not_called()

    @pytest.mark.asyncio
    async def test_accepts_token_without_type(
        self, mock_websocket, mock_token_service
    ):
        """Test that tokens without type field are accepted."""
        no_type_payload = {
            "sub": "user-123",
            "jti": "notype-202",
        }
        mock_token_service.decode_token_any_type.return_value = no_type_payload

        with patch("api.middleware.jwt_auth.token_service", mock_token_service):
            user_id, jti = await validate_websocket_token(
                mock_websocket, token="notype.token"
            )

            assert user_id == "user-123"
            assert jti == "notype-202"
            mock_websocket.close.assert_not_called()


class TestValidateWebSocketTokenEdgeCases:
    """Test cases for edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_malformed_token_handled_gracefully(
        self, mock_websocket, mock_token_service
    ):
        """Test that malformed tokens are handled without crashing."""
        malformed_token = "not.a.valid.jwt.token.format"
        mock_token_service.decode_token_any_type.return_value = None

        with patch("api.middleware.jwt_auth.token_service", mock_token_service):
            with pytest.raises(WebSocketDisconnect) as exc_info:
                await validate_websocket_token(mock_websocket, malformed_token)

            assert exc_info.value.code == status.WS_1008_POLICY_VIOLATION

    @pytest.mark.asyncio
    async def test_whitespace_only_token_rejected(
        self, mock_websocket, mock_token_service
    ):
        """Test that whitespace-only tokens are rejected."""
        whitespace_token = "   "
        mock_token_service.decode_token_any_type.return_value = None

        with patch("api.middleware.jwt_auth.token_service", mock_token_service):
            # Whitespace is truthy, so decode is called but returns None
            with pytest.raises(WebSocketDisconnect) as exc_info:
                await validate_websocket_token(mock_websocket, whitespace_token)

            assert exc_info.value.code == status.WS_1008_POLICY_VIOLATION

    @pytest.mark.asyncio
    async def test_token_with_extra_claims_preserves_them(
        self, mock_websocket, mock_token_service
    ):
        """Test that tokens with extra claims work correctly."""
        extra_claims_payload = {
            "sub": "user-123",
            "jti": "token-456",
            "type": "access",
            "username": "testuser",
            "role": "admin",
            "custom_field": "custom_value",
        }
        mock_token_service.decode_token_any_type.return_value = extra_claims_payload

        with patch("api.middleware.jwt_auth.token_service", mock_token_service):
            user_id, jti = await validate_websocket_token(
                mock_websocket, token="token.with.claims"
            )

            # Only sub and jti are extracted
            assert user_id == "user-123"
            assert jti == "token-456"

    @pytest.mark.asyncio
    async def test_empty_sub_field_returns_empty_string(
        self, mock_websocket, mock_token_service
    ):
        """Test that empty sub field returns empty string."""
        empty_sub_payload = {"sub": "", "jti": "token-456"}
        mock_token_service.decode_token_any_type.return_value = empty_sub_payload

        with patch("api.middleware.jwt_auth.token_service", mock_token_service):
            user_id, jti = await validate_websocket_token(
                mock_websocket, token="token"
            )

            assert user_id == ""
            assert jti == "token-456"

    @pytest.mark.asyncio
    async def test_empty_jti_field_returns_empty_string(
        self, mock_websocket, mock_token_service
    ):
        """Test that empty jti field returns empty string."""
        empty_jti_payload = {"sub": "user-123", "jti": ""}
        mock_token_service.decode_token_any_type.return_value = empty_jti_payload

        with patch("api.middleware.jwt_auth.token_service", mock_token_service):
            user_id, jti = await validate_websocket_token(
                mock_websocket, token="token"
            )

            assert user_id == "user-123"
            assert jti == ""


class TestValidateWebSocketTokenRevokedTokens:
    """Test cases for revoked token handling."""

    @pytest.mark.asyncio
    async def test_revoked_token_rejected(
        self, mock_websocket, mock_token_service
    ):
        """Test that revoked tokens are rejected."""
        # Token service returns None for revoked tokens
        mock_token_service.decode_token_any_type.return_value = None

        with patch("api.middleware.jwt_auth.token_service", mock_token_service):
            with pytest.raises(WebSocketDisconnect) as exc_info:
                await validate_websocket_token(
                    mock_websocket, token="revoked.token"
                )

            assert exc_info.value.code == status.WS_1008_POLICY_VIOLATION
            assert "Invalid or expired JWT token" in exc_info.value.reason


class TestValidateWebSocketTokenCloseCallOrdering:
    """Test cases for WebSocket close call ordering."""

    @pytest.mark.asyncio
    async def test_websocket_closed_before_exception_raised(
        self, mock_websocket, mock_token_service
    ):
        """Test that websocket.close() is called before WebSocketDisconnect is raised."""
        close_call_order = []

        async def track_close(*args, **kwargs):
            close_call_order.append("close")

        mock_websocket.close = AsyncMock(side_effect=track_close)
        mock_token_service.decode_token_any_type.return_value = None

        with patch("api.middleware.jwt_auth.token_service", mock_token_service):
            try:
                await validate_websocket_token(mock_websocket, token=None)
            except WebSocketDisconnect:
                close_call_order.append("exception")

            # Close should be called before exception
            assert close_call_order == ["close", "exception"]

    @pytest.mark.asyncio
    async def test_close_code_matches_disconnect_code_for_missing_token(
        self, mock_websocket, mock_token_service
    ):
        """Test that close code matches WebSocketDisconnect code for missing token."""
        mock_token_service.decode_token_any_type.return_value = None

        with patch("api.middleware.jwt_auth.token_service", mock_token_service):
            with pytest.raises(WebSocketDisconnect) as exc_info:
                await validate_websocket_token(mock_websocket, token=None)

            # Get the close call arguments
            close_call = mock_websocket.close.call_args
            assert close_call[1]["code"] == exc_info.value.code
            assert close_call[1]["reason"] == exc_info.value.reason

    @pytest.mark.asyncio
    async def test_close_code_matches_disconnect_code_for_invalid_token(
        self, mock_websocket, mock_token_service
    ):
        """Test that close code matches WebSocketDisconnect code for invalid token."""
        mock_token_service.decode_token_any_type.return_value = None

        with patch("api.middleware.jwt_auth.token_service", mock_token_service):
            with pytest.raises(WebSocketDisconnect) as exc_info:
                await validate_websocket_token(mock_websocket, token="invalid")

            # Get the close call arguments
            close_call = mock_websocket.close.call_args
            assert close_call[1]["code"] == exc_info.value.code
            assert close_call[1]["reason"] == exc_info.value.reason
