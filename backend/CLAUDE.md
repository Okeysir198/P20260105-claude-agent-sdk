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
│   ├── agents.py               # Agent YAML loading
│   ├── subagents.py            # Subagent YAML loading
│   ├── yaml_utils.py           # Shared YAML parsing utilities
│   ├── hook.py                 # Agent hook definitions
│   ├── file_storage.py         # File storage utilities
│   └── agent_options.py        # SDK options builder (MCP servers, plugins, permissions)
├── tools/
│   ├── email/                  # Gmail OAuth + universal IMAP (MCP server)
│   └── media/                  # OCR, STT, TTS tools (MCP server, local services)
│       ├── config.py           # Service URLs (localhost Docker)
│       ├── helpers.py          # Shared utilities (path sanitization, error handling, session context)
│       ├── clients/            # OCR, STT, TTS HTTP clients
│       ├── ocr_tools.py        # perform_ocr tool
│       ├── stt_tools.py        # transcribe_audio, list_stt_engines
│       ├── tts_tools.py        # synthesize_speech, list_tts_engines
│       └── mcp_server.py       # MCP server + contextvars username
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
├── base.py                     # Base platform adapter interface + Platform enum
├── adapters/                   # Platform-specific adapters
│   ├── telegram.py             # Telegram bot adapter
│   ├── telegram_setup.py       # Telegram webhook setup
│   ├── whatsapp.py             # WhatsApp adapter
│   ├── zalo.py                 # Zalo adapter
│   ├── imessage.py             # iMessage adapter (via BlueBubbles)
│   └── imessage_setup.py       # iMessage webhook setup
├── worker.py                   # Async message processing worker
├── session_bridge.py           # Platform session ↔ chat session bridge
├── identity.py                 # Platform user identity mapping
├── media.py                    # Media download + processing (Telegram, WhatsApp, BlueBubbles)
└── event_formatter.py          # Agent event formatting for platform display
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
│   ├── admin.py                # Admin settings (whitelist, users)
│   └── health.py               # Health checks (no auth)
├── services/
│   ├── file_download_token.py  # Signed download tokens for platform file delivery
│   ├── session_manager.py      # Session lifecycle + in-memory cache
│   ├── session_setup.py        # Session initialization
│   ├── token_service.py        # JWT create/decode/blacklist
│   ├── history_tracker.py      # JSONL history persistence
│   ├── search_service.py       # Full-text search with relevance
│   ├── question_manager.py     # AskUserQuestion tool handling
│   ├── message_utils.py        # Message serialization
│   ├── content_normalizer.py   # Multi-part content handling
│   ├── streaming_input.py      # Async message generator
│   ├── text_extractor.py       # Text extraction from files/PDFs
│   ├── settings_service.py     # Application settings persistence
│   └── whitelist_service.py    # User whitelist management
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
tests/                          # pytest + pytest-asyncio (21 test files)
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
EMAIL_GMAIL_FULL_ACCESS_EMAILS=a@gmail.com,b@gmail.com  # Gmail addresses with full send/modify access

# Pre-configured email accounts (admin user only, auto-seeded at startup)
EMAIL_ACCOUNT_1_EMAIL=user@gmail.com    # Email address
EMAIL_ACCOUNT_1_PASSWORD=apppassword    # App-specific password
# EMAIL_ACCOUNT_1_IMAP_SERVER=...       # Optional (auto-detected from domain)
# EMAIL_ACCOUNT_1_IMAP_PORT=993         # Optional (default: 993)

# PDF decryption passwords (admin user only)
# PDF_PASSWORD_DEFAULT=password          # Fallback for any PDF

# Platform adapters (each adapter activates when its required env var is set)
TELEGRAM_BOT_TOKEN=...                   # Telegram bot token from @BotFather
TELEGRAM_WEBHOOK_SECRET=...              # Optional: webhook signature verification
WHATSAPP_PHONE_NUMBER_ID=...             # WhatsApp phone number ID
WHATSAPP_ACCESS_TOKEN=...                # WhatsApp Cloud API access token
WHATSAPP_VERIFY_TOKEN=...                # Webhook verification token
WHATSAPP_APP_SECRET=...                  # Optional: HMAC signature verification
ZALO_OA_ACCESS_TOKEN=...                 # Zalo OA access token (expires 24h)
ZALO_APP_SECRET=...                      # Optional: Zalo app secret
BLUEBUBBLES_SERVER_URL=http://mac:1234   # BlueBubbles server URL (iMessage)
BLUEBUBBLES_PASSWORD=...                 # BlueBubbles server password
BLUEBUBBLES_WEBHOOK_SECRET=...           # Optional: webhook signature verification
PLATFORM_DEFAULT_AGENT_ID=...            # Default agent for platform messages
PLATFORM_SESSION_MAX_AGE_HOURS=24        # Auto-rotate sessions after N hours

# Platform whitelist (comma-separated phone numbers, all default to 'admin')
WHATSAPP_WHITELIST=84907996550,84123456789
TELEGRAM_WHITELIST=123456789,987654321
# Custom username override (applied after whitelist):
# PLATFORM_USER_MAP_WHATSAPP_84907996550=custom_user
BACKEND_PUBLIC_URL=https://...            # Dev: your-backend-dev-url.example.com, Prod: your-backend-url.example.com

# Media services (local Docker containers - optional)
VLLM_API_KEY=...                        # OCR service API key (Ollama GLM-OCR)
DEEPGRAM_API_KEY=dummy                  # TTS service (Supertonic accepts dummy key locally)
```

### Docker

```bash
docker compose build              # Build Trung-bot image
docker compose up -d trung-bot    # Start API (host networking, port 7003)
docker compose down               # Stop containers
docker compose run --rm trung-bot-cli  # Interactive CLI
make help                         # All Make targets
make rebuild                      # Build with --no-cache
```

Uses `network_mode: host`. `restart: unless-stopped` for auto-start on reboot.

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

### Official Plugins (agents.yaml)

Plugins are loaded via the SDK `plugins` parameter, NOT by listing tool names in `allowed_tools`.
In `agents.yaml`, list plugin identifiers (e.g. `playwright@claude-plugins-official`).
`_resolve_plugins()` looks up install paths from `~/.claude/plugins/installed_plugins.json`.

```yaml
plugins:
  - playwright@claude-plugins-official
  - context7@claude-plugins-official
  - github@claude-plugins-official
```

- Dev: `claude plugin install <name>@claude-plugins-official --scope project`
- Docker: plugins installed during build (marketplace cloned + `claude plugin install`)
- Custom plugins: put in `backend/plugins/<name>/` with `.claude-plugin/plugin.json` + `.mcp.json`, reference as `{"path": "./plugins/<name>"}` in agents.yaml
- Docker is self-contained — only `./data` and `./config.yaml` mounted

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

- **Sanitization debug logging** — When sensitive data is redacted from WebSocket/platform messages, warnings are logged. Check logs for `Sanitization redacted sensitive data` to verify protection is working.
- **Token blacklist is in-memory** — Restarting server clears it. Use Redis for multi-instance production.
- **Session manager is a singleton** — `get_session_manager()` returns global instance with in-memory cache.
- **SDK client per-request** — Cannot reuse ConversationSession across HTTP requests (async context isolation).
- **AskUserQuestion has timeout** — If user doesn't respond, agent execution resumes with timeout error.
- **Public paths skip API key check** — `/`, `/health`, `/api/v1/auth/ws-token`, `/api/v1/auth/ws-token-refresh`, `/api/v1/auth/login`, `/api/v1/files/dl/*`.
- **Default users created at startup** — `init_database()` creates admin + tester users from env vars.
- **CORS wildcard warning** — Using `"*"` for CORS_ORIGINS logs a production warning.
- **OAuth state is in-memory** — Gmail OAuth CSRF state tokens stored in-memory with 10-min TTL. Not shared across instances.
- **Email tools are optional** — `google-api-python-client` and `google-auth-oauthlib` are optional deps (`uv pip install -e ".[email]"`). Missing deps log a warning at startup.
- **Email username uses contextvars** — `mcp_server.py` uses `contextvars.ContextVar` for thread-safe per-request username. Call `set_username()` before tool execution.
- **Email accounts auto-seeded for admin only** — `EMAIL_ACCOUNT_N_*` env vars are seeded at startup for the admin user only. Other users connect via frontend Profile page. Won't overwrite existing credentials. PDF auto-decryption also admin-only.
- **Platform file delivery is size-gated** — Files < 10MB sent directly via platform API; larger files (or failed sends) fall back to signed download URLs (24h expiry). See `worker._deliver_file_to_platform()`.
- **Platform adapters use worker pattern** — `platforms/worker.py` processes messages async. Each adapter (Telegram, WhatsApp, Zalo, iMessage) bridges to chat sessions via `session_bridge.py`.
- **Platform identity mapping** — `platforms/identity.py` maps platform user IDs to application usernames for per-user data isolation.
- **Platform "new session" keyword** — Users can send "new session", "new chat", "reset", or "start over" to clear their session and start fresh. Handled in `worker.py` before agent invocation.
- **iMessage requires Mac** — The iMessage adapter connects to a BlueBubbles server running on macOS. See `docs/IMESSAGE_SETUP.md`.
- **Platform setup docs** — See `docs/TELEGRAM_SETUP.md`, `docs/WHATSAPP_SETUP.md`, `docs/ZALO_SETUP.md`, `docs/IMESSAGE_SETUP.md`.
- **Media tools use contextvars** — `agent/tools/media/mcp_server.py` uses `contextvars.ContextVar` for thread-safe per-request username (same pattern as email tools). Call `set_media_tools_username()` before tool execution via `agent_options.py`.
- **Media services are local Docker** — OCR (port 18013), STT (18050/18052), TTS (18030/18033/18034). All run on localhost. Services must be running before tools can be used.
- **Media tools primary engines** — Whisper V3 Turbo (STT, 99 languages, auto-detect), Supertonic v1_1 (TTS, 21 voices, MP3), Kokoro (TTS, lightweight multi-language), Chatterbox Turbo (TTS, voice cloning with reference audio).
- **Plugins ≠ tool whitelisting** — Do NOT add `mcp__plugin_*` tool names to `allowed_tools` in agents.yaml. Load plugins via the `plugins` parameter instead; they auto-register their tools.
- **Plugin install scope** — `claude plugin install --scope project` writes to `.claude/settings.json` in the current directory. Install from `backend/` for backend plugins.
