"""
Test suite for sensitive_data_filter.py

Run with: pytest backend/api/utils/test_sensitive_data_filter.py -v
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from sensitive_data_filter import (
    redact_sensitive_data,
    redact_dict,
    sanitize_tool_result,
    sanitize_log_message,
    sanitize_websocket_message,
    is_safe_for_logging,
    get_safe_repr,
    redact,
)


class TestRedactSensitiveData:
    """Tests for redact_sensitive_data function."""

    def test_oauth_tokens(self):
        """Test OAuth token redaction."""
        result1 = redact_sensitive_data('access_token = "secret123"')
        assert '***REDACTED***' in result1
        assert 'secret123' not in result1

        result2 = redact_sensitive_data('refresh_token:"xyz789"')
        assert '***REDACTED***' in result2
        assert 'xyz789' not in result2

    def test_bearer_tokens(self):
        """Test Bearer token redaction."""
        jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        assert redact_sensitive_data(f'Bearer {jwt_token}') == 'Bearer ***REDACTED***'

    def test_api_keys(self):
        """Test API key redaction."""
        result1 = redact_sensitive_data('api_key: sk-1234567890abcdef')
        assert '***REDACTED***' in result1
        assert 'sk-1234567890abcdef' not in result1

        result2 = redact_sensitive_data('AIzaSyDaAbC1234567890abcdef')
        assert result2 == '***REDACTED***'

    def test_passwords(self):
        """Test password redaction."""
        result1 = redact_sensitive_data('password: "secret123"')
        assert '***REDACTED***' in result1
        assert 'secret123' not in result1

        result2 = redact_sensitive_data('app_password = "mypassword"')
        assert '***REDACTED***' in result2
        assert 'mypassword' not in result2

    def test_auth_markers(self):
        """Test auth type marker redaction."""
        assert redact_sensitive_data('[OAuth] Connected') == '[****] Connected'
        assert redact_sensitive_data('[app_password] Auth success') == '[****] Auth success'

    def test_base64_strings(self):
        """Test long base64 string redaction."""
        long_b64 = "VGhpcyBpcyBhIHZlcnkgbG9uZyBiYXNlNjQgZW5jb2RlZCBzdHJpbmcgdGhhdCBzaG91bGQgYmUgcmVkYWN0ZWQ="
        assert redact_sensitive_data(long_b64) == '***REDACTED***'

    def test_context_aware_redaction(self):
        """Test context-specific redaction."""
        result = redact_sensitive_data(
            '{"app_password": "mypassword"}',
            context='email'
        )
        assert '***REDACTED***' in result
        assert 'mypassword' not in result

    def test_imap_connection_string(self):
        """Test IMAP connection string redaction."""
        result = redact_sensitive_data('user@imap.gmail.com:password123@imap.gmail.com')
        assert 'password123' not in result
        assert '***REDACTED***' in result


class TestRedactDict:
    """Tests for redact_dict function."""

    def test_simple_dict(self):
        """Test dictionary redaction."""
        data = {
            "email": "user@example.com",
            "app_password": "secret123",
            "host": "imap.gmail.com"
        }
        result = redact_dict(data)
        assert result["email"] == "user@example.com"
        assert result["app_password"] == "***REDACTED***"
        assert result["host"] == "imap.gmail.com"

    def test_nested_dict(self):
        """Test nested dictionary redaction."""
        data = {
            "credentials": {
                "access_token": "secret_token",
                "refresh_token": "another_secret"
            },
            "safe_field": "public_data"
        }
        result = redact_dict(data)
        assert result["credentials"]["access_token"] == "***REDACTED***"
        assert result["credentials"]["refresh_token"] == "***REDACTED***"
        assert result["safe_field"] == "public_data"

    def test_list_of_dicts(self):
        """Test list redaction."""
        data = [
            {"token": "secret1", "id": "1"},
            {"token": "secret2", "id": "2"}
        ]
        result = redact_dict(data)
        assert result[0]["token"] == "***REDACTED***"
        assert result[0]["id"] == "1"
        assert result[1]["token"] == "***REDACTED***"

    def test_case_insensitive_keys(self):
        """Test case-insensitive key detection."""
        data = {
            "Password": "secret",
            "API_KEY": "key123",
            "AccessToken": "token123"
        }
        result = redact_dict(data)
        assert result["Password"] == "***REDACTED***"
        assert result["API_KEY"] == "***REDACTED***"
        assert result["AccessToken"] == "***REDACTED***"


class TestSanitizeToolResult:
    """Tests for sanitize_tool_result function."""

    def test_email_tool(self):
        """Test email tool sanitization."""
        content = '{"access_token": "secret123", "email": "user@example.com"}'
        result = sanitize_tool_result(content, 'email_imap_connect')
        assert '***REDACTED***' in result
        assert 'secret123' not in result

    def test_string_with_auth_marker(self):
        """Test string with auth marker."""
        result = sanitize_tool_result('[OAuth] Successfully connected', 'email_gmail_send')
        assert '[****]' in result
        assert '[OAuth]' not in result

    def test_dict_content(self):
        """Test dictionary content."""
        content = {"token": "secret", "status": "success"}
        result = sanitize_tool_result(content, 'whatsapp_send')
        assert result["token"] == "***REDACTED***"
        assert result["status"] == "success"


class TestSanitizeLogMessage:
    """Tests for sanitize_log_message function."""

    def test_token_in_log(self):
        """Test token in log message."""
        msg = 'User authenticated with access_token="abc123xyz"'
        result = sanitize_log_message(msg)
        assert '***REDACTED***' in result
        assert 'abc123xyz' not in result

    def test_connection_string(self):
        """Test connection string in log."""
        msg = 'Connecting: user@host.com:password123@imap.host.com'
        result = sanitize_log_message(msg)
        assert 'password123' not in result
        assert '***REDACTED***' in result

    def test_url_with_token(self):
        """Test URL with token parameter."""
        msg = 'Request: https://api.example.com/webhook?token=secret123'
        result = sanitize_log_message(msg)
        assert 'secret123' not in result
        assert '***REDACTED***' in result

    def test_authorization_header(self):
        """Test Authorization header in log."""
        msg = 'Headers: Authorization: Bearer secret_token_123'
        result = sanitize_log_message(msg)
        assert 'secret_token_123' not in result
        assert '***REDACTED***' in result


class TestSanitizeWebSocketMessage:
    """Tests for sanitize_websocket_message function."""

    def test_tool_result_message(self):
        """Test WebSocket tool_result message."""
        msg = {
            "type": "tool_result",
            "tool": "email_gmail_send",
            "content": '{"access_token": "secret"}'
        }
        result = sanitize_websocket_message(msg)
        assert '***REDACTED***' in result["content"]
        assert 'secret' not in result["content"]

    def test_regular_message(self):
        """Test regular WebSocket message."""
        msg = {
            "type": "message",
            "content": "Here is my password: secret123"
        }
        result = sanitize_websocket_message(msg)
        assert 'secret123' not in result["content"]


class TestIsSafeForLogging:
    """Tests for is_safe_for_logging function."""

    def test_safe_data(self):
        """Test safe data."""
        assert is_safe_for_logging('{"user": "john", "email": "john@example.com"}') == True
        assert is_safe_for_logging('Processing request') == True

    def test_unsafe_data(self):
        """Test unsafe data."""
        assert is_safe_for_logging('{"password": "secret123"}') == False
        # Short tokens may pass length check but are still checked
        # The important thing is that actual long tokens are caught
        assert is_safe_for_logging('Bearer verylongtokenthatshouldbecaught12345') == False
        assert is_safe_for_logging('api_key=sk-1234567890') == False


class TestGetSafeRepr:
    """Tests for get_safe_repr function."""

    def test_dict_repr(self):
        """Test dictionary representation."""
        data = {"user": "john", "password": "secret"}
        result = get_safe_repr(data)
        assert '"user": "john"' in result
        assert '"password": "***REDACTED***"' in result
        assert 'secret' not in result

    def test_truncation(self):
        """Test output truncation."""
        data = {"key": "x" * 200}
        result = get_safe_repr(data, max_length=50)
        # The data gets redacted first, making it shorter, so it may not truncate
        # But if it does truncate, it should have '...'
        assert len(result) <= 53  # max_length + '...'
        # Verify the data was redacted
        assert '***REDACTED***' in result


class TestRedactConvenience:
    """Tests for redact convenience function."""

    def test_string_input(self):
        """Test string input."""
        assert redact('password: secret') == 'password: ***REDACTED***'

    def test_dict_input(self):
        """Test dictionary input."""
        result = redact({"token": "secret", "user": "john"})
        assert result["token"] == "***REDACTED***"
        assert result["user"] == "john"

    def test_list_input(self):
        """Test list input."""
        result = redact([{"password": "secret"}])
        assert result[0]["password"] == "***REDACTED***"


class TestRealWorldScenarios:
    """Tests for real-world scenarios."""

    def test_gmail_oauth_response(self):
        """Test Gmail OAuth response redaction."""
        response = {
            "access_token": "ya29.a0AfH6SMBx...",
            "refresh_token": "1//0gxyz...",
            "expires_in": 3600,
            "token_type": "Bearer",
            "email": "user@gmail.com"
        }
        result = redact_dict(response)
        assert result["access_token"] == "***REDACTED***"
        assert result["refresh_token"] == "***REDACTED***"
        assert result["expires_in"] == 3600
        assert result["email"] == "user@gmail.com"

    def test_whatsapp_connection(self):
        """Test WhatsApp connection redaction."""
        msg = 'Connected to WhatsApp with token: abcdef1234567890'
        result = sanitize_log_message(msg)
        assert '***REDACTED***' in result
        assert 'abcdef1234567890' not in result

    def test_imap_credentials(self):
        """Test IMAP credential storage redaction."""
        data = {
            "email": "user@imap.gmail.com",
            "app_password": "abcd efgh ijkl mnop",
            "host": "imap.gmail.com",
            "port": 993
        }
        result = redact_dict(data)
        assert result["app_password"] == "***REDACTED***"
        assert result["email"] == "user@imap.gmail.com"

    def test_tool_result_with_email(self):
        """Test tool result containing email data."""
        content = '''
        Email sent successfully!
        From: sender@example.com
        To: recipient@example.com
        Subject: Test
        Using access_token: ya29.a0AfH6SMBx...
        '''
        result = sanitize_tool_result(content, 'email_gmail_send')
        assert 'ya29.a0AfH6SMBx' not in result
        assert '***REDACTED***' in result

    def test_websocket_message_chain(self):
        """Test complete WebSocket message sanitization."""
        msg = {
            "type": "tool_result",
            "tool": "email_imap_connect",
            "content": {
                "status": "success",
                "credentials": {
                    "email": "user@example.com",
                    "app_password": "secret123"
                }
            }
        }
        result = sanitize_websocket_message(msg)
        assert result["content"]["credentials"]["app_password"] == "***REDACTED***"
        assert result["content"]["credentials"]["email"] == "user@example.com"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
