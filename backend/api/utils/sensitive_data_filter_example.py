"""
Usage Examples for Sensitive Data Filter

This file demonstrates how to use the sensitive_data_filter module
to protect sensitive information in logs, tool results, and WebSocket messages.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.utils.sensitive_data_filter import (
    redact_sensitive_data,
    redact_dict,
    sanitize_tool_result,
    sanitize_log_message,
    sanitize_websocket_message,
    is_safe_for_logging,
    get_safe_repr,
    redact,
)


# Example 1: Redacting sensitive data from text
print("=== Example 1: Text Redaction ===")
original_text = 'User logged in with access_token="ya29.a0AfH6SMBx..." and password="secret123"'
redacted_text = redact_sensitive_data(original_text)
print(f"Original: {original_text}")
print(f"Redacted: {redacted_text}")
print()


# Example 2: Redacting dictionary data
print("=== Example 2: Dictionary Redaction ===")
credentials = {
    "email": "user@gmail.com",
    "app_password": "abcd efgh ijkl mnop",
    "imap_server": "imap.gmail.com",
    "oauth_tokens": {
        "access_token": "ya29.a0AfH6SMBx...",
        "refresh_token": "1//0gxyz..."
    }
}
safe_credentials = redact_dict(credentials)
print(f"Original: {credentials}")
print(f"Redacted: {safe_credentials}")
print()


# Example 3: Sanitizing tool results
print("=== Example 3: Tool Result Sanitization ===")
tool_result = '''
Email sent successfully!
From: sender@example.com
To: recipient@example.com
Subject: Test
Using access_token: ya29.a0AfH6SMBx...
'''
safe_result = sanitize_tool_result(tool_result, 'email_gmail_send')
print(f"Original: {tool_result.strip()}")
print(f"Sanitized: {safe_result.strip()}")
print()


# Example 4: Sanitizing log messages
print("=== Example 4: Log Message Sanitization ===")
log_message = 'Connecting to IMAP: user@imap.gmail.com:password123@imap.gmail.com'
safe_log = sanitize_log_message(log_message)
print(f"Original: {log_message}")
print(f"Sanitized: {safe_log}")
print()


# Example 5: Sanitizing WebSocket messages
print("=== Example 5: WebSocket Message Sanitization ===")
ws_message = {
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
safe_ws_message = sanitize_websocket_message(ws_message)
print(f"Original content: {ws_message['content']}")
print(f"Sanitized content: {safe_ws_message['content']}")
print()


# Example 6: Checking if data is safe for logging
print("=== Example 6: Safety Check ===")
safe_data = {"user": "john", "email": "john@example.com"}
unsafe_data = {"user": "john", "password": "secret123"}

print(f"Safe data check: {is_safe_for_logging(safe_data)}")
print(f"Unsafe data check: {is_safe_for_logging(unsafe_data)}")
print()


# Example 7: Getting safe representation for debugging
print("=== Example 7: Safe Representation ===")
debug_data = {
    "email": "user@host.com",
    "password": "secret",
    "config": {"key1": "value1", "key2": "value2"}
}
safe_repr = get_safe_repr(debug_data)
print(f"Safe repr: {safe_repr}")
print()


# Example 8: Using the convenience function
print("=== Example 8: Convenience Function ===")
mixed_data = [
    "password: secret",
    {"token": "abc123xyz"},
    "normal text"
]
for item in mixed_data:
    redacted_item = redact(item)
    print(f"Original: {item} => Redacted: {redacted_item}")
print()


# Example 9: Context-aware redaction
print("=== Example 9: Context-Aware Redaction ===")
whatsapp_message = '{"token": "abcdef1234567890", "phone": "+1234567890"}'
redacted_whatsapp = redact_sensitive_data(whatsapp_message, context='whatsapp')
print(f"Original: {whatsapp_message}")
print(f"Redacted: {redacted_whatsapp}")
print()


# Example 10: Real-world log sanitization
print("=== Example 10: Real-World Log Sanitization ===")
complex_log = """
[INFO] Gmail OAuth successful
Response: {
  "access_token": "ya29.a0AfH6SMBx...",
  "refresh_token": "1//0gxyz...",
  "expires_in": 3600
}
[INFO] Connecting to IMAP: user@gmail.com:password@imap.gmail.com
[INFO] Using Bearer token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
"""
safe_complex_log = sanitize_log_message(complex_log)
print("Original log:")
print(complex_log)
print("\nSanitized log:")
print(safe_complex_log)
