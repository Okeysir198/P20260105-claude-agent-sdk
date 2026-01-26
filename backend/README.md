# Claude Agent SDK Backend

FastAPI server providing REST API, WebSocket, and SSE endpoints for the Claude Agent SDK chat application.

## Quick Start

```bash
# Install dependencies
uv sync && source .venv/bin/activate

# Configure environment
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY and API_KEY

# Start server
python main.py serve --port 7001
```

## Authentication

The backend supports two authentication methods:
- **API Key** - For REST API endpoints (via `X-API-Key` header)
- **JWT** - For WebSocket connections (via `token` query parameter)

### Security Architecture

The frontend uses a proxy architecture to protect API keys:

```
REST API:
  Browser ──────> Frontend /api/proxy/* ──────> Backend /api/v1/*
                     (adds X-API-Key)

WebSocket:
  Browser ──────> Frontend /api/auth/token ──────> JWT created locally
    │                 (derives JWT_SECRET           (no backend call)
    │                  from API_KEY)
    └───────────> wss://backend/ws/chat?token=JWT (DIRECT connection)
```

### JWT Secret Derivation

The JWT secret is **derived** from `API_KEY` using HMAC-SHA256 - no separate `JWT_SECRET_KEY` needed:

```python
# Both frontend and backend use the same derivation:
salt = b"claude-agent-sdk-jwt-v1"
jwt_secret = hmac.new(salt, api_key.encode(), hashlib.sha256).hexdigest()
```

This approach ensures:
- Only one secret (API_KEY) needs to be configured
- JWT secret cannot be used to recover the API_KEY
- Frontend and backend use identical JWT secrets

### Setup

1. Generate secure key:
   ```bash
   openssl rand -hex 32  # For API_KEY
   ```

2. Add to `.env`:
   ```
   API_KEY=your-api-key
   ```

3. Restart the server

**Note:** No separate `JWT_SECRET_KEY` is needed - it's derived automatically from `API_KEY`.

### Auth Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/ws-token` | API Key | Exchange API key for WebSocket JWT |
| POST | `/auth/ws-token-refresh` | JWT | Refresh WebSocket JWT |

**Get WebSocket Token:**
```bash
POST /auth/ws-token
Headers: X-API-Key: your-api-key
Response: {
  "access_token": "jwt...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Refresh Token:**
```bash
POST /auth/ws-token-refresh
Headers: Authorization: Bearer <jwt_token>
Response: {
  "access_token": "new-jwt...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**WebSocket Connection:**
```
wss://host/api/v1/ws/chat?token=<jwt_token>&agent_id=xxx
```

### REST API Authentication

All REST endpoints (except `/health` and `/auth/*`) require API key:
```bash
GET /api/v1/sessions
Headers: X-API-Key: your-api-key
```

## API Endpoints

### Health Check

```bash
GET /health
# Response: {"status": "ok", "service": "agent-sdk-api"}
```

### Sessions

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/sessions` | Yes | List all sessions |
| GET | `/api/v1/sessions/{id}/history` | Yes | Get message history |
| DELETE | `/api/v1/sessions/{id}` | Yes | Delete session + history |
| POST | `/api/v1/sessions/{id}/close` | Yes | Close session (keep history) |
| POST | `/api/v1/sessions/{id}/resume` | Yes | Resume session context |

### Conversations (SSE)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/conversations` | Yes | Create conversation and stream response |
| POST | `/api/v1/conversations/{id}/stream` | Yes | Send follow-up message |

### Configuration

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/config/agents` | Yes | List available agents and their IDs |

### WebSocket

**Endpoint:** `/api/v1/ws/chat`

**Connection Flow Diagram:**

```
+-------------+                    +-------------+                    +-------------+
|   Client    |                    |   Backend   |                    |  Claude SDK |
|  (Browser)  |                    |  (FastAPI)  |                    |   Agent     |
+------+------                    +------+------+                    +------+------+
       |                                  |                                  |
       |  1. WebSocket Connect            │                                  |
       |  (wss://host/ws/chat?token=JWT) │                                  |
       |--------------------------------->|                                  |
       |                                  |                                  |
       |  2. Validate JWT Token           │                                  |
       |<---------------------------------|                                  |
       |                                  |                                  |
       |  3. Accept Connection            │                                  |
       |<---------------------------------|                                  |
       |                                  |                                  |
       |  4. Ready Event                  │                                  |
       |<---------------------------------|                                  |
       |  {"type": "ready"}               │                                  |
       |                                  |                                  |
       |  5. User Message                 │                                  |
       |  {"content": "Hello"}            │                                  |
       |--------------------------------->|                                  |
       |                                  |  6. Forward to SDK               │
       |                                  |--------------------------------->|
       |                                  |                                  |
       │  7. Stream Response              │                                  |
       │<---------------------------------|  8. Process & Generate          │
       │  {"type": "text_delta", ...}     |<---------------------------------|
       │  {"type": "text_delta", ...}     │                                  |
       │  {"type": "tool_use", ...}       │                                  |
       │  {"type": "tool_result", ...}    │                                  |
       │  {"type": "done", ...}           │                                  |
       │                                  │                                  │
       │  9. Next Message (Turn 2)        │                                  │
       │  {"content": "..."}              │                                  │
       │--------------------------------->|                                  │
       │                                  │  (Connection persists)            │
       │  10. Stream Response             │<---------------------------------|
       │<---------------------------------|                                  │
       │                                  │                                  │
       │  ... Repeat Turns ...            │                                  │
       │                                  │                                  │
       │  11. Disconnect                  │                                  │
       │  X Close WebSocket               │                                  │
       │--------------------------------->|                                  │
       │                                  │  Cleanup & Close                 │
       │                                  |--------------------------------->|
```

**Query Parameters:**
- `token` (required) - JWT token from `/auth/ws-token`
- `agent_id` (optional) - Agent to use for new sessions
- `session_id` (optional) - Existing session to resume

**Protocol:**

```
# Connection established
Server → {"type": "ready"}
Server → {"type": "ready", "session_id": "...", "resumed": true, "turn_count": 5}  # if resuming

# Client sends message
Client → {"content": "Hello!"}

# Server streams response
Server → {"type": "session_id", "session_id": "uuid"}
Server → {"type": "text_delta", "text": "Hi there!"}
Server → {"type": "tool_use", "name": "Read", "input": {...}}
Server → {"type": "tool_result", "content": "...", "tool_use_id": "...", "is_error": false}

# AskUserQuestion interaction
Server → {"type": "ask_user_question", "question_id": "...", "questions": [...], "timeout": 60}
Client → {"type": "user_answer", "question_id": "...", "answers": {...}}
Server → {"type": "question_answered", "question_id": "..."}
```

**AskUserQuestion Flow Diagram:**

```
+-------------+                    +-------------+                    +-------------+
|   Client    |                    |   Backend   |                    |  Claude SDK |
|  (Browser)  |                    |  (FastAPI)  |                    |   Agent     |
+------+------                    +------+------+                    +------+------+
       |                                  |                                  |
       |  Processing query...             |                                  |
       |<---------------------------------|  Agent processing               |
       |  {"type": "text_delta", ...}     |<---------------------------------|
       |                                  |                                  |
       |  Agent needs user input!         |                                  |
       |<---------------------------------|  AskUserQuestion triggered       |
       |  {"type": "ask_user_question",   |<---------------------------------|
       |   "question_id": "uuid",         |                                  |
       |   "questions": [...],            |                                  |
       |   "timeout": 60}                 |                                  |
       |                                  |                                  |
       |  [SHOW MODAL TO USER]            |                                  |
       |  +-------------------------+     |                                  |
       |  | Question: Choose option |     |                                  |
       |  | O Option A              |     |                                  |
       |  | O Option B              |     |                                  |
       |  | O Option C              |     |                                  |
       |  +-------------------------+     |                                  |
       |                                  |                                  |
       |  User selects option             |                                  |
       |                                  |                                  |
       |  Send user answer                |                                  |
       |--------------------------------->|                                  |
       |  {"type": "user_answer",         |                                  |
       |   "question_id": "uuid",         |                                  |
       |   "answers": {...}}              |                                  |
       |                                  |  Resume agent with answer        |
       |                                  |--------------------------------->|
       |                                  |  PermissionResultAllow           |
       |  Question processed              |<---------------------------------|
       |<---------------------------------|                                  |
       |  {"type": "question_answered",   |                                  |
       |   "question_id": "uuid"}         |                                  |
       |                                  |                                  |
       │  Continue response               |                                  |
       |<---------------------------------|  Agent continues                 |
       │  {"type": "text_delta", ...}     |<---------------------------------|
       │  {"type": "done", ...}           │                                  |
       │                                  |                                  |
```

**Additional Protocol Examples:**

```
# Turn complete
Server → {"type": "done", "turn_count": 1}

# Errors
Server → {"type": "error", "error": "message"}
```

**WebSocket Close Codes:**

| Code | Name | Description |
|------|------|-------------|
| 1000 | NORMAL | Normal closure |
| 1008 | POLICY_VIOLATION | Invalid or missing JWT token |
| 1003 | SESSION_NOT_FOUND | Session to resume not found |
| 1011 | INTERNAL_ERROR | Failed to initialize SDK client or JWT not configured |

**Event Types:**

| Type | Direction | Description |
|------|-----------|-------------|
| `ready` | Server→Client | Connection ready, includes session info if resuming |
| `session_id` | Server→Client | SDK session identifier (first message only) |
| `text_delta` | Server→Client | Streaming text chunk |
| `tool_use` | Server→Client | Tool invocation details |
| `tool_result` | Server→Client | Tool execution result |
| `ask_user_question` | Server→Client | Interactive question (requires user_answer) |
| `question_answered` | Server→Client | Question processed acknowledgment |
| `done` | Server→Client | Response complete, includes turn_count |
| `error` | Server→Client | Error occurred |
| `content` | Client→Server | User message content |
| `user_answer` | Client→Server | Answer to ask_user_question |

## SSE Protocol

**SSE Flow Diagram:**

```
+-------------+                    +-------------+                    +-------------+
|   Client    |                    |   Backend   |                    |  Claude SDK |
|  (Browser)  |                    |  (FastAPI)  |                    |   Agent     |
+------+------                    +------+------+                    +------+------+
       |                                  |                                  |
       |  1. HTTP POST                    │                                  |
       |  /api/v1/conversations           │                                  |
       |  Headers: X-API-Key              │                                  |
       |  Body: {"content": "Hello"}      │                                  |
       |--------------------------------->|                                  |
       |                                  |                                  |
       |                                  |  2. Get/Create Session            │
       |                                  |  3. Create SDK Client             │
       |                                  |--------------------------------->|
       |                                  |                                  |
       │  4. SSE Stream Open              │                                  │
       │<---------------------------------|                                  │
       │  Content-Type: text/event-stream │                                  │
       │                                  │                                  │
       │  5. Send Query                   │                                  │
       │                                  |--------------------------------->|
       │                                  │                                  │
       │  6. Stream Events                │                                  │
       │<---------------------------------|  7. Process & Generate           │
       │  event: session_id               │<---------------------------------|
       │  data: {"session_id": "..."}     │                                  │
       │                                  │                                  │
       │  event: text_delta               │                                  │
       │  data: {"text": "Hello"}         │                                  │
       │                                  │                                  │
       │  event: text_delta               │                                  │
       │  data: {"text": " there!"}       │                                  │
       │                                  │                                  │
       │  event: done                     │                                  │
       │  data: {"turn_count": 1}         │                                  │
       │                                  │                                  │
       │  8. Stream Closes                │                                  │
       │  X Connection ends               │                                  │
       │                                  │                                  │
       │  ... For next message, new HTTP request ...                       │
       │                                  │                                  │
       │  9. HTTP POST (Follow-up)        │                                  │
       │  /api/v1/conversations/{id}/stream                                  │
       │--------------------------------->|                                  │
       │                                  │  Resume session                  │
       │  10. Stream Events               │<---------------------------------|
       │<---------------------------------|                                  │
       │  event: session_id               │                                  │
       │  data: {"found_in_cache": true}  │                                  │
       │  ...                             │                                  │
```

**Create Conversation:**

```bash
POST /api/v1/conversations
Headers: Authorization: Bearer <access_token>
Body: {"content": "Hello", "agent_id": "OPTIONAL_ID"}

# Response streams SSE events:
event: session_id
data: {"session_id": "uuid", "found_in_cache": false}

event: text_delta
data: {"text": "Hello"}

event: sdk_session_id
data: {"sdk_session_id": "sdk-uuid"}

event: text_delta
data: {"text": " there!"}

event: done
data: {"turn_count": 1}
```

**Follow-up Message:**

```bash
POST /api/v1/conversations/{session_id}/stream
Headers: Authorization: Bearer <access_token>
Body: {"content": "What is 2+2?"}

# Response streams SSE events
event: session_id
data: {"session_id": "uuid", "found_in_cache": true}

event: text_delta
data: {"text": "2+2 is 4"}

event: done
data: {"turn_count": 2}
```

**SSE Event Types:**

| Event | Description |
|-------|-------------|
| `session_id` | Session initialized |
| `sdk_session_id` | SDK session identifier |
| `text_delta` | Streaming text chunk |
| `tool_use` | Tool invocation |
| `tool_result` | Tool result |
| `done` | Turn completed |
| `error` | Error occurred |

**Note:** SSE does not support `AskUserQuestion`. Use WebSocket for interactive features.

## CLI Commands

```bash
python main.py serve              # Start API server (port 7001)
python main.py serve --reload     # Dev mode with auto-reload
python main.py chat               # Interactive chat (WebSocket)
python main.py chat --mode sse    # Interactive chat (SSE)
python main.py chat --agent ID    # Chat with specific agent
python main.py agents             # List available agents
python main.py subagents          # List delegation subagents
python main.py sessions           # List conversation sessions
python main.py skills             # List available skills
```

## Directory Structure

```
backend/
├── main.py                 # CLI entry point
├── agents.yaml             # Agent definitions (root level)
├── subagents.yaml          # Subagent definitions (root level)
├── agent/
│   └── core/               # Agent utilities
│       ├── agent_options.py # create_agent_sdk_options()
│       └── storage.py       # SessionStorage + HistoryStorage
├── api/
│   ├── main.py             # FastAPI app factory
│   ├── config.py           # API configuration
│   ├── constants.py        # Event types, close codes, timeouts
│   ├── dependencies.py     # Dependency injection
│   ├── middleware/
│   │   ├── auth.py         # API key authentication
│   │   └── jwt_auth.py     # JWT authentication
│   ├── routers/
│   │   ├── websocket.py    # WebSocket endpoint
│   │   ├── conversations.py # SSE streaming
│   │   ├── sessions.py     # Session CRUD operations
│   │   ├── configuration.py # Agent listing
│   │   ├── auth.py         # JWT auth endpoints
│   │   └── health.py       # Health check
│   ├── services/
│   │   ├── session_manager.py   # Session management
│   │   ├── history_tracker.py   # Message history
│   │   ├── question_manager.py  # AskUserQuestion handling
│   │   ├── token_service.py     # JWT token operations
│   │   └── message_utils.py     # Message conversion utilities
│   └── models/             # Pydantic models
│       └── auth.py         # Auth request/response models
├── cli/
│   ├── main.py             # Click CLI
│   ├── commands/           # CLI commands (chat, serve, list)
│   └── clients/            # API/WS clients
├── tests/                  # Test files
└── data/
    ├── sessions.json       # Session metadata
    └── history/            # Message history (JSONL per session)
```

## Available Agents

| Agent ID | Name | Description | Model |
|----------|------|-------------|-------|
| `general-agent-a1b2c3d4` | General Assistant | General-purpose coding assistant (default) | sonnet |
| `code-reviewer-x9y8z7w6` | Code Reviewer | Code reviews and security analysis | sonnet |
| `doc-writer-m5n6o7p8` | Documentation Writer | Documentation generation | sonnet |
| `research-agent-q1r2s3t4` | Code Researcher | Codebase exploration (read-only) | haiku |
| `sandbox-agent-s4ndb0x1` | Sandbox Agent | Restricted file permissions for testing | sonnet |

## Subagents (Delegation)

Available for task delegation via Task tool:
- **researcher** - Code exploration and analysis
- **reviewer** - Code review and quality checks
- **file_assistant** - File operations assistance

## Configuration

### Environment Variables (.env)

```bash
# Claude API
ANTHROPIC_API_KEY=sk-ant-...

# Authentication key (generate with: openssl rand -hex 32)
API_KEY=your-api-key              # For REST API auth and JWT secret derivation

# JWT token expiration (optional, defaults shown)
# ACCESS_TOKEN_EXPIRE_MINUTES=30
# REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS (production frontend URL)
# Note: Localhost origins (http://localhost:* and http://127.0.0.1:*) are automatically allowed
CORS_ORIGINS=https://claude-agent-sdk-chat.tt-ai.org

# Server
API_HOST=0.0.0.0
API_PORT=7001
```

**Note:** No `JWT_SECRET_KEY` needed - the JWT secret is derived from `API_KEY` using HMAC-SHA256 with salt `claude-agent-sdk-jwt-v1`. Both frontend and backend use identical derivation.

### Agent Configuration (agents.yaml)

Located at `backend/agents.yaml`:

```yaml
_defaults:
  tools: [Skill, Task, Read, Write, Edit, Bash, Grep, Glob]
  model: sonnet
  permission_mode: acceptEdits
  with_permissions: true
  allowed_directories: [/tmp]

default_agent: general-agent-a1b2c3d4

agents:
  my-agent-abc123:
    name: "My Agent"
    description: "What this agent does"
    system_prompt: |
      Instructions appended to claude_code preset
    tools: [Read, Write, Bash, Grep, Glob]
    subagents: [researcher, reviewer, file_assistant]
    model: sonnet   # haiku, sonnet, opus
```

### Subagent Configuration (subagents.yaml)

Located at `backend/subagents.yaml`:

```yaml
subagents:
  researcher:
    name: "Research Specialist"
    description: "Code exploration and analysis"
    prompt: |
      You are a research specialist...
    tools: [Skill, Read, Grep, Glob]
    model: sonnet
```

## Docker

```bash
cd backend
make build   # Build image
make up      # Start container
make logs    # View logs
make down    # Stop container
```

## Testing

```bash
# Run tests
pytest

# Run specific test
pytest tests/test_websocket_timing.py

# Run with coverage
pytest --cov=api --cov=agent
```

## Production Deployment

```bash
# Using Cloudflare Tunnel
cloudflare tunnel --url http://localhost:7001 --hostname api.domain.com

# Production URL
https://claude-agent-sdk-fastapi-sg4.tt-ai.org
```
