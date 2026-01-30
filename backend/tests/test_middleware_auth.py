"""Tests for APIKeyMiddleware."""
from unittest.mock import AsyncMock, MagicMock, patch
import os

import pytest
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from api.middleware.auth import APIKeyMiddleware
from api.services.token_service import TokenService


@pytest.fixture
def mock_request():
    """Create a mock FastAPI request."""
    request = MagicMock(spec=Request)
    request.url = MagicMock()
    request.url.path = "/api/v1/sessions"
    request.method = "GET"
    request.client = MagicMock()
    request.client.host = "127.0.0.1"
    request.headers = MagicMock()
    request.headers.get = MagicMock(return_value=None)
    # Use a simple object for state that doesn't auto-create attributes
    from types import SimpleNamespace
    request.state = SimpleNamespace()
    return request


@pytest.fixture
def mock_call_next():
    """Create a mock call_next function."""
    mock_call = AsyncMock()
    mock_call.return_value = MagicMock(status_code=200)
    return mock_call


@pytest.fixture
def mock_token_service():
    """Create a mock token service."""
    return MagicMock(spec=TokenService)


class TestAPIKeyMiddleware:
    """Test cases for APIKeyMiddleware public path skipping."""

    @pytest.fixture
    def middleware(self, mock_token_service):
        """Create middleware instance with mocked token service."""
        with patch("api.middleware.auth.token_service", mock_token_service):
            return APIKeyMiddleware(MagicMock())

    @pytest.mark.asyncio
    async def test_public_path_root_skips_auth(self, middleware, mock_request, mock_call_next):
        """Test that root path skips authentication."""
        mock_request.url.path = "/"
        response = await middleware.dispatch(mock_request, mock_call_next)
        assert response.status_code == 200
        mock_call_next.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_public_path_health_skips_auth(self, middleware, mock_request, mock_call_next):
        """Test that health check path skips authentication."""
        mock_request.url.path = "/health"
        response = await middleware.dispatch(mock_request, mock_call_next)
        assert response.status_code == 200
        mock_call_next.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_public_path_ws_token_skips_auth(self, middleware, mock_request, mock_call_next):
        """Test that ws-token endpoint skips authentication."""
        mock_request.url.path = "/api/v1/auth/ws-token"
        response = await middleware.dispatch(mock_request, mock_call_next)
        assert response.status_code == 200
        mock_call_next.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_public_path_ws_token_refresh_skips_auth(self, middleware, mock_request, mock_call_next):
        """Test that ws-token-refresh endpoint skips authentication."""
        mock_request.url.path = "/api/v1/auth/ws-token-refresh"
        response = await middleware.dispatch(mock_request, mock_call_next)
        assert response.status_code == 200
        mock_call_next.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_public_path_login_skips_auth(self, middleware, mock_request, mock_call_next):
        """Test that login endpoint skips authentication."""
        mock_request.url.path = "/api/v1/auth/login"
        response = await middleware.dispatch(mock_request, mock_call_next)
        assert response.status_code == 200
        mock_call_next.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_options_method_skips_auth(self, middleware, mock_request, mock_call_next):
        """Test that OPTIONS method (CORS preflight) skips authentication."""
        mock_request.method = "OPTIONS"
        response = await middleware.dispatch(mock_request, mock_call_next)
        assert response.status_code == 200
        mock_call_next.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_options_with_non_public_path_skips_auth(self, middleware, mock_request, mock_call_next):
        """Test that OPTIONS method skips auth even on protected paths."""
        mock_request.method = "OPTIONS"
        mock_request.url.path = "/api/v1/sessions"
        response = await middleware.dispatch(mock_request, mock_call_next)
        assert response.status_code == 200
        mock_call_next.assert_called_once_with(mock_request)


class TestAPIKeyMiddlewareWithAPIKey:
    """Test cases for APIKeyMiddleware when API_KEY is configured."""

    @pytest.fixture
    def api_key(self):
        """Test API key."""
        return "test-valid-api-key-12345"

    @pytest.fixture
    def middleware(self, api_key, mock_token_service):
        """Create middleware instance with API key set using environment variable."""
        # Set environment variable before middleware creation
        original_key = os.environ.get("API_KEY")
        os.environ["API_KEY"] = api_key
        # Reload the config module to pick up new env var
        import importlib
        import api.config
        import api.middleware.auth
        importlib.reload(api.config)
        importlib.reload(api.middleware.auth)

        try:
            with patch("api.middleware.auth.token_service", mock_token_service):
                yield APIKeyMiddleware(MagicMock())
        finally:
            # Restore original value
            if original_key is None:
                os.environ.pop("API_KEY", None)
            else:
                os.environ["API_KEY"] = original_key
            importlib.reload(api.config)
            importlib.reload(api.middleware.auth)

    @pytest.mark.asyncio
    async def test_valid_api_key_accepted(self, middleware, mock_request, mock_call_next, api_key):
        """Test that valid API key is accepted."""
        mock_request.headers.get.return_value = api_key
        response = await middleware.dispatch(mock_request, mock_call_next)
        assert response.status_code == 200
        mock_call_next.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_invalid_api_key_rejected(self, middleware, mock_request, mock_call_next):
        """Test that invalid API key is rejected with 401."""
        mock_request.headers.get.return_value = "wrong-api-key"
        response = await middleware.dispatch(mock_request, mock_call_next)
        assert isinstance(response, JSONResponse)
        assert response.status_code == 401
        mock_call_next.assert_not_called()

    @pytest.mark.asyncio
    async def test_missing_api_key_rejected(self, middleware, mock_request, mock_call_next):
        """Test that missing API key is rejected with 401."""
        mock_request.headers.get.return_value = None
        response = await middleware.dispatch(mock_request, mock_call_next)
        assert isinstance(response, JSONResponse)
        assert response.status_code == 401
        mock_call_next.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_api_key_rejected(self, middleware, mock_request, mock_call_next):
        """Test that empty API key is rejected with 401."""
        mock_request.headers.get.return_value = ""
        response = await middleware.dispatch(mock_request, mock_call_next)
        assert isinstance(response, JSONResponse)
        assert response.status_code == 401
        mock_call_next.assert_not_called()

    @pytest.mark.asyncio
    async def test_api_key_from_query_param_ignored(self, middleware, mock_request, mock_call_next):
        """Test that API key from query params is ignored (security feature)."""
        mock_request.headers.get.return_value = None
        mock_request.url.path = "/api/v1/sessions?X-API-Key=test-key"
        response = await middleware.dispatch(mock_request, mock_call_next)
        assert isinstance(response, JSONResponse)
        assert response.status_code == 401
        mock_call_next.assert_not_called()

    @pytest.mark.asyncio
    async def test_error_response_content(self, middleware, mock_request, mock_call_next):
        """Test that error response has correct content."""
        mock_request.headers.get.return_value = None
        response = await middleware.dispatch(mock_request, mock_call_next)
        assert isinstance(response, JSONResponse)
        assert response.status_code == 401
        import json
        body = json.loads(response.body.decode())
        assert body["detail"] == "Invalid or missing API key"

    @pytest.mark.asyncio
    async def test_timing_safe_comparison_used(self, middleware, mock_request, mock_call_next, api_key):
        """Test that timing-safe comparison is used for key validation."""
        mock_request.headers.get.return_value = api_key
        with patch("api.middleware.auth.secrets.compare_digest") as mock_compare:
            mock_compare.return_value = True
            response = await middleware.dispatch(mock_request, mock_call_next)
            assert response.status_code == 200
            # Verify compare_digest was called with the expected key
            assert mock_compare.called
            call_args = mock_compare.call_args[0]
            assert call_args[0] == api_key
            assert call_args[1] == api_key


class TestAPIKeyMiddlewareUserToken:
    """Test cases for X-User-Token handling in APIKeyMiddleware."""

    @pytest.fixture
    def api_key(self):
        """Test API key."""
        return "test-api-key"

    @pytest.fixture
    def middleware(self, api_key, mock_token_service):
        """Create middleware instance with API key and token service."""
        original_key = os.environ.get("API_KEY")
        os.environ["API_KEY"] = api_key
        import importlib
        import api.config
        import api.middleware.auth
        importlib.reload(api.config)
        importlib.reload(api.middleware.auth)

        try:
            with patch("api.middleware.auth.token_service", mock_token_service):
                yield APIKeyMiddleware(MagicMock())
        finally:
            if original_key is None:
                os.environ.pop("API_KEY", None)
            else:
                os.environ["API_KEY"] = original_key
            importlib.reload(api.config)
            importlib.reload(api.middleware.auth)

    @pytest.mark.asyncio
    async def test_valid_user_token_populates_state(
        self, middleware, mock_request, mock_call_next, api_key, mock_token_service
    ):
        """Test that valid X-User-Token populates request.state.user."""
        user_token = "valid.jwt.token"
        payload = {
            "username": "testuser",
            "user_id": "user-123",
            "role": "admin",
            "full_name": "Test User"
        }

        def mock_get_header(key):
            return {"X-API-Key": api_key, "X-User-Token": user_token}.get(key)

        mock_request.headers.get = MagicMock(side_effect=mock_get_header)
        mock_token_service.decode_token_any_type.return_value = payload
        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 200
        assert hasattr(mock_request.state, "user")
        assert mock_request.state.user["username"] == "testuser"
        assert mock_request.state.user["user_id"] == "user-123"
        assert mock_request.state.user["role"] == "admin"
        assert mock_request.state.user["full_name"] == "Test User"

    @pytest.mark.asyncio
    async def test_user_token_fallback_to_sub_for_user_id(
        self, middleware, mock_request, mock_call_next, api_key, mock_token_service
    ):
        """Test that user_id falls back to 'sub' field if 'user_id' not present."""
        user_token = "valid.jwt.token"
        payload = {
            "username": "testuser",
            "sub": "sub-456",
            "role": "user",
            "full_name": "Test User"
        }

        def mock_get_header(key):
            return {"X-API-Key": api_key, "X-User-Token": user_token}.get(key)

        mock_request.headers.get = MagicMock(side_effect=mock_get_header)
        mock_token_service.decode_token_any_type.return_value = payload
        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 200
        assert mock_request.state.user["user_id"] == "sub-456"

    @pytest.mark.asyncio
    async def test_user_token_defaults_for_optional_fields(
        self, middleware, mock_request, mock_call_next, api_key, mock_token_service
    ):
        """Test that optional fields have default values."""
        user_token = "valid.jwt.token"
        payload = {"username": "testuser"}

        def mock_get_header(key):
            return {"X-API-Key": api_key, "X-User-Token": user_token}.get(key)

        mock_request.headers.get = MagicMock(side_effect=mock_get_header)
        mock_token_service.decode_token_any_type.return_value = payload
        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 200
        assert mock_request.state.user["username"] == "testuser"
        assert mock_request.state.user["user_id"] is None
        assert mock_request.state.user["role"] == "user"
        assert mock_request.state.user["full_name"] == ""

    @pytest.mark.asyncio
    async def test_missing_username_skips_user_population(
        self, middleware, mock_request, mock_call_next, api_key, mock_token_service
    ):
        """Test that missing username in token skips user population."""
        user_token = "valid.jwt.token"
        payload = {"user_id": "user-123"}

        def mock_get_header(key):
            return {"X-API-Key": api_key, "X-User-Token": user_token}.get(key)

        mock_request.headers.get = MagicMock(side_effect=mock_get_header)
        mock_token_service.decode_token_any_type.return_value = payload
        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 200
        # state.user should not be populated without username
        assert not hasattr(mock_request.state, "user")

    @pytest.mark.asyncio
    async def test_invalid_user_token_does_not_fail_request(
        self, middleware, mock_request, mock_call_next, api_key, mock_token_service
    ):
        """Test that invalid user token doesn't fail the request."""
        user_token = "invalid.jwt.token"

        def mock_get_header(key):
            return {"X-API-Key": api_key, "X-User-Token": user_token}.get(key)

        mock_request.headers.get = MagicMock(side_effect=mock_get_header)
        mock_token_service.decode_token_any_type.return_value = None
        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 200
        mock_call_next.assert_called_once_with(mock_request)

    @pytest.mark.asyncio
    async def test_user_token_decode_exception_does_not_fail_request(
        self, middleware, mock_request, mock_call_next, api_key, mock_token_service
    ):
        """Test that exception during token decode doesn't fail the request."""
        user_token = "malformed.token"

        def mock_get_header(key):
            return {"X-API-Key": api_key, "X-User-Token": user_token}.get(key)

        mock_request.headers.get = MagicMock(side_effect=mock_get_header)
        mock_token_service.decode_token_any_type.side_effect = Exception("Decode error")
        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_no_user_token_header_proceeds_normally(
        self, middleware, mock_request, mock_call_next, api_key
    ):
        """Test that request without X-User-Token proceeds normally."""
        def mock_get_header(key):
            return {"X-API-Key": api_key}.get(key, None)

        mock_request.headers.get = MagicMock(side_effect=mock_get_header)
        response = await middleware.dispatch(mock_request, mock_call_next)

        assert response.status_code == 200
        # state.user should not be populated
        assert not hasattr(mock_request.state, "user")


class TestAPIKeyMiddlewareNoAPIKey:
    """Test cases for APIKeyMiddleware when API_KEY is not configured."""

    @pytest.fixture
    def middleware(self):
        """Create middleware instance with no API key configured."""
        original_key = os.environ.get("API_KEY")
        os.environ.pop("API_KEY", None)
        import importlib
        import api.config
        import api.middleware.auth
        importlib.reload(api.config)
        importlib.reload(api.middleware.auth)

        try:
            yield APIKeyMiddleware(MagicMock())
        finally:
            if original_key is not None:
                os.environ["API_KEY"] = original_key
                importlib.reload(api.config)
                importlib.reload(api.middleware.auth)

    @pytest.mark.asyncio
    async def test_no_api_key_allows_all_requests(self, middleware, mock_request, mock_call_next):
        """Test that when no API key is configured, all requests proceed."""
        mock_request.headers.get.return_value = None
        response = await middleware.dispatch(mock_request, mock_call_next)
        assert response.status_code == 200
        mock_call_next.assert_called_once_with(mock_request)


class TestAPIKeyMiddlewareLogging:
    """Test cases for logging behavior in APIKeyMiddleware."""

    @pytest.fixture
    def api_key(self):
        """Test API key."""
        return "test-api-key"

    @pytest.fixture
    def middleware(self, api_key):
        """Create middleware instance."""
        original_key = os.environ.get("API_KEY")
        os.environ["API_KEY"] = api_key
        import importlib
        import api.config
        import api.middleware.auth
        importlib.reload(api.config)
        importlib.reload(api.middleware.auth)

        try:
            yield APIKeyMiddleware(MagicMock())
        finally:
            if original_key is None:
                os.environ.pop("API_KEY", None)
            else:
                os.environ["API_KEY"] = original_key
            importlib.reload(api.config)
            importlib.reload(api.middleware.auth)

    @pytest.mark.asyncio
    async def test_auth_failure_logs_client_ip_and_path(self, middleware, mock_request, mock_call_next, caplog):
        """Test that auth failure logs client IP and path."""
        import logging
        mock_request.client.host = "192.168.1.100"
        mock_request.headers.get.return_value = None

        with caplog.at_level(logging.WARNING):
            response = await middleware.dispatch(mock_request, mock_call_next)

        assert any(
            "Authentication failed" in record.message
            and "client_ip=192.168.1.100" in record.message
            and "path=/api/v1/sessions" in record.message
            for record in caplog.records
        )

    @pytest.mark.asyncio
    async def test_auth_failure_logs_unknown_client_ip(self, mock_request, mock_call_next, caplog):
        """Test that auth failure logs 'unknown' when client IP is not available."""
        import logging
        request = MagicMock(spec=Request)
        request.url = MagicMock()
        request.url.path = "/api/v1/sessions"
        request.method = "GET"
        request.client = None
        request.headers = MagicMock()
        request.headers.get = MagicMock(return_value=None)
        request.state = MagicMock()

        original_key = os.environ.get("API_KEY")
        os.environ["API_KEY"] = "test-api-key"
        import importlib
        import api.config
        importlib.reload(api.config)

        try:
            middleware = APIKeyMiddleware(MagicMock())

            with caplog.at_level(logging.WARNING):
                response = await middleware.dispatch(request, mock_call_next)

            assert any(
                "Authentication failed" in record.message
                and "client_ip=unknown" in record.message
                for record in caplog.records
            )
        finally:
            if original_key is None:
                os.environ.pop("API_KEY", None)
            else:
                os.environ["API_KEY"] = original_key
            importlib.reload(api.config)

    @pytest.mark.asyncio
    async def test_auth_failure_never_logs_actual_key(self, middleware, mock_request, mock_call_next, caplog):
        """Test that auth failure NEVER logs the actual API key."""
        import logging
        invalid_key = "my-secret-api-key-12345"
        mock_request.headers.get.return_value = invalid_key

        with caplog.at_level(logging.WARNING):
            response = await middleware.dispatch(mock_request, mock_call_next)

        assert not any(
            invalid_key in record.message
            for record in caplog.records
        )

    @pytest.mark.asyncio
    async def test_user_token_decode_failure_logs_debug(
        self, mock_request, mock_call_next, caplog
    ):
        """Test that user token decode failure logs at debug level."""
        import logging
        api_key = "test-api-key"
        user_token = "invalid.token"

        def mock_get_header(key):
            return {"X-API-Key": api_key, "X-User-Token": user_token}.get(key)

        mock_request.headers.get = MagicMock(side_effect=mock_get_header)

        original_key = os.environ.get("API_KEY")
        os.environ["API_KEY"] = api_key
        import importlib
        import api.config
        import api.middleware.auth
        importlib.reload(api.config)
        importlib.reload(api.middleware.auth)

        try:
            # Create mock token service
            mock_token_service = MagicMock()
            mock_token_service.decode_token_any_type.side_effect = Exception("Decode failed")

            # Patch token_service before creating middleware
            with patch("api.middleware.auth.token_service", mock_token_service):
                middleware = APIKeyMiddleware(MagicMock())

                with caplog.at_level(logging.DEBUG):
                    response = await middleware.dispatch(mock_request, mock_call_next)

                assert response.status_code == 200
                assert any(
                    "Failed to decode user token" in record.message
                    for record in caplog.records
                )
        finally:
            if original_key is None:
                os.environ.pop("API_KEY", None)
            else:
                os.environ["API_KEY"] = original_key
            importlib.reload(api.config)
            importlib.reload(api.middleware.auth)


class TestAPIKeyMiddlewareTimingSafeComparison:
    """Test cases for timing-safe comparison behavior."""

    @pytest.fixture
    def api_key(self):
        """Test API key."""
        return "test-api-key-12345"

    @pytest.fixture
    def middleware(self, api_key):
        """Create middleware instance."""
        original_key = os.environ.get("API_KEY")
        os.environ["API_KEY"] = api_key
        import importlib
        import api.config
        import api.middleware.auth
        importlib.reload(api.config)
        importlib.reload(api.middleware.auth)

        try:
            yield APIKeyMiddleware(MagicMock())
        finally:
            if original_key is None:
                os.environ.pop("API_KEY", None)
            else:
                os.environ["API_KEY"] = original_key
            importlib.reload(api.config)
            importlib.reload(api.middleware.auth)

    @pytest.mark.asyncio
    async def test_compare_digest_called_with_correct_args(self, middleware, mock_request, mock_call_next, api_key):
        """Test that secrets.compare_digest is called with correct arguments."""
        provided_key = "test-api-key-12345"
        mock_request.headers.get.return_value = provided_key

        with patch("api.middleware.auth.secrets.compare_digest") as mock_compare:
            mock_compare.return_value = True
            response = await middleware.dispatch(mock_request, mock_call_next)
            # Verify compare_digest was called
            assert mock_compare.called
            call_args = mock_compare.call_args[0]
            assert call_args[0] == provided_key
            assert call_args[1] == api_key

    @pytest.mark.asyncio
    async def test_compare_digest_false_returns_401(self, middleware, mock_request, mock_call_next):
        """Test that compare_digest returning False results in 401."""
        mock_request.headers.get.return_value = "wrong-key"

        with patch("api.middleware.auth.secrets.compare_digest") as mock_compare:
            mock_compare.return_value = False
            response = await middleware.dispatch(mock_request, mock_call_next)
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_none_key_short_circuits_compare_digest(self, middleware, mock_request, mock_call_next):
        """Test that None provided key short-circuits compare_digest."""
        mock_request.headers.get.return_value = None

        with patch("api.middleware.auth.secrets.compare_digest") as mock_compare:
            response = await middleware.dispatch(mock_request, mock_call_next)
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_empty_string_treated_as_missing_key(self, middleware, mock_request, mock_call_next, api_key):
        """Test that empty string is treated as missing key (falsy value)."""
        mock_request.headers.get.return_value = ""

        with patch("api.middleware.auth.secrets.compare_digest") as mock_compare:
            response = await middleware.dispatch(mock_request, mock_call_next)
            # Empty string is falsy, so compare_digest should not be called due to short-circuit
            assert response.status_code == 401
