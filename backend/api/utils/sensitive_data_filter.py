"""
Sensitive Data Filter for Claude Agent SDK

This module provides pattern-based redaction of sensitive information from:
- Log messages
- Tool results
- WebSocket output
- API responses
- .env file content (all variants: .env, .env.local, .env.production, etc.)

Supported patterns:
- OAuth tokens (access_token, refresh_token, token)
- API keys (api_key, sk-, AIza)
- Passwords (app_password, password)
- Auth type markers ([app_password], [OAuth], [oauth])
- Base64-encoded tokens (long strings)
- Bearer tokens
- JWT tokens
- .env file format (KEY=value) with common secret key names
- Long values (32+ chars) in .env format
"""

import os
import re
import json
from pathlib import Path
from typing import Any, Dict, List, Union, Optional
import base64


# Regex patterns for sensitive data
SENSITIVE_PATTERNS = [
    # ============================================================================
    # SIMPLE APPROACH: Hide ALL values after : or = in common formats
    # ============================================================================

    # Hide ALL values in markdown/credential list format: *Field*: value
    (r'(\*[^*]+?\*:\s*)([^\n]+?)(?:\n|$)', r'\1***REDACTED***\n'),

    # Hide ALL values in .env format: KEY=value (for ALL_CAPS keys)
    (r'([A-Z_][A-Z0-9_]*=\s*)([^\s\n]+)', r'\1***REDACTED***'),

    # Hide values after common credential field names (lowercase, with : separator)
    # Uses [^ \n] to only match values on same line (space or newline ends it)
    (r'(["\']?(?:password|secret|token|api_key|client_secret|app_secret|access_key|private_key)["\']?\s*:\s*)([^ \n]+)', r'\1***REDACTED***'),

    # ============================================================================
    # Legacy patterns below (for edge cases)
    # ============================================================================

    # OAuth tokens (quoted and unquoted)
    (r'(access_token|refresh_token|token)["\']?\s*[:=]\s*["\']([^"\']+?)["\']', r'\1 "***REDACTED***"'),
    (r'(access_token|refresh_token|token)\s*[:=]\s*([^\s,}\]]+)', r'\1 ***REDACTED***'),

    # API keys
    (r'(["\']?api_key["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_-]{15,})(["\']?)', r'\1***REDACTED***\3'),
    (r'(["\']?apikey["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_-]{15,})(["\']?)', r'\1***REDACTED***\3'),
    (r'(sk-[a-zA-Z0-9_-]{15,})', '***REDACTED***'),
    (r'(AIza[a-zA-Z0-9_-]{15,})', '***REDACTED***'),

    # Bearer tokens
    (r'Bearer\s+([a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+)', 'Bearer ***REDACTED***'),
    (r'Bearer\s+([a-zA-Z0-9_-]{15,})', 'Bearer ***REDACTED***'),

    # Auth type markers in brackets
    (r'\[(app_password|OAuth|oauth|XOAUTH2|xoauth2)\]', '[****]'),

    # Long base64 strings (likely tokens) - 40+ chars
    (r'([a-zA-Z0-9+/]{40,}={0,2})', '***REDACTED***'),

    # Email credentials in dict format
    (r'("email":\s*"[^"]+",\s*"app_password":\s*")([^"]+)"', r'\1***REDACTED***"'),
    (r'("app_password":\s*")([^"]+)",\s*"email":\s*"[^"]+"', r'\1***REDACTED***",'),

    # IMAP/SMTP connection strings with passwords
    (r'([a-zA-Z0-9._%+-]+@[^:\s]+):([^@\s]+)@', r'\1:***REDACTED***@'),
    (r'(["\']?(?:secret|private_key|access_token|refresh_token)["\']?\s*[:=]\s*["\'])([^"\']+?)(["\'])', r'\1***REDACTED***\3'),

    # PDF passwords (numeric patterns, 8+ digits)
    (r'([A-Z_]*(?:PDF.*PASSWORD|HSBC|VIB.*CASHBACK|VIB.*BOUNDLESS)[A-Z_]*)(\s*[:=]\s*)([0-9]{8,})', r'\1\2***REDACTED***'),

    # App secret values (hex strings, 20+ chars)
    (r'(["\']?app_secret["\']?\s*[:=]\s*["\']?)([a-fA-F0-9]{20,})(["\']?)', r'\1***REDACTED***\3'),

    # Client secret values (alphanumeric, 20+ chars)
    (r'(["\']?client_secret["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_-]{20,})(["\']?)', r'\1***REDACTED***\3'),

    # Verify token values
    (r'(["\']?verify_token["\']?\s*[:=]\s*["\']?)([a-zA-Z0-9_-]{10,})(["\']?)', r'\1***REDACTED***\3'),

    # .env file format: KEY=value
    # Match common secret key names (case-insensitive)
    (r'([A-Z_]*(?:API_KEY|SECRET|PASSWORD|TOKEN|ACCESS_KEY|PRIVATE_KEY|AUTH|CREDENTIALS|DATABASE_URL|REDIS_URL|JWT_SECRET|ENCRYPTION_KEY|CONNECTION_STRING|MONGO_URL|POSTGRES_URL|MYSQL_URL)[A-Z_]*)(\s*=\s*)([^\s]+)', r'\1\2***REDACTED***'),

    # .env with quoted values
    (r'([A-Z_]*(?:API_KEY|SECRET|PASSWORD|TOKEN|ACCESS_KEY|PRIVATE_KEY|AUTH|CREDENTIALS)[A-Z_]*)(\s*=\s*)"([^"]+)"', r'\1\2"***REDACTED***"'),

    # .env with single-quoted values
    (r"([A-Z_]*(?:API_KEY|SECRET|PASSWORD|TOKEN|ACCESS_KEY|PRIVATE_KEY|AUTH|CREDENTIALS)[A-Z_]*)(\s*=\s*)'([^']+)'", r"\1\2'***REDACTED***'"),

    # Catch-all for suspiciously long values (likely secrets) in .env format
    (r'([A-Z_]+)(\s*=\s*)([a-zA-Z0-9_-]{32,})', r'\1\2***REDACTED***'),

    # Colon format in bullet points: - Key: value
    (r'(\s*[-*]\s*[A-Z_]*(?:SECRET|PASSWORD|TOKEN|KEY|ID)[A-Z_]*:\s*)([^\n]{8,}?)(\n|$)', r'\1***REDACTED***\3'),

    # Catch values ending with ... pattern (partial redaction)
    (r'([a-zA-Z0-9_-]{8,})\.\.\.', '***REDACTED***'),
]

# Additional patterns for context-aware redaction
CONTEXT_PATTERNS = {
    'email': [
        (r'([a-zA-Z0-9._%+-]+@[^:\s]+):([^@\s]{8,})@', r'\1:***REDACTED***@'),
        (r'("app_password":\s*")([^"]{8,})"', r'\1***REDACTED***"'),
        (r'("access_token":\s*")([^"]{20,})"', r'\1***REDACTED***"'),
        (r'("refresh_token":\s*")([^"]{20,})"', r'\1***REDACTED***"'),
    ],
    'whatsapp': [
        (r'("token":\s*")([^"]{20,})"', r'\1***REDACTED***"'),
        (r'("api_key":\s*")([^"]{20,})"', r'\1***REDACTED***"'),
    ],
    'telegram': [
        (r'("bot_token":\s*")([^"]{30,})"', r'\1***REDACTED***"'),
        (r'("token":\s*")([^"]{30,})"', r'\1***REDACTED***"'),
    ],
    'zalo': [
        (r'("access_token":\s*")([^"]{30,})"', r'\1***REDACTED***"'),
        (r'("api_key":\s*")([^"]{30,})"', r'\1***REDACTED***"'),
    ],
}


def redact_sensitive_data(text: str, context: Optional[str] = None) -> str:
    """
    Redact sensitive data patterns from text.

    Args:
        text: Input text potentially containing sensitive data
        context: Optional context (e.g., 'email', 'whatsapp') for context-specific patterns

    Returns:
        Text with sensitive data redacted

    Examples:
        >>> redact_sensitive_data('access_token = "secret123"')
        'access_token = "***REDACTED***"'

        >>> redact_sensitive_data('Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9')
        'Bearer ***REDACTED***'

        >>> redact_sensitive_data('{"app_password": "mypassword"}', context='email')
        '{"app_password": "***REDACTED***"}'
    """
    if not isinstance(text, str):
        return text

    redacted = text

    # Apply general patterns
    for pattern, replacement in SENSITIVE_PATTERNS:
        redacted = re.sub(pattern, replacement, redacted, flags=re.IGNORECASE)

    # Apply context-specific patterns if provided
    if context and context in CONTEXT_PATTERNS:
        for pattern, replacement in CONTEXT_PATTERNS[context]:
            redacted = re.sub(pattern, replacement, redacted, flags=re.IGNORECASE)

    return redacted


def redact_dict(data: Any, depth: int = 0, max_depth: int = 50) -> Any:
    """
    Recursively redact sensitive data from dictionaries and lists.

    Args:
        data: Dictionary, list, or other data structure to redact
        depth: Current recursion depth (prevents infinite loops)
        max_depth: Maximum recursion depth

    Returns:
        Redacted copy of the data structure

    Examples:
        >>> redact_dict({"email": "user@example.com", "app_password": "secret"})
        {'email': 'user@example.com', 'app_password': '***REDACTED***'}

        >>> redact_dict([{"token": "abc123"}, {"data": "safe"}])
        [{'token': '***REDACTED***'}, {'data': 'safe'}]
    """
    if depth > max_depth:
        return data

    # Sensitive field names to redact (case-insensitive)
    sensitive_fields = {
        'password', 'passwd', 'app_password', 'api_key', 'apikey',
        'access_token', 'refresh_token', 'token', 'secret', 'private_key',
        'auth_token', 'session_token', 'bearer_token', 'authorization',
        'client_secret', 'client_id', 'oauth_token', 'oauth_token_secret',
    }

    if isinstance(data, dict):
        redacted = {}
        for key, value in data.items():
            # Check if key is sensitive
            key_lower = str(key).lower()
            key_is_sensitive = any(sensitive in key_lower for sensitive in sensitive_fields)

            if key_is_sensitive:
                # Redact the value
                if isinstance(value, str):
                    redacted[key] = '***REDACTED***'
                elif isinstance(value, (dict, list)):
                    # Still recurse but also redact at this level
                    redacted[key] = redact_dict(value, depth + 1, max_depth)
                    # Double-redaction for sensitive keys
                    if isinstance(redacted[key], str) and len(str(redacted[key])) > 0:
                        redacted[key] = '***REDACTED***'
                    elif isinstance(redacted[key], dict):
                        redacted[key] = {'***REDACTED***': '***REDACTED***'}
                else:
                    redacted[key] = '***REDACTED***'
            else:
                # Recurse into value
                if isinstance(value, str):
                    # Apply text redaction
                    redacted[key] = redact_sensitive_data(value)
                elif isinstance(value, (dict, list)):
                    redacted[key] = redact_dict(value, depth + 1, max_depth)
                else:
                    redacted[key] = value

        return redacted

    elif isinstance(data, list):
        return [redact_dict(item, depth + 1, max_depth) for item in data]

    elif isinstance(data, str):
        return redact_sensitive_data(data)

    else:
        return data


def sanitize_tool_result(content: Any, tool_name: str) -> Any:
    """
    Sanitize tool results with special handling for specific tool types.

    Args:
        content: Tool result content (string, dict, list, etc.)
        tool_name: Name of the tool that generated the result

    Returns:
        Sanitized copy of the tool result

    Examples:
        >>> sanitize_tool_result('{"access_token": "secret"}', 'email_gmail_send')
        '{"access_token": "***REDACTED***"}'

        >>> sanitize_tool_result('[OAuth] Connected', 'email_imap_connect')
        '[****] Connected'
    """
    # Determine context from tool name
    context = None
    tool_lower = tool_name.lower()

    if any(keyword in tool_lower for keyword in ['email', 'gmail', 'imap', 'smtp', 'mail']):
        context = 'email'
    elif 'whatsapp' in tool_lower:
        context = 'whatsapp'
    elif 'telegram' in tool_lower:
        context = 'telegram'
    elif 'zalo' in tool_lower:
        context = 'zalo'

    # Handle different content types
    if isinstance(content, str):
        # First redact sensitive data
        sanitized = redact_sensitive_data(content, context=context)

        # Special handling for auth type markers
        sanitized = re.sub(r'\[(app_password|OAuth|oauth|XOAUTH2|xoauth2)\]', '[****]', sanitized)

        return sanitized

    elif isinstance(content, (dict, list)):
        # Recursively redact dictionary/list
        return redact_dict(content)

    else:
        # For other types, try to convert to string and redact
        try:
            content_str = str(content)
            return redact_sensitive_data(content_str, context=context)
        except Exception:
            # If conversion fails, return as-is
            return content


def sanitize_log_message(message: str) -> str:
    """
    Sanitize log messages by redacting sensitive patterns.

    Args:
        message: Log message to sanitize

    Returns:
        Sanitized log message

    Examples:
        >>> sanitize_log_message('User logged in with access_token="abc123xyz"')
        'User logged in with access_token="***REDACTED***"'

        >>> sanitize_log_message('Email connection: user@host:password123@imap.host.com')
        'Email connection: user@host:***REDACTED***@imap.host.com'
    """
    if not isinstance(message, str):
        message = str(message)

    # Apply all redaction patterns
    sanitized = redact_sensitive_data(message)

    # Additional log-specific patterns
    log_patterns = [
        # Connection strings
        (r'([a-zA-Z0-9._%+-]+@[^:\s]+):([^@\s]{6,})@', r'\1:***REDACTED***@'),

        # URLs with tokens
        (r'(https?://[^\s]+)(token|key|secret|password)=([^\s&]+)', r'\1\2=***REDACTED***'),

        # Query parameters
        (r'([?&])(token|key|secret|password|access_token)=([^&\s]+)', r'\1\2=***REDACTED***'),

        # Headers in logs
        (r'(Authorization:?\s*(?:Bearer|Basic)?)\s+[^\s]+', r'\1 ***REDACTED***'),

        # Generic "with token:" patterns in logs
        (r'with token:\s*([a-zA-Z0-9_-]{15,})', 'with token: ***REDACTED***'),

        # "Using access_token:" patterns
        (r'Using access_token:\s*([a-zA-Z0-9_.-]{10,})', 'Using access_token: ***REDACTED***'),
    ]

    for pattern, replacement in log_patterns:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

    return sanitized


def sanitize_websocket_message(message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize WebSocket messages before sending to client.

    Args:
        message: WebSocket message dictionary

    Returns:
        Sanitized message dictionary

    Examples:
        >>> msg = {"type": "tool_result", "content": '{"token": "secret"}'}
        >>> sanitize_websocket_message(msg)
        {'type': 'tool_result', 'content': '{"token": "***REDACTED***"}'}
    """
    if not isinstance(message, dict):
        return message

    sanitized = {}

    for key, value in message.items():
        if key == 'content' and isinstance(value, (str, dict, list)):
            # Special handling for content field
            if 'tool' in message and isinstance(message['tool'], str):
                sanitized[key] = sanitize_tool_result(value, message['tool'])
            else:
                sanitized[key] = redact_dict(value) if isinstance(value, (dict, list)) else redact_sensitive_data(value)
        elif isinstance(value, str):
            sanitized[key] = redact_sensitive_data(value)
        elif isinstance(value, (dict, list)):
            sanitized[key] = redact_dict(value)
        else:
            sanitized[key] = value

    return sanitized


def is_safe_for_logging(data: Any) -> bool:
    """
    Check if data is safe to log (contains no sensitive patterns).

    Args:
        data: Data to check

    Returns:
        True if safe, False if contains sensitive patterns

    Examples:
        >>> is_safe_for_logging('{"user": "john"}')
        True

        >>> is_safe_for_logging('{"password": "secret123"}')
        False
    """
    # Convert to string for pattern matching
    data_str = json.dumps(data) if not isinstance(data, str) else data

    # Sensitive field names to check
    sensitive_fields = [
        'password', 'passwd', 'app_password', 'api_key', 'apikey',
        'access_token', 'refresh_token', 'secret', 'private_key',
        'auth_token', 'session_token', 'bearer_token', 'authorization',
        'client_secret', 'oauth_token', 'oauth_token_secret',
    ]

    # Check for sensitive field names
    data_lower = data_str.lower()
    for field in sensitive_fields:
        if field in data_lower:
            return False

    # Check for Bearer token pattern
    if 'bearer' in data_lower and len(data_str) > 20:
        return False

    # Check for common token patterns
    if re.search(r'token["\']?\s*[:=]\s*["\']?[a-zA-Z0-9_-]{15,}', data_str, flags=re.IGNORECASE):
        return False

    return True


def get_safe_repr(data: Any, max_length: int = 100) -> str:
    """
    Get a safe string representation of data for logging/debugging.

    Args:
        data: Data to represent
        max_length: Maximum length of output

    Returns:
        Safe string representation

    Examples:
        >>> get_safe_repr({"email": "user@host.com", "password": "secret"})
        '{"email": "user@host.com", "password": "***REDACTED***"}'
    """
    # First redact the data
    safe_data = redact_dict(data)

    # Convert to string
    try:
        safe_str = json.dumps(safe_data, ensure_ascii=False)
    except Exception:
        safe_str = str(safe_data)

    # Truncate if too long
    if len(safe_str) > max_length:
        safe_str = safe_str[:max_length] + '...'

    return safe_str


# Convenience function for one-liner redaction
def redact(data: Any) -> Any:
    """
    One-liner to redact sensitive data from any structure.

    Args:
        data: Any data structure (str, dict, list, etc.)

    Returns:
        Redacted version of the data

    Examples:
        >>> redact('Bearer secret123')
        'Bearer ***REDACTED***'

        >>> redact({"token": "abc", "user": "john"})
        {'token': '***REDACTED***', 'user': 'john'}
    """
    if isinstance(data, str):
        return redact_sensitive_data(data)
    elif isinstance(data, (dict, list)):
        return redact_dict(data)
    else:
        return data


# ---------------------------------------------------------------------------
# Path sanitization — strips absolute server paths from outbound text
# ---------------------------------------------------------------------------

class PathSanitizer:
    """Replaces absolute server paths with safe relative/generic forms.

    Computed once at import time.  Uses ``str.replace`` (no regex) for speed
    on streaming ``text_delta`` payloads.

    Replacement order (longest prefix first):
    1. Project root + "/" → "" (becomes a relative path)
    2. Home directory + "/" → "~/"
    3. "/home/<username>" → "/home/[user]"  (catch-all for remaining refs)

    Toggled by env var ``SANITIZE_PATHS`` (default: ``true``).
    """

    def __init__(self) -> None:
        self.enabled = os.getenv("SANITIZE_PATHS", "true").lower() in ("true", "1", "yes")
        if not self.enabled:
            return

        # Project root: sensitive_data_filter.py → api/utils/ → api/ → backend/
        self._project_root = str(Path(__file__).resolve().parents[2]) + "/"
        self._home_dir = str(Path.home()) + "/"
        self._username = Path.home().name
        self._home_prefix = f"/home/{self._username}"

        # Build replacement pairs, longest first
        self._replacements: list[tuple[str, str]] = []
        # Project root is always a subdirectory of home, so it's longer → first
        self._replacements.append((self._project_root, ""))
        self._replacements.append((self._home_dir, "~/"))
        # Catch-all for the username in remaining paths
        self._replacements.append((self._home_prefix, "/home/[user]"))

    def sanitize(self, text: str) -> str:
        if not self.enabled or not text:
            return text
        for old, new in self._replacements:
            text = text.replace(old, new)
        return text


# Module-level singleton — computed once at import
_path_sanitizer = PathSanitizer()


def sanitize_paths(text: str) -> str:
    """Sanitize absolute server paths from a single string."""
    return _path_sanitizer.sanitize(text)


def sanitize_event_paths(event: dict) -> dict:
    """Recursively sanitize all string values in an outbound event dict.

    Mutates the dict **in place** (these are ephemeral outbound dicts).
    Returns the same dict for convenience.
    """
    if not _path_sanitizer.enabled:
        return event
    _sanitize_dict_values(event)
    return event


def _sanitize_dict_values(obj: Any) -> None:
    """Walk a dict/list tree, replacing string leaves in place."""
    if isinstance(obj, dict):
        for key in obj:
            val = obj[key]
            if isinstance(val, str):
                obj[key] = _path_sanitizer.sanitize(val)
            elif isinstance(val, (dict, list)):
                _sanitize_dict_values(val)
    elif isinstance(obj, list):
        for i, val in enumerate(obj):
            if isinstance(val, str):
                obj[i] = _path_sanitizer.sanitize(val)
            elif isinstance(val, (dict, list)):
                _sanitize_dict_values(val)


# ---------------------------------------------------------------------------
# Sensitive data content sanitization — redacts secrets from all event fields
# ---------------------------------------------------------------------------


def sanitize_event_content(event: dict) -> dict:
    """Recursively sanitize sensitive data from all string values in an event.

    This protects against leaks in:
    - Assistant text responses (when agent summarizes .env content)
    - Tool results (already handled by normalize_tool_result_content, but double-protection)
    - Any event field that might contain sensitive data

    Args:
        event: Event dictionary to sanitize (mutated in place)

    Returns:
        The same event dict for convenience
    """
    _sanitize_dict_values_for_content(event)
    return event


def _sanitize_dict_values_for_content(obj: Any) -> None:
    """Walk a dict/list tree, applying redact_sensitive_data to all string values."""
    if isinstance(obj, dict):
        for key in obj:
            val = obj[key]
            if isinstance(val, str):
                obj[key] = redact_sensitive_data(val)
            elif isinstance(val, (dict, list)):
                _sanitize_dict_values_for_content(val)
    elif isinstance(obj, list):
        for i, val in enumerate(obj):
            if isinstance(val, str):
                obj[i] = redact_sensitive_data(val)
            elif isinstance(val, (dict, list)):
                _sanitize_dict_values_for_content(val)
