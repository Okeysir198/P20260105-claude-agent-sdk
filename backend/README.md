# Claude Agent SDK Backend

FastAPI server with user authentication, WebSocket streaming, and per-user data isolation.

## Quick Start

```bash
# Install dependencies (using uv)
uv sync && source .venv/bin/activate

# Or using pip
pip install -e .

# Configure environment
cp .env.example .env
# Edit .env to set: ANTHROPIC_API_KEY, API_KEY, CLI_ADMIN_PASSWORD, CLI_TESTER_PASSWORD

# Start server
python main.py serve --port 7001
```

## CLI Commands

```bash
python main.py serve              # Start server (default port 7001)
python main.py chat               # Interactive chat (prompts for password)
python main.py agents             # List available agents
python main.py subagents          # List available subagents
python main.py skills             # List available skills
python main.py sessions           # List conversation sessions
```

## Environment Variables

```bash
# Required
ANTHROPICIC_API_KEY=sk-ant-...
API_KEY=your-api-key              # For REST auth + JWT derivation

# User credentials (for CLI and tests)
CLI_USERNAME=admin
CLI_ADMIN_PASSWORD=your-password        # Admin user password
CLI_TESTER_PASSWORD=your-password       # Tester user password

# Optional
CORS_ORIGINS=https://your-frontend.com
API_HOST=0.0.0.0
API_PORT=7001
```

## Authentication

### Two-Layer Authentication

1. **API Key Authentication** - Required for all REST endpoints via `X-API-Key` header
2. **User Authentication** - SQLite-based authentication returning JWT tokens with `user_identity` type

### JWT Token Types

| Token Type | Purpose | Expires In | Contains |
|------------|---------|------------|----------|
| **Access Token** | WebSocket authentication | 30 minutes | `sub` (user_id), `type: "access"` |
| **Refresh Token** | Get new access tokens | 7 days | `sub` (user_id), `type: "refresh"`, `jti` |
| **User Identity Token** | User login sessions | 30 minutes | `sub` (user_id), `type: "user_identity"`, `username`, `role` |

### Token Refresh Flow

1. **Initial Login:** Client → `POST /api/v1/auth/login` → Server returns `{token, refresh_token, user}`
2. **Use Token:** REST requests with `X-User-Token` header, WebSocket with `?token=` query param
3. **Refresh:** Client → `POST /api/v1/auth/ws-token-refresh` → Server returns new tokens

### WebSocket Authentication

WebSocket requires JWT with `user_identity` type (includes username for per-user storage):

```
wss://host/api/v1/ws/chat?token=<user_identity_jwt>&agent_id=xxx&session_id=xxx
```

Query parameters:
- `token` (required) - JWT with user_identity type
- `agent_id` (optional) - Agent to use
- `session_id` (optional) - Session to resume

### Default Users

Created automatically in `data/users.db`:

| Username | Role | Password Source |
|----------|------|-----------------|
| admin | admin | `CLI_ADMIN_PASSWORD` env var |
| tester | user | `CLI_TESTER_PASSWORD` env var |

## API Endpoints

### Health Endpoints (No authentication)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Root health check |
| GET | `/health` | Health check with service name |

### User Authentication (API Key required)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/login` | User login with username/password |
| POST | `/api/v1/auth/logout` | User logout (for audit) |
| GET | `/api/v1/auth/me` | Get current authenticated user info |

**Login Request:** `{"username": "admin", "password": "your-password"}`

**Login Response:** `{success, token, refresh_token, user: {id, username, full_name, role}}`

### WebSocket Token Management (API Key required)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/ws-token` | Exchange API key for WebSocket tokens |
| POST | `/api/v1/auth/ws-token-refresh` | Refresh access token using refresh token |

**ws-token Request:** `{"api_key": "your-api-key"}`

**ws-token-refresh Request:** `{"refresh_token": "your_refresh_token"}`

**Response:** `{access_token, refresh_token, token_type: "bearer", expires_in: 1800, user_id}`

### Sessions (API Key + User JWT required)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/sessions` | Create a new session |
| GET | `/api/v1/sessions` | List all sessions (newest first) |
| GET | `/api/v1/sessions/{id}/history` | Get session conversation history |
| GET | `/api/v1/sessions/search` | Search sessions by content |
| PATCH | `/api/v1/sessions/{id}` | Update session properties (name) |
| DELETE | `/api/v1/sessions/{id}` | Delete a session |
| POST | `/api/v1/sessions/{id}/close` | Close a session (keep in history) |
| POST | `/api/v1/sessions/{id}/resume` | Resume a specific session by ID |
| POST | `/api/v1/sessions/batch-delete` | Delete multiple sessions |
| POST | `/api/v1/sessions/resume` | Resume previous session |
| WS | `/api/v1/ws/chat` | WebSocket chat connection |

**Session Response:** `{session_id, name, first_message, created_at, turn_count, agent_id}`

**Search Query Params:** `query` (search term), `max_results` (default 20, max 100)

**Search Response:** `{results: [{session_id, name, relevance_score, match_count, snippet}], total_count, query}`

**Search Capabilities:**
- Searches all message types: `user`, `assistant`, `tool_use`, `tool_result`
- Case-insensitive matching
- Relevance-based ranking
- Contextual snippets showing search term in context

### Conversations (API Key + User JWT required)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/conversations` | Create new conversation with SSE streaming |
| POST | `/api/v1/conversations/{session_id}/stream` | Send message in existing session with SSE streaming |

**Request:** `{content: "message", agent_id: "agent-id"}`

**SSE Events:** `session_id`, `sdk_session_id`, `text_delta`, `done`

### Configuration (API Key required)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/config/agents` | List available agents |

**Response:** `{agents: [{agent_id, name, description, model}]}`

## WebSocket Protocol

### Connection Flow

1. Client connects: `wss://host/api/v1/ws/chat?token=jwt&agent_id=xxx`
2. Server sends: `{"type": "ready"}`
3. Client sends: `{"content": "Hello!"}`
4. Server streams: `session_id`, `text_delta` (multiple), `tool_use`, `tool_result`, `done`

### AskUserQuestion Flow

1. Server asks: `{"type": "ask_user_question", "question_id": "q1", "questions": [...]}`
2. Client answers: `{"type": "user_answer", "question_id": "q1", "answers": {...}}`
3. Server continues: `text_delta`, `done`

### Message Types

| Type | Direction | Description |
|------|-----------|-------------|
| `ready` | Server→Client | Connection ready |
| `session_id` | Server→Client | Session ID for this connection |
| `text_delta` | Server→Client | Streaming text fragment |
| `tool_use` | Server→Client | Tool being invoked |
| `tool_result` | Server→Client | Tool execution result |
| `done` | Server→Client | Response complete |
| `error` | Server→Client | Error occurred |
| `ask_user_question` | Server→Client | Question for user |
| `user_answer` | Client→Server | User's answer |
| `cancel_request` | Client→Server | Cancel streaming response |
| `cancelled` | Server→Client | Response cancelled |
| `compact_request` | Client→Server | Request context compaction |
| `compact_started` | Server→Client | Compaction started |
| `compact_completed` | Server→Client | Compaction completed |

## Architecture

### Data Structure

```
data/
├── users.db              # SQLite user database
├── admin/                # Admin's data
│   ├── sessions.json     # Session metadata
│   └── history/          # Conversation history
│       └── {session_id}.jsonl
└── tester/               # Tester's data
    └── ...
```

### Codebase Structure

```
backend/
├── main.py                    # CLI entry point
├── agents.yaml                # Agent definitions
├── subagents.yaml             # Delegation subagents
├── pyproject.toml             # Project dependencies
├── api/
│   ├── core/
│   │   └── errors.py         # Custom exceptions
│   ├── config.py              # Configuration (API key, CORS)
│   ├── dependencies/
│   │   └── auth.py           # Auth dependencies
│   ├── middleware/
│   │   └── jwt_auth.py       # JWT authentication middleware
│   ├── models/                # Pydantic models
│   │   ├── auth.py           # Auth models
│   │   ├── requests.py       # Request models
│   │   ├── responses.py      # Response models
│   │   └── user_auth.py      # User auth models
│   ├── routers/
│   │   ├── auth.py           # JWT token endpoints
│   │   ├── configuration.py  # Agent listing
│   │   ├── conversations.py  # SSE streaming
│   │   ├── health.py         # Health checks
│   │   ├── sessions.py       # Session management
│   │   ├── user_auth.py      # User login/logout
│   │   └── websocket.py      # WebSocket chat
│   ├── services/
│   │   ├── content_normalizer.py  # Message formatting
│   │   ├── history_service.py     # History tracking
│   │   ├── message_utils.py       # Message utilities
│   │   ├── search_service.py      # Session search
│   │   ├── session_service.py     # Session manager
│   │   └── token_service.py       # JWT token management
│   └── db/
│       └── user_database.py   # SQLite user management
├── agent/
│   ├── core/
│   │   ├── agent_options.py  # Agent configuration
│   │   └── storage.py        # Per-user file storage
│   └── tools/                # Tool implementations
├── cli/                      # Click CLI
│   └── commands/
│       ├── list.py           # List commands
│       └── serve.py          # Server command
└── tests/                    # Test suite
```

### Session Persistence

**Primary: WebSocket Persistence**
- SessionManager's in-memory cache maintains state
- SDK session created on connection
- Multi-turn conversations work seamlessly

**Fallback: REST API**
- Create session via `POST /api/v1/sessions`
- Client stores session_id locally
- Send messages via `POST /api/v1/conversations/{session_id}/stream`
- Backend resolves pending_id to SDK session ID on first message

### Per-User Data Isolation

All session data isolated per-user in filesystem:
- `backend/data/{username}/sessions.json` - Session metadata
- `backend/data/{username}/history/{session_id}.jsonl` - Conversation history

### Session Resolution Order

1. **In-Memory Cache** - Active WebSocket sessions
2. **Session Storage** - Persistent session metadata
3. **History Storage** - Conversation history

Ensures sessions can be resumed after server restart.

## Testing

```bash
# Set CLI_ADMIN_PASSWORD and CLI_TESTER_PASSWORD in .env first
pytest tests/                    # Run all tests
pytest tests/test_09_history_tracker.py -v  # Run specific test file
pytest tests/ -x                 # Stop on first failure
```

**65 tests** across 11 test files covering history tracking, content normalization, streaming, storage, auth, session search, and WebSocket timing.

## SDK Message Types and History Persistence

### SDK Message Types

The Claude Agent SDK emits typed Python dataclass messages during conversation streaming:

```
Message = UserMessage | AssistantMessage | SystemMessage | ResultMessage | StreamEvent
```

| SDK Type | Fields | When Emitted |
|----------|--------|--------------|
| **UserMessage** | `content: str \| list[ContentBlock]`, `uuid`, `parent_tool_use_id` | User submits a prompt, or after tool execution (contains ToolResultBlocks) |
| **AssistantMessage** | `content: list[ContentBlock]`, `model: str`, `parent_tool_use_id`, `error` | Assistant completes a response turn |
| **SystemMessage** | `subtype: str`, `data: dict` | System-level events (e.g., session init) |
| **ResultMessage** | `subtype`, `duration_ms`, `duration_api_ms`, `is_error`, `num_turns`, `session_id`, `total_cost_usd`, `usage`, `result` | Conversation ends |
| **StreamEvent** | `uuid`, `session_id`, `event: dict`, `parent_tool_use_id` | During streaming (text_delta, partial results) |

**AssistantMessage.error** is one of: `authentication_failed`, `billing_error`, `rate_limit`, `invalid_request`, `server_error`, `unknown`.

### Content Block Types

AssistantMessage and UserMessage carry content as a list of typed blocks:

| Block Type | Fields | Purpose |
|------------|--------|---------|
| **TextBlock** | `text: str` | Assistant text response |
| **ThinkingBlock** | `thinking: str`, `signature: str` | Extended thinking (internal reasoning) |
| **ToolUseBlock** | `id: str`, `name: str`, `input: dict` | Tool invocation request |
| **ToolResultBlock** | `tool_use_id: str`, `content: str \| list \| None`, `is_error: bool` | Tool execution result |

### Event Types (WebSocket/SSE)

Events sent between server and client during streaming:

| Event Type | Direction | Persisted to History | Description |
|------------|-----------|---------------------|-------------|
| `session_id` | Server→Client | No (control) | Session initialization |
| `ready` | Server→Client | No (control) | Connection ready |
| `text_delta` | Server→Client | Yes → accumulated as `assistant` | Streaming text chunk |
| `tool_use` | Server→Client | Yes → `tool_use` role | Tool invocation |
| `tool_result` | Server→Client | Yes → `tool_result` role | Tool execution result |
| `thinking` | Server→Client | Yes → `assistant` (block_type=thinking) | Extended thinking |
| `assistant_text` | Server→Client | No (display only) | Canonical assistant text |
| `done` | Server→Client | Yes → `system` (event_type=result) | Turn complete with cost/usage |
| `error` | Server→Client | Yes → `system` (event_type=error) | Error occurred |
| `ask_user_question` | Server→Client | No | Interactive question for user |
| `user_answer` | Client→Server | Yes → `tool_result` role | User's answer |
| `cancel_request` | Client→Server | No (control) | Cancel current operation |
| `cancelled` | Server→Client | Yes → `assistant` (cancelled=true) | Operation cancelled |
| `compact_request` | Client→Server | No (control) | Request context compaction |
| `compact_started` | Server→Client | No (control) | Compaction started |
| `compact_completed` | Server→Client | No (control) | Compaction finished |

### History JSONL Format

Each session's history is stored in `data/{username}/history/{session_id}.jsonl`. Each line is a JSON object:

```json
{
  "role": "user|assistant|tool_use|tool_result|system|event",
  "content": "string or list of content blocks",
  "timestamp": "2026-02-12T04:00:00.000Z",
  "message_id": "uuid or null",
  "tool_name": "Bash|Read|Write|... or null",
  "tool_use_id": "tool invocation ID or null",
  "is_error": false,
  "metadata": {}
}
```

**Message Roles:**

| Role | Purpose | Content Format |
|------|---------|----------------|
| `user` | User message | String or `[{type, text}, {type, source}]` for multi-part |
| `assistant` | Assistant text response | Plain text (cleaned of proxy artifacts) |
| `tool_use` | Tool invocation | JSON-encoded input dict. `metadata.input` has structured dict |
| `tool_result` | Tool execution output | Result string. `tool_use_id` references the tool_use |
| `system` | System events | JSON-encoded data. `metadata.event_type` identifies the event |
| `event` | Unrecognized SDK events | JSON-encoded data (catch-all for future types) |

### SDK Message → History Mapping

#### AssistantMessage (typed path)

An AssistantMessage with mixed content blocks produces **multiple ordered JSONL entries**:

```
AssistantMessage(content=[TextBlock, ToolUseBlock, TextBlock, ToolUseBlock], model="claude-opus-4-6")
```

Produces this history (text flushed BEFORE each tool call):

```jsonl
{"role": "assistant", "content": "I'll read the file.", "metadata": {"model": "claude-opus-4-6"}}
{"role": "tool_use", "content": "{\"path\": \"a.txt\"}", "tool_name": "Read", "tool_use_id": "tu1", "metadata": {"input": {"path": "a.txt"}, "model": "claude-opus-4-6"}}
{"role": "assistant", "content": "Now I'll edit it.", "metadata": {"model": "claude-opus-4-6"}}
{"role": "tool_use", "content": "{\"path\": \"a.txt\"}", "tool_name": "Edit", "tool_use_id": "tu2", "metadata": {"input": {"path": "a.txt"}, "model": "claude-opus-4-6"}}
```

Trailing text after the last tool call is saved when `finalize_assistant_response()` is called at turn end.

**ThinkingBlock** → `{"role": "assistant", "metadata": {"block_type": "thinking", "model": "..."}}`

**AssistantMessage.error** → `{"role": "system", "metadata": {"event_type": "assistant_error", "error": "rate_limit"}}`

#### UserMessage (typed path)

- **String content** → `{"role": "user", "content": "Hello"}`
- **ToolResultBlock** → `{"role": "tool_result", "tool_use_id": "tu1", "content": "file contents"}`
- **TextBlock** → `{"role": "user", "content": "user text"}`

#### StreamEvent (dict path via process_event)

| Event | History Action |
|-------|---------------|
| `text_delta` | Accumulated in buffer, saved as `assistant` on flush |
| `tool_use` | **Flush text first**, then save as `tool_use` |
| `tool_result` | Save as `tool_result` |
| `done` | Flush remaining text, save ResultMessage as `system` |
| `cancelled` | Flush text with `{"cancelled": true}` metadata |
| `user_answer` | Save as `tool_result` |
| Unrecognized | Save as `event` role with `event_type` metadata |

#### ResultMessage

```jsonl
{"role": "system", "content": "{\"num_turns\": 3, \"total_cost_usd\": 0.015, ...}", "metadata": {"event_type": "result", "num_turns": 3, "total_cost_usd": 0.015, ...}}
```

### Two History Paths

The backend has two paths for saving history, used depending on the SDK message type:

| Path | Used For | Method |
|------|----------|--------|
| **Typed path** | `AssistantMessage`, `UserMessage` | `save_from_assistant_message()`, `save_from_user_message()` — uses block attributes directly, captures model/error metadata |
| **Dict path** | `StreamEvent`, `ResultMessage`, other events | `process_event()` — routes by event_type string, handles text accumulation and flushing |

The typed path is primary for WebSocket connections. The dict path handles SSE streaming and legacy events. Both paths maintain correct temporal ordering by flushing accumulated text before tool_use events.

### Key Implementation: `api/services/history_tracker.py`

```python
# Typed path (WebSocket - AssistantMessage/UserMessage)
tracker.save_from_assistant_message(msg)  # Flushes text before each ToolUseBlock
tracker.save_from_user_message(msg)       # Handles TextBlock + ToolResultBlock

# Dict path (SSE - StreamEvent/ResultMessage)
tracker.process_event(event_type, data)   # Routes by EventType, auto-flushes text

# Manual finalization (called at turn end)
tracker.finalize_assistant_response()     # Saves any remaining buffered text
```

## Docker

```bash
make build && make up
```
