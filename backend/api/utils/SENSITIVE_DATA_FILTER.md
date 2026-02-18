# Sensitive Data Filter

## Overview

`sensitive_data_filter.py` provides pattern-based redaction for protecting sensitive information across logs, tool results, and WebSocket output.

## Key Functions

| Function | Purpose |
|----------|---------|
| `redact(data)` | Auto-detect input type and apply redaction |
| `redact_sensitive_data(text, context)` | Redact sensitive patterns from text strings |
| `redact_dict(data)` | Recursively redact dictionaries and lists |
| `sanitize_tool_result(content, tool_name)` | Context-aware sanitization for tool results |
| `sanitize_log_message(message)` | Sanitize log messages (URLs, tokens, connection strings) |
| `sanitize_websocket_message(message)` | Sanitize WebSocket messages before sending to clients |
| `is_safe_for_logging(data)` | Check if data contains sensitive patterns |
| `get_safe_repr(data, max_length)` | Safe string representation for debugging |

## Supported Patterns

- **OAuth tokens**: `access_token`, `refresh_token` (quoted/unquoted formats)
- **API keys**: `api_key`, `sk-...`, `AIza...` (15+ char values)
- **Passwords**: `password`, `passwd`, `app_password`
- **Bearer tokens**: JWT format, long tokens (15+ chars)
- **Auth markers**: `[app_password]`, `[OAuth]`, `[XOAUTH2]`
- **Base64 strings**: 40+ character base64-encoded strings
- **Connection strings**: IMAP/SMTP credentials, URL parameters, Authorization headers

## Usage

```python
from api.utils.sensitive_data_filter import redact, redact_dict, sanitize_log_message

redact('password: secret123')  # => 'password: ***REDACTED***'

redact_dict({
    "email": "user@gmail.com",
    "app_password": "secret"
})  # => {'email': 'user@gmail.com', 'app_password': '***REDACTED***'}

sanitize_log_message('Connecting: user@host:password@imap.host.com')
# => 'Connecting: user@host:***REDACTED***@imap.host.com'
```

## Integration Points

Used in:
- WebSocket message pipeline (`api/routers/websocket.py`)
- History tracker (`api/services/history_tracker.py`)
- Content normalizer (`api/services/content_normalizer.py`)
- Email auth router error messages

## Tests

```bash
pytest tests/test_sensitive_data_filter.py -v
```
