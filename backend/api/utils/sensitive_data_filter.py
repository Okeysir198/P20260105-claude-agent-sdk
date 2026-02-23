"""Pattern-based redaction of sensitive data (tokens, API keys, passwords, .env values)."""

import json
import os
import re
from pathlib import Path
from typing import Any


# Pre-compiled regex to match signed download URLs (must not be redacted)
_DOWNLOAD_URL_RE = re.compile(
    r'https?://[^\s]+/api/v1/files/dl/[A-Za-z0-9_-]+\.[a-f0-9]+'
)

# Regex patterns for sensitive data
SENSITIVE_PATTERNS = [
    # Markdown/credential list format: *Field*: value
    (r'(\*[^*]+?\*:\s*)([^\n]+?)(?:\n|$)', r'\1***REDACTED***\n'),

    # .env format: KEY=value (ALL_CAPS keys)
    (r'([A-Z_][A-Z0-9_]*=\s*)([^\s\n]+)', r'\1***REDACTED***'),

    # Credential field names (lowercase, colon separator)
    (r'(["\']?(?:password|secret|token|api_key|client_secret|app_secret|access_key|private_key)["\']?\s*:\s*)([^ \n]+)', r'\1***REDACTED***'),

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


def redact_sensitive_data(text: str, context: str | None = None) -> str:
    """Redact sensitive data patterns from text, with optional context-specific rules."""
    if not isinstance(text, str):
        return text

    redacted = text

    # Preserve download URLs before redaction (they contain base64 tokens)
    download_urls = _DOWNLOAD_URL_RE.findall(redacted)
    for i, url in enumerate(download_urls):
        redacted = redacted.replace(url, f'\x00DLURL_{i}\x00', 1)

    for pattern, replacement in SENSITIVE_PATTERNS:
        redacted = re.sub(pattern, replacement, redacted, flags=re.IGNORECASE)

    if context and context in CONTEXT_PATTERNS:
        for pattern, replacement in CONTEXT_PATTERNS[context]:
            redacted = re.sub(pattern, replacement, redacted, flags=re.IGNORECASE)

    for i, url in enumerate(download_urls):
        redacted = redacted.replace(f'\x00DLURL_{i}\x00', url)

    return redacted


def redact_dict(data: Any, depth: int = 0, max_depth: int = 50) -> Any:
    """Recursively redact sensitive data from dicts and lists."""
    if depth > max_depth:
        return data

    sensitive_fields = {
        'password', 'passwd', 'app_password', 'api_key', 'apikey',
        'access_token', 'refresh_token', 'token', 'secret', 'private_key',
        'auth_token', 'session_token', 'bearer_token', 'authorization',
        'client_secret', 'client_id', 'oauth_token', 'oauth_token_secret',
    }

    if isinstance(data, dict):
        redacted = {}
        for key, value in data.items():
            key_lower = str(key).lower()
            key_is_sensitive = any(sensitive in key_lower for sensitive in sensitive_fields)

            if key_is_sensitive:
                if isinstance(value, str):
                    redacted[key] = '***REDACTED***'
                elif isinstance(value, (dict, list)):
                    redacted[key] = redact_dict(value, depth + 1, max_depth)
                    if isinstance(redacted[key], str) and len(str(redacted[key])) > 0:
                        redacted[key] = '***REDACTED***'
                    elif isinstance(redacted[key], dict):
                        redacted[key] = {'***REDACTED***': '***REDACTED***'}
                else:
                    redacted[key] = '***REDACTED***'
            else:
                if isinstance(value, str):
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
    """Sanitize tool results with context-aware redaction based on tool type."""
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

    if isinstance(content, str):
        sanitized = redact_sensitive_data(content, context=context)
        sanitized = re.sub(r'\[(app_password|OAuth|oauth|XOAUTH2|xoauth2)\]', '[****]', sanitized)
        return sanitized

    if isinstance(content, (dict, list)):
        return redact_dict(content)

    try:
        return redact_sensitive_data(str(content), context=context)
    except Exception:
        return content


def sanitize_log_message(message: str) -> str:
    """Sanitize log messages by redacting sensitive patterns."""
    if not isinstance(message, str):
        message = str(message)

    sanitized = redact_sensitive_data(message)

    log_patterns = [
        (r'([a-zA-Z0-9._%+-]+@[^:\s]+):([^@\s]{6,})@', r'\1:***REDACTED***@'),
        (r'(https?://[^\s]+)(token|key|secret|password)=([^\s&]+)', r'\1\2=***REDACTED***'),
        (r'([?&])(token|key|secret|password|access_token)=([^&\s]+)', r'\1\2=***REDACTED***'),
        (r'(Authorization:?\s*(?:Bearer|Basic)?)\s+[^\s]+', r'\1 ***REDACTED***'),
        (r'with token:\s*([a-zA-Z0-9_-]{15,})', 'with token: ***REDACTED***'),
        (r'Using access_token:\s*([a-zA-Z0-9_.-]{10,})', 'Using access_token: ***REDACTED***'),
    ]

    for pattern, replacement in log_patterns:
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)

    return sanitized


def sanitize_websocket_message(message: dict[str, Any]) -> dict[str, Any]:
    """Sanitize WebSocket messages before sending to client."""
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
    """Check if data contains no sensitive patterns (safe to log as-is)."""
    data_str = json.dumps(data) if not isinstance(data, str) else data

    sensitive_fields = [
        'password', 'passwd', 'app_password', 'api_key', 'apikey',
        'access_token', 'refresh_token', 'secret', 'private_key',
        'auth_token', 'session_token', 'bearer_token', 'authorization',
        'client_secret', 'oauth_token', 'oauth_token_secret',
    ]

    data_lower = data_str.lower()
    for field in sensitive_fields:
        if field in data_lower:
            return False

    if 'bearer' in data_lower and len(data_str) > 20:
        return False

    if re.search(r'token["\']?\s*[:=]\s*["\']?[a-zA-Z0-9_-]{15,}', data_str, flags=re.IGNORECASE):
        return False

    return True


def get_safe_repr(data: Any, max_length: int = 100) -> str:
    """Get a redacted, truncated string representation for logging."""
    safe_data = redact_dict(data)

    try:
        safe_str = json.dumps(safe_data, ensure_ascii=False)
    except Exception:
        safe_str = str(safe_data)

    if len(safe_str) > max_length:
        safe_str = safe_str[:max_length] + '...'

    return safe_str


def redact(data: Any) -> Any:
    """Redact sensitive data from any structure (str, dict, list)."""
    if isinstance(data, str):
        return redact_sensitive_data(data)
    elif isinstance(data, (dict, list)):
        return redact_dict(data)
    else:
        return data


class PathSanitizer:
    """Replaces absolute server paths with safe relative/generic forms.

    Toggled by env var SANITIZE_PATHS (default: true).
    """

    def __init__(self) -> None:
        self.enabled = os.getenv("SANITIZE_PATHS", "true").lower() in ("true", "1", "yes")
        if not self.enabled:
            return

        self._project_root = str(Path(__file__).resolve().parents[2]) + "/"
        self._home_dir = str(Path.home()) + "/"
        self._username = Path.home().name
        self._home_prefix = f"/home/{self._username}"

        # Longest prefix first so project root (subdirectory of home) matches first
        self._replacements: list[tuple[str, str]] = [
            (self._project_root, ""),
            (self._home_dir, "~/"),
            (self._home_prefix, "/home/[user]"),
        ]

    def sanitize(self, text: str) -> str:
        if not self.enabled or not text:
            return text
        for old, new in self._replacements:
            text = text.replace(old, new)
        return text


_path_sanitizer = PathSanitizer()


def sanitize_paths(text: str) -> str:
    """Sanitize absolute server paths from a single string."""
    return _path_sanitizer.sanitize(text)


def sanitize_event_paths(event: dict) -> dict:
    """Sanitize absolute server paths from all string values in event dict (in place)."""
    if not _path_sanitizer.enabled:
        return event
    _walk_and_transform(event, _path_sanitizer.sanitize)
    return event


def sanitize_event_content(event: dict) -> dict:
    """Redact sensitive data from all string values in event dict (in place)."""
    _walk_and_transform(event, redact_sensitive_data)
    return event


def _walk_and_transform(obj: Any, transform: Any) -> None:
    """Walk a dict/list tree, applying transform to all string leaves in place."""
    if isinstance(obj, dict):
        for key in obj:
            val = obj[key]
            if isinstance(val, str):
                obj[key] = transform(val)
            elif isinstance(val, (dict, list)):
                _walk_and_transform(val, transform)
    elif isinstance(obj, list):
        for i, val in enumerate(obj):
            if isinstance(val, str):
                obj[i] = transform(val)
            elif isinstance(val, (dict, list)):
                _walk_and_transform(val, transform)
