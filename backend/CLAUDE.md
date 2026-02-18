# Backend CLAUDE.md

FastAPI server with Claude Agent SDK integration, WebSocket/SSE streaming, and per-user data isolation.

## Commands

```bash
source .venv/bin/activate
python main.py serve --port 7001    # Start API server
python main.py chat                 # Interactive CLI chat
python main.py agents               # List agents from agents.yaml
python main.py subagents             # List subagents from subagents.yaml
python main.py sessions              # List stored sessions
python main.py skills                # List skills from .claude/skills/
```

### Testing

```bash
pytest tests/ -v                          # All tests
pytest tests/test_05_auth.py -v           # Specific test file
pytest tests/ -x                          # Stop on first failure
```

Tests use `pytest-asyncio`. Fixtures in `conftest.py` provide `client`, `api_key`, `auth_headers`, `user_token`.

## Architecture

```
main.py                          # CLI entry (delegates to cli/main.py)
agents.yaml                      # Agent definitions (tools, model, system_prompt)
subagents.yaml                   # Delegation subagent definitions
config.yaml                      # Runtime configuration
core/settings.py                 # Pydantic settings (env var config)
agent/
├── core/
│   ├── storage.py              # Per-user SessionStorage + HistoryStorage
│   ├── client.py               # ConversationSession wrapper around SDK
│   ├── loader.py               # Agent/subagent YAML loading
│   └── agent_options.py        # SDK options builder (includes email MCP setup)
├── display/                    # Console output formatting
│   ├── console.py              # Rich console output
│   └── messages.py             # Message display formatting
├── tools/email/                # Email integration (optional dependency)
│   ├── gmail_tools.py          # Gmail API client + MCP tool impls
│   ├── imap_client.py          # Universal IMAP client for any provider
│   ├── mcp_server.py           # MCP server registration (contextvars for thread safety)
│   ├── credential_store.py     # Per-user OAuth/app-password storage + env-var seeding
│   └── attachment_store.py     # Downloaded email attachment storage
platforms/                       # Multi-platform messaging integration
├── base.py                     # Base platform adapter interface
├── adapters/                   # Platform-specific adapters
│   ├── telegram.py             # Telegram bot adapter
│   ├── telegram_setup.py       # Telegram webhook setup
│   ├── whatsapp.py             # WhatsApp adapter
│   └── zalo.py                 # Zalo adapter
├── worker.py                   # Async message processing worker
├── session_bridge.py           # Platform session ↔ chat session bridge
└── identity.py                 # Platform user identity mapping
api/
├── main.py                     # FastAPI app factory + lifespan
├── core/                       # Base router, shared utilities
├── db/user_database.py         # SQLite user DB (bcrypt passwords)
├── dependencies/auth.py        # get_current_user() dependency
├── middleware/auth.py           # API key middleware (X-API-Key)
├── routers/
│   ├── websocket.py            # WS /api/v1/ws/chat (main streaming)
│   ├── conversations.py        # SSE /api/v1/conversations
│   ├── sessions.py             # REST session CRUD (12 endpoints)
│   ├── auth.py                 # JWT token exchange
│   ├── user_auth.py            # Login/logout/me
│   ├── configuration.py        # GET /api/v1/config/agents
│   ├── email_auth.py           # Gmail OAuth + universal IMAP connect/disconnect
│   ├── files.py                # File upload/download
│   ├── webhooks.py             # Platform webhook handlers
│   └── health.py               # Health checks (no auth)
├── services/
│   ├── session_manager.py      # Session lifecycle + in-memory cache
│   ├── session_setup.py        # Session initialization
│   ├── token_service.py        # JWT create/decode/blacklist
│   ├── history_tracker.py      # JSONL history persistence
│   ├── search_service.py       # Full-text search with relevance
│   ├── question_manager.py     # AskUserQuestion tool handling
│   ├── message_utils.py        # Message serialization
│   ├── content_normalizer.py   # Multi-part content handling
│   ├── streaming_input.py      # Async message generator
│   └── text_extractor.py       # Text extraction from files/PDFs
├── models/                     # Pydantic request/response models
└── utils/                      # API helper utilities
cli/                            # Click CLI with login
├── commands/                   # CLI command handlers
│   ├── chat.py                 # Interactive chat command
│   ├── serve.py                # Server start command
│   ├── list.py                 # List agents/sessions/skills
│   └── handlers.py             # Shared command handlers
├── clients/                    # CLI client utilities
│   ├── ws.py                   # WebSocket client
│   ├── api.py                  # REST API client
│   ├── auth.py                 # Authentication client
│   ├── config.py               # CLI configuration
│   ├── direct.py               # Direct SDK client
│   └── event_normalizer.py     # Event stream normalization
data/{username}/                # Per-user storage (auto-created)
├── sessions.json
├── history/{session_id}.jsonl
├── email_credentials/{key}.json   # Email credentials (OAuth or app password)
└── email_attachments/             # Downloaded email attachments
tests/                          # pytest + pytest-asyncio (15 test files)
```

## Environment Variables

**Required:**
```bash
API_KEY=<strong-key>             # REST auth + JWT secret derivation
CLI_ADMIN_PASSWORD=<password>    # Admin user password
CLI_TESTER_PASSWORD=<password>   # Tester user password
```

**API provider (one required):**
```bash
ANTHROPIC_API_KEY=sk-ant-...
# OR
PROXY_BASE_URL=http://localhost:4000
# OR
ZAI_API_KEY=... + ZAI_BASE_URL=https://api.z.ai/api/anthropic
```

**Optional:**
```bash
API_HOST=0.0.0.0                        # Default: 0.0.0.0
API_PORT=7001                            # Default: 7001
CORS_ORIGINS=http://localhost:7002       # Comma-separated origins
DATA_DIR=/path/to/data                   # Default: backend/data
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
STORAGE_MAX_SESSIONS=20

# Email integration (optional — install with: uv pip install -e ".[email]")
EMAIL_GMAIL_CLIENT_ID=...               # Gmail OAuth client ID
EMAIL_GMAIL_CLIENT_SECRET=...           # Gmail OAuth client secret
EMAIL_GMAIL_REDIRECT_URI=http://localhost:7002/api/auth/callback/email/gmail
EMAIL_FRONTEND_URL=http://localhost:7002  # Redirect after OAuth

# Pre-configured email accounts (admin user only, auto-seeded at startup)
EMAIL_ACCOUNT_1_EMAIL=user@gmail.com    # Email address
EMAIL_ACCOUNT_1_PASSWORD=apppassword    # App-specific password
# EMAIL_ACCOUNT_1_IMAP_SERVER=...       # Optional (auto-detected from domain)
# EMAIL_ACCOUNT_1_IMAP_PORT=993         # Optional (default: 993)

# PDF decryption passwords (admin user only)
# PDF_PASSWORD_DEFAULT=password          # Fallback for any PDF
```

## Key Patterns

### Two-Layer Authentication

1. **API Key (middleware)** — All non-public endpoints require `X-API-Key` header. Timing-safe comparison.
2. **JWT (dependency)** — `get_current_user()` extracts username from JWT for per-user isolation.

JWT secret is **derived** from API_KEY via HMAC-SHA256, not a separate env var:
```python
secret = hmac.new(salt.encode(), API_KEY.encode(), hashlib.sha256).hexdigest()
```

### Three Token Types

| Token | Lifetime | Purpose |
|-------|----------|---------|
| `access_token` | 30 min | WebSocket/REST API access |
| `refresh_token` | 7 days | Obtain new access tokens |
| `user_identity_token` | 30 min | Login sessions (includes username/role) |

### Per-User Data Isolation

All data stored under `data/{username}/`. Username comes from JWT `username` claim.

```python
from agent.core.storage import get_user_session_storage, get_user_history_storage
session_store = get_user_session_storage(username)
history_store = get_user_history_storage(username)
```

Never hardcode paths. Never access another user's data directory.

### Agent Configuration (agents.yaml)

```yaml
agent-id-xyz123:
  name: "Display Name"
  description: "What this agent does"
  system_prompt: |
    Instructions APPENDED to default SDK prompt (not replacing)
  subagents: [reviewer]
  tools: [Read, Write, Edit, Bash, Grep, Glob]
  model: sonnet  # haiku, sonnet, opus
```

`system_prompt` is **appended**, not replaced. Default SDK prompt preserved.

### WebSocket Protocol

Connect: `WS /api/v1/ws/chat?token={jwt}&agent_id={id}&session_id={id}`

Events sent to client: `ready`, `text_delta`, `tool_use`, `tool_result`, `done`, `error`, `ask_user_question`, `plan_approval`, `compact_completed`, `cancelled`

Client messages: `{content}`, `{type: "answer", ...}`, `{type: "plan_approval", ...}`, `{type: "cancel"}`, `{type: "compact"}`

### Multi-Part Content

Messages support both string and array content:
```python
"Hello"                                    # String (legacy)
[{"type": "text", "text": "Hello"},        # Multi-part (images + text)
 {"type": "image", "source": {...}}]
```

## Gotchas

- **Token blacklist is in-memory** — Restarting server clears it. Use Redis for multi-instance production.
- **Session manager is a singleton** — `get_session_manager()` returns global instance with in-memory cache.
- **SDK client per-request** — Cannot reuse ConversationSession across HTTP requests (async context isolation).
- **AskUserQuestion has timeout** — If user doesn't respond, agent execution resumes with timeout error.
- **Public paths skip API key check** — `/`, `/health`, `/api/v1/auth/ws-token`, `/api/v1/auth/ws-token-refresh`, `/api/v1/auth/login`.
- **Default users created at startup** — `init_database()` creates admin + tester users from env vars.
- **CORS wildcard warning** — Using `"*"` for CORS_ORIGINS logs a production warning.
- **OAuth state is in-memory** — Gmail OAuth CSRF state tokens stored in-memory with 10-min TTL. Not shared across instances.
- **Email tools are optional** — `google-api-python-client` and `google-auth-oauthlib` are optional deps (`uv pip install -e ".[email]"`). Missing deps log a warning at startup.
- **Email username uses contextvars** — `mcp_server.py` uses `contextvars.ContextVar` for thread-safe per-request username. Call `set_username()` before tool execution.
- **Email accounts auto-seeded for admin only** — `EMAIL_ACCOUNT_N_*` env vars are seeded at startup for the admin user only. Other users connect via frontend Profile page. Won't overwrite existing credentials. PDF auto-decryption also admin-only.
- **Platform adapters use worker pattern** — `platforms/worker.py` processes messages async. Each adapter (Telegram, WhatsApp, Zalo) bridges to chat sessions via `session_bridge.py`.
- **Platform identity mapping** — `platforms/identity.py` maps platform user IDs to application usernames for per-user data isolation.
