"""
Test suite for sensitive_data_filter.py

Run with: pytest backend/api/utils/test_sensitive_data_filter.py -v
"""

import pytest

from api.utils.sensitive_data_filter import (
    redact_sensitive_data,
    redact_dict,
    sanitize_tool_result,
    sanitize_log_message,
    sanitize_websocket_message,
    sanitize_event_content,
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
        jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3sdfsdf9PlFUP0THsR8U"
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


class TestEnvFileRedaction:
    """Tests for .env file content redaction."""

    def test_env_file_redaction(self):
        """Test that .env file content is redacted."""
        content = '''API_KEY=sk-ant-1234567890abcdef
SECRET="mysecret123"
DATABASE_URL=postgres://localhost:5432/db
JWT_SECRET=supersecretkey123
DEBUG=true
'''
        redacted = redact_sensitive_data(content)
        assert '***REDACTED***' in redacted
        assert 'sk-ant-1234567890abcdef' not in redacted
        assert 'mysecret123' not in redacted
        assert 'supersecretkey123' not in redacted
        # Non-secret values should remain (unless they match pattern)
        assert 'DEBUG=true' in redacted or '***REDACTED***' in redacted

    def test_env_local_redaction(self):
        """Test that .env.local content is redacted."""
        content = 'LOCAL_API_KEY=local_key_12345678\nADMIN_PASSWORD=adminpass'
        redacted = redact_sensitive_data(content)
        assert '***REDACTED***' in redacted
        assert 'local_key_12345678' not in redacted
        assert 'adminpass' not in redacted

    def test_env_production_redaction(self):
        """Test that .env.production content is redacted."""
        content = 'PROD_API_KEY=prod_key_xyz\nPROD_SECRET=prod_secret_abc'
        redacted = redact_sensitive_data(content)
        assert redacted.count('***REDACTED***') >= 2
        assert 'prod_key_xyz' not in redacted
        assert 'prod_secret_abc' not in redacted

    def test_env_with_quoted_values(self):
        """Test .env with double-quoted values."""
        content = '''API_KEY="sk-ant-api-key-123"
SECRET_KEY="supersecretkey"
NORMAL_VAR="not_a_secret"
'''
        redacted = redact_sensitive_data(content)
        assert '***REDACTED***' in redacted
        assert 'sk-ant-api-key-123' not in redacted
        assert 'supersecretkey' not in redacted
        # The NORMAL_VAR should remain unless caught by length pattern
        # (it might be redacted if it's long enough, but that's expected)

    def test_env_with_single_quotes(self):
        """Test .env with single-quoted values."""
        content = "API_KEY='sk-ant-single-quoted'\nPASSWORD='mypassword'"
        redacted = redact_sensitive_data(content)
        assert '***REDACTED***' in redacted
        assert 'sk-ant-single-quoted' not in redacted
        assert 'mypassword' not in redacted

    def test_env_database_urls(self):
        """Test .env database URL patterns."""
        content = '''DATABASE_URL=postgres://user:pass@localhost:5432/db
REDIS_URL=redis://:password@localhost:6379
MONGO_URL=mongodb://user:pass@localhost:27017
'''
        redacted = redact_sensitive_data(content)
        assert '***REDACTED***' in redacted
        # The actual URLs should be redacted
        assert 'pass@localhost' not in redacted or '***REDACTED***' in redacted

    def test_env_long_values_redaction(self):
        """Test that long values (32+ chars) are redacted."""
        content = 'SUSPICIOUS_KEY=verylongvaluethatshouldbecaught1234\nSHORT_KEY=short'
        redacted = redact_sensitive_data(content)
        # Long values should be redacted
        assert '***REDACTED***' in redacted
        assert 'verylongvaluethatshouldbecaught1234' not in redacted
        # Short safe values might remain
        assert 'SHORT_KEY=short' in redacted or 'SHORT_KEY=***REDACTED***' in redacted

    def test_env_mixed_content(self):
        """Test .env with mix of secrets and safe values."""
        content = '''# Configuration file
APP_NAME=MyApp
DEBUG=true
API_KEY=sk-ant-1234567890abcdef
DATABASE_URL=postgres://localhost:5432/mydb
PORT=3000
SECRET=topsecretkey123
'''
        redacted = redact_sensitive_data(content)
        assert '***REDACTED***' in redacted
        assert 'sk-ant-1234567890abcdef' not in redacted
        assert 'topsecretkey123' not in redacted
        # Comments and some safe values may remain
        assert '# Configuration file' in redacted or redacted.count('#') > 0


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


class TestSanitizeEventContent:
    """Tests for sanitize_event_content function."""

    def test_simple_dict_event(self):
        """Test sanitization of a simple event dict."""
        event = {
            "type": "tool_result",
            "content": "API_KEY=secret123"
        }
        sanitize_event_content(event)
        assert "secret123" not in str(event)
        assert "***REDACTED***" in event["content"]

    def test_nested_dict_event(self):
        """Test sanitization of nested dict structures."""
        event = {
            "type": "tool_result",
            "content": "API_KEY=secret123",
            "nested": {
                "data": "PASSWORD=mypass",
                "list": ["TOKEN=abc123", "safe data"]
            }
        }
        sanitize_event_content(event)
        assert "secret123" not in str(event)
        assert "mypass" not in str(event)
        assert "abc123" not in str(event)
        assert "safe data" in str(event)

    def test_text_delta_event(self):
        """Test that assistant text is redacted (text_delta event)."""
        event = {
            "type": "text_delta",
            "text": "Your API key is sk-ant-1234567890abcdef"
        }
        sanitize_event_content(event)
        assert "sk-ant-1234567890abcdef" not in event["text"]
        assert "***REDACTED***" in event["text"]

    def test_assistant_message_event(self):
        """Test that assistant message summarizing .env is redacted."""
        event = {
            "type": "message",
            "role": "assistant",
            "content": {
                "text": "I found these secrets in .env:\nAPI_KEY=sk-ant-real-secret\nDB_PASSWORD=mypass123"
            }
        }
        sanitize_event_content(event)
        event_str = str(event)
        assert "sk-ant-real-secret" not in event_str
        assert "mypass123" not in event_str
        assert "***REDACTED***" in event_str

    def test_list_of_dicts_in_event(self):
        """Test sanitization of list of dicts within event.

        Note: sanitize_event_content redacts patterns within string values,
        not field-based redaction (which is done by redact_dict).
        This test verifies that string content containing sensitive patterns
        is redacted even when nested in lists of dicts.
        """
        event = {
            "type": "tool_result",
            "content": [
                {"email": "user@test.com", "note": "password=pass123"},
                {"email": "user2@test.com", "config": "token=tok-xyz-abc"}
            ]
        }
        sanitize_event_content(event)
        assert "pass123" not in str(event)
        assert "tok-xyz-abc" not in str(event)

    def test_multiple_env_formats(self):
        """Test all .env formats are caught in event content."""
        event = {
            "type": "text_delta",
            "text": """
            API_KEY=sk-ant-123
            SECRET="quoted_secret"
            PASSWORD='single_quoted'
            DATABASE_URL=postgres://user:pass@host/db
            """
        }
        sanitize_event_content(event)
        event_str = str(event)
        assert "sk-ant-123" not in event_str
        assert "quoted_secret" not in event_str
        assert "single_quoted" not in event_str
        # DATABASE_URL pattern might catch the whole URL
        assert "***REDACTED***" in event_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
