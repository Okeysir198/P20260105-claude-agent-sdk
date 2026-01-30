"""Tests for WebSocket utility functions."""
import pytest
from unittest.mock import AsyncMock, MagicMock, Mock
from starlette.websockets import WebSocketDisconnect

from api.utils.websocket import close_with_error


def create_mock_websocket():
    """Create a properly mocked WebSocket object with async close method."""
    websocket = MagicMock()
    websocket.close = AsyncMock()
    return websocket


class TestCloseWithError:
    """Test cases for close_with_error function."""

    @pytest.mark.asyncio
    async def test_close_with_error_default_behavior(self):
        """Test closing WebSocket with error and raising disconnect (default)."""
        websocket = create_mock_websocket()

        with pytest.raises(WebSocketDisconnect) as exc_info:
            await close_with_error(
                websocket=websocket,
                code=1008,
                reason="Invalid token"
            )

        # Verify WebSocket.close was called
        websocket.close.assert_called_once_with(code=1008, reason="Invalid token")

        # Verify WebSocketDisconnect was raised with correct parameters
        assert exc_info.value.code == 1008
        assert exc_info.value.reason == "Invalid token"

    @pytest.mark.asyncio
    async def test_close_with_error_without_raising_disconnect(self):
        """Test closing WebSocket with error without raising disconnect."""
        websocket = create_mock_websocket()

        # Should not raise any exception
        await close_with_error(
            websocket=websocket,
            code=1000,
            reason="Normal closure",
            raise_disconnect=False
        )

        # Verify WebSocket.close was called
        websocket.close.assert_called_once_with(code=1000, reason="Normal closure")

    @pytest.mark.asyncio
    async def test_close_with_error_different_codes(self):
        """Test closing WebSocket with various close codes."""
        test_cases = [
            (1000, "Normal closure"),
            (1008, "Policy violation"),
            (1011, "Internal error"),
            (4000, "Custom error code"),
            (4999, "Another custom code"),
        ]

        for code, reason in test_cases:
            websocket = create_mock_websocket()

            with pytest.raises(WebSocketDisconnect) as exc_info:
                await close_with_error(
                    websocket=websocket,
                    code=code,
                    reason=reason
                )

            assert exc_info.value.code == code
            assert exc_info.value.reason == reason
            websocket.close.assert_called_once_with(code=code, reason=reason)

    @pytest.mark.asyncio
    async def test_close_with_error_empty_reason(self):
        """Test closing WebSocket with empty reason string."""
        websocket = create_mock_websocket()

        with pytest.raises(WebSocketDisconnect) as exc_info:
            await close_with_error(
                websocket=websocket,
                code=1008,
                reason=""
            )

        websocket.close.assert_called_once_with(code=1008, reason="")
        assert exc_info.value.reason == ""

    @pytest.mark.asyncio
    async def test_close_with_error_long_reason(self):
        """Test closing WebSocket with long reason string."""
        long_reason = "This is a very long reason string that contains " * 10
        websocket = create_mock_websocket()

        with pytest.raises(WebSocketDisconnect) as exc_info:
            await close_with_error(
                websocket=websocket,
                code=1011,
                reason=long_reason
            )

        websocket.close.assert_called_once_with(code=1011, reason=long_reason)
        assert exc_info.value.reason == long_reason

    @pytest.mark.asyncio
    async def test_close_with_error_unicode_reason(self):
        """Test closing WebSocket with Unicode characters in reason."""
        unicode_reason = "Error: Authentication failed for user Jose! 🚫"
        websocket = create_mock_websocket()

        with pytest.raises(WebSocketDisconnect) as exc_info:
            await close_with_error(
                websocket=websocket,
                code=1008,
                reason=unicode_reason
            )

        websocket.close.assert_called_once_with(code=1008, reason=unicode_reason)
        assert exc_info.value.reason == unicode_reason

    @pytest.mark.asyncio
    async def test_close_with_error_special_characters_in_reason(self):
        """Test closing WebSocket with special characters in reason."""
        special_reason = "Error: \n\t\r\"'\\<>[]{}&%$#@!"
        websocket = create_mock_websocket()

        with pytest.raises(WebSocketDisconnect) as exc_info:
            await close_with_error(
                websocket=websocket,
                code=1008,
                reason=special_reason
            )

        websocket.close.assert_called_once_with(code=1008, reason=special_reason)
        assert exc_info.value.reason == special_reason

    @pytest.mark.asyncio
    async def test_close_with_error_zero_code(self):
        """Test closing WebSocket with code 0."""
        websocket = create_mock_websocket()

        with pytest.raises(WebSocketDisconnect) as exc_info:
            await close_with_error(
                websocket=websocket,
                code=0,
                reason="Zero code"
            )

        websocket.close.assert_called_once_with(code=0, reason="Zero code")
        assert exc_info.value.code == 0

    @pytest.mark.asyncio
    async def test_close_with_error_large_code(self):
        """Test closing WebSocket with large close code."""
        websocket = create_mock_websocket()

        with pytest.raises(WebSocketDisconnect) as exc_info:
            await close_with_error(
                websocket=websocket,
                code=65535,
                reason="Max code"
            )

        websocket.close.assert_called_once_with(code=65535, reason="Max code")
        assert exc_info.value.code == 65535

    @pytest.mark.asyncio
    async def test_close_with_error_negative_code(self):
        """Test closing WebSocket with negative close code."""
        websocket = create_mock_websocket()

        with pytest.raises(WebSocketDisconnect) as exc_info:
            await close_with_error(
                websocket=websocket,
                code=-1,
                reason="Negative code"
            )

        websocket.close.assert_called_once_with(code=-1, reason="Negative code")
        assert exc_info.value.code == -1

    @pytest.mark.asyncio
    async def test_close_with_error_websocket_close_exception(self):
        """Test handling when websocket.close itself raises an exception."""
        websocket = create_mock_websocket()
        websocket.close.side_effect = RuntimeError("Connection already closed")

        with pytest.raises(RuntimeError, match="Connection already closed"):
            await close_with_error(
                websocket=websocket,
                code=1000,
                reason="Test"
            )

        websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_with_error_multiple_calls(self):
        """Test multiple calls to close_with_error with same websocket."""
        websocket = create_mock_websocket()

        # First call
        await close_with_error(
            websocket=websocket,
            code=1008,
            reason="First error",
            raise_disconnect=False
        )

        # Second call
        await close_with_error(
            websocket=websocket,
            code=1011,
            reason="Second error",
            raise_disconnect=False
        )

        # Verify both calls were made
        assert websocket.close.call_count == 2
        websocket.close.assert_any_call(code=1008, reason="First error")
        websocket.close.assert_any_call(code=1011, reason="Second error")

    @pytest.mark.asyncio
    async def test_close_with_error_return_value(self):
        """Test that function returns None when raise_disconnect is False."""
        websocket = create_mock_websocket()

        result = await close_with_error(
            websocket=websocket,
            code=1000,
            reason="Test",
            raise_disconnect=False
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_close_with_error_true_raises(self):
        """Test that raise_disconnect=True actually raises WebSocketDisconnect."""
        websocket = create_mock_websocket()

        with pytest.raises(WebSocketDisconnect):
            await close_with_error(
                websocket=websocket,
                code=1008,
                reason="Test",
                raise_disconnect=True
            )

    @pytest.mark.asyncio
    async def test_close_with_error_false_does_not_raise(self):
        """Test that raise_disconnect=False does not raise WebSocketDisconnect."""
        websocket = create_mock_websocket()

        # Should not raise
        await close_with_error(
            websocket=websocket,
            code=1008,
            reason="Test",
            raise_disconnect=False
        )

    @pytest.mark.asyncio
    async def test_close_with_error_disconnect_attributes(self):
        """Test that WebSocketDisconnect has correct attributes."""
        websocket = create_mock_websocket()

        with pytest.raises(WebSocketDisconnect) as exc_info:
            await close_with_error(
                websocket=websocket,
                code=4003,
                reason="Custom error"
            )

        # Access exception attributes
        assert hasattr(exc_info.value, 'code')
        assert hasattr(exc_info.value, 'reason')
        assert exc_info.value.code == 4003
        assert exc_info.value.reason == "Custom error"

    @pytest.mark.asyncio
    async def test_close_with_error_common_websocket_codes(self):
        """Test common WebSocket close codes from RFC 6455."""
        common_codes = {
            1000: "Normal Closure",
            1001: "Going Away",
            1002: "Protocol Error",
            1003: "Unsupported Data",
            1007: "Invalid frame payload data",
            1008: "Policy Violation",
            1009: "Message Too Big",
            1010: "Mandatory Extension",
            1011: "Internal Server Error",
            1015: "TLS Handshake",
        }

        for code, reason in common_codes.items():
            websocket = create_mock_websocket()

            with pytest.raises(WebSocketDisconnect) as exc_info:
                await close_with_error(
                    websocket=websocket,
                    code=code,
                    reason=reason
                )

            assert exc_info.value.code == code
            websocket.close.assert_called_once_with(code=code, reason=reason)

    @pytest.mark.asyncio
    async def test_close_with_error_asynchronous_execution(self):
        """Test that function properly awaits websocket.close."""
        websocket = create_mock_websocket()

        await close_with_error(
            websocket=websocket,
            code=1000,
            reason="Test async",
            raise_disconnect=False
        )

        # Verify the async close was awaited
        websocket.close.assert_awaited_once_with(code=1000, reason="Test async")

    @pytest.mark.asyncio
    async def test_close_with_error_exception_propagation(self):
        """Test that WebSocketDisconnect exception can be caught and its properties accessed."""
        websocket = create_mock_websocket()

        try:
            await close_with_error(
                websocket=websocket,
                code=4001,
                reason="Test exception propagation"
            )
            pytest.fail("Expected WebSocketDisconnect to be raised")
        except WebSocketDisconnect as e:
            assert e.code == 4001
            assert e.reason == "Test exception propagation"
            # Also verify we can catch it as generic Exception
            assert isinstance(e, Exception)

    @pytest.mark.asyncio
    async def test_close_with_error_newline_in_reason(self):
        """Test closing WebSocket with newline characters in reason."""
        reason_with_newlines = "Error occurred:\n- Invalid token\n- Expired session"
        websocket = create_mock_websocket()

        with pytest.raises(WebSocketDisconnect) as exc_info:
            await close_with_error(
                websocket=websocket,
                code=1008,
                reason=reason_with_newlines
            )

        assert exc_info.value.reason == reason_with_newlines
        websocket.close.assert_called_once_with(code=1008, reason=reason_with_newlines)

    @pytest.mark.asyncio
    async def test_close_with_error_null_bytes_in_reason(self):
        """Test closing WebSocket with null bytes in reason."""
        reason_with_null = "Error\x00with\x00null\x00bytes"
        websocket = create_mock_websocket()

        with pytest.raises(WebSocketDisconnect) as exc_info:
            await close_with_error(
                websocket=websocket,
                code=1008,
                reason=reason_with_null
            )

        assert exc_info.value.reason == reason_with_null
        websocket.close.assert_called_once_with(code=1008, reason=reason_with_null)

    @pytest.mark.asyncio
    async def test_close_with_error_very_short_reason(self):
        """Test closing WebSocket with single character reason."""
        websocket = create_mock_websocket()

        with pytest.raises(WebSocketDisconnect) as exc_info:
            await close_with_error(
                websocket=websocket,
                code=1000,
                reason="X"
            )

        assert exc_info.value.reason == "X"
        websocket.close.assert_called_once_with(code=1000, reason="X")

    @pytest.mark.asyncio
    async def test_close_with_error_json_serializable_reason(self):
        """Test that reason with JSON-like content is preserved."""
        json_like_reason = '{"error": "Authentication failed", "code": "AUTH_001"}'
        websocket = create_mock_websocket()

        with pytest.raises(WebSocketDisconnect) as exc_info:
            await close_with_error(
                websocket=websocket,
                code=1008,
                reason=json_like_reason
            )

        assert exc_info.value.reason == json_like_reason
        websocket.close.assert_called_once_with(code=1008, reason=json_like_reason)

    @pytest.mark.asyncio
    async def test_close_with_error_default_raise_disconnect_true(self):
        """Test that raise_disconnect defaults to True."""
        websocket = create_mock_websocket()

        # Don't specify raise_disconnect, should default to True
        with pytest.raises(WebSocketDisconnect):
            await close_with_error(
                websocket=websocket,
                code=1008,
                reason="Test default"
            )

    @pytest.mark.asyncio
    async def test_close_with_error_boolean_explicit_values(self):
        """Test with explicit boolean values for raise_disconnect."""
        websocket = create_mock_websocket()

        # Test with True
        with pytest.raises(WebSocketDisconnect):
            await close_with_error(
                websocket=websocket,
                code=1000,
                reason="Test",
                raise_disconnect=True
            )

        # Test with False
        websocket_mock = create_mock_websocket()
        await close_with_error(
            websocket=websocket_mock,
            code=1000,
            reason="Test",
            raise_disconnect=False
        )
        websocket_mock.close.assert_called_once()


class TestCloseWithErrorIntegration:
    """Integration-style tests for close_with_error function."""

    @pytest.mark.asyncio
    async def test_close_sequence_in_handler(self):
        """Test using close_with_error in a realistic WebSocket handler scenario."""
        async def websocket_handler(ws: MagicMock, authenticated: bool):
            """Simulated WebSocket handler that uses close_with_error."""
            if not authenticated:
                await close_with_error(
                    websocket=ws,
                    code=1008,
                    reason="Authentication failed"
                )
            await ws.close(code=1000, reason="Success")

        # Test unauthenticated path
        websocket = create_mock_websocket()
        with pytest.raises(WebSocketDisconnect) as exc_info:
            await websocket_handler(websocket, authenticated=False)

        assert exc_info.value.code == 1008
        assert exc_info.value.reason == "Authentication failed"

        # Test authenticated path
        websocket_mock = create_mock_websocket()
        await websocket_handler(websocket_mock, authenticated=True)
        websocket_mock.close.assert_called_once_with(code=1000, reason="Success")

    @pytest.mark.asyncio
    async def test_error_handling_pattern(self):
        """Test error handling pattern with close_with_error."""
        async def safe_handler(ws: MagicMock, should_fail: bool):
            """Handler that uses close_with_error for error cases."""
            try:
                if should_fail:
                    raise ValueError("Processing failed")
                await ws.close(code=1000, reason="OK")
            except Exception:
                await close_with_error(
                    websocket=ws,
                    code=1011,
                    reason="Internal processing error",
                    raise_disconnect=False
                )

        # Test error path
        websocket = create_mock_websocket()
        await safe_handler(websocket, should_fail=True)
        websocket.close.assert_called_with(code=1011, reason="Internal processing error")

        # Test success path
        websocket_mock = create_mock_websocket()
        await safe_handler(websocket_mock, should_fail=False)
        websocket_mock.close.assert_called_with(code=1000, reason="OK")

    @pytest.mark.asyncio
    async def test_multiple_error_codes_mapping(self):
        """Test mapping different error conditions to close codes."""
        error_conditions = {
            "invalid_token": (1008, "Invalid authentication token"),
            "rate_limited": (1003, "Rate limit exceeded"),
            "server_error": (1011, "Internal server error"),
            "not_found": (1000, "Resource not found"),
        }

        for error_type, (code, reason) in error_conditions.items():
            websocket = create_mock_websocket()

            with pytest.raises(WebSocketDisconnect) as exc_info:
                await close_with_error(
                    websocket=websocket,
                    code=code,
                    reason=reason
                )

            assert exc_info.value.code == code
            assert exc_info.value.reason == reason
            websocket.close.assert_called_once_with(code=code, reason=reason)
