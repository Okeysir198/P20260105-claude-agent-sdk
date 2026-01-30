# Claude Agent SDK Backend

FastAPI server with user authentication, WebSocket streaming, and per-user data isolation.

## Quick Start

```bash
uv sync
cp .env.example .env   # Configure ANTHROPIC_API_KEY, API_KEY, JWT_SECRET, CLI_ADMIN_PASSWORD, CLI_TESTER_PASSWORD
uv run main.py serve --port 7001
```

## Authentication Principles

### Two-Layer Authentication

The backend uses a two-layer authentication system:

1. **API Key Authentication** - Required for all REST endpoints via `X-API-Key` header
2. **User Authentication** - SQLite-based authentication returning JWT tokens with `user_identity` type

### API Key Authentication

All REST endpoints require a valid API key passed via the `X-API-Key` header:

```bash
curl -H "X-API-Key: your-api-key" https://backend/api/v1/config/agents
```

The API key is used for:
- Validating client applications
- Deriving JWT tokens for WebSocket connections
- Protecting REST endpoints from unauthorized access

### User Authentication

User authentication provides per-user data isolation and multi-tenancy:

**Login Flow:**

```bash
POST /api/v1/auth/login
Headers: X-API-Key: your-api-key
Body: {"username": "admin", "password": "your-password"}

Response: {
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6ImF1dGhfaWRlbnRpdHk...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6InJlZnJlc2g...",
  "user": {
    "id": "...",
    "username": "admin",
    "full_name": "Admin User",
    "role": "admin"
  }
}
```

The returned token has `type: "user_identity"` and includes the username for per-user storage.

### JWT Token Types

| Token Type | Purpose | Expires In | Contains |
|------------|---------|------------|----------|
| **Access Token** | WebSocket authentication | 30 minutes | `sub` (user_id), `type: "access"` |
| **Refresh Token** | Get new access tokens | 7 days | `sub` (user_id), `type: "refresh"`, `jti` |
| **User Identity Token** | User login sessions | 30 minutes | `sub` (user_id), `type: "user_identity"`, `username`, `role` |

### Token Refresh Flow

```
1. Initial Login
   Client → POST /api/v1/auth/login
   Server → {token: "user_identity_jwt", refresh_token: "refresh_jwt"}

2. Use User Identity Token
   Client → REST requests with X-User-Token header
   Client → WebSocket with ?token=user_identity_jwt

3. Refresh When Expiring
   Client → POST /api/v1/auth/ws-token-refresh
          Body: {refresh_token: "refresh_jwt"}
   Server → {access_token: "new_access_jwt", refresh_token: "new_refresh_jwt"}
```

### WebSocket Authentication

WebSocket requires JWT with `user_identity` type (includes username for per-user storage):

```bash
wss://host/api/v1/ws/chat?token=<user_identity_jwt>&agent_id=xxx
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

## API Endpoint Catalog

### Health Endpoints (2 endpoints)

No authentication required.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Root health check for load balancers |
| GET | `/health` | Health check with service name |

**Response:**
```json
{
  "status": "ok",
  "service": "agent-sdk-api"
}
```

### User Authentication (3 endpoints)

API Key required via `X-API-Key` header.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/login` | User login with username/password |
| POST | `/api/v1/auth/logout` | User logout (for audit) |
| GET | `/api/v1/auth/me` | Get current authenticated user info |

**POST /api/v1/auth/login**
```bash
# Request
curl -X POST https://backend/api/v1/auth/login \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your-password"}'

# Response
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6ImF1dGhfaWRlbnRpdHk...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6InJlZnJlc2g...",
  "user": {
    "id": "user-uuid",
    "username": "admin",
    "full_name": "Admin User",
    "role": "admin"
  }
}
```

**GET /api/v1/auth/me**
```bash
# Request
curl https://backend/api/v1/auth/me \
  -H "X-API-Key: your-api-key" \
  -H "X-User-Token: user_identity_jwt"

# Response
{
  "id": "user-uuid",
  "username": "admin",
  "full_name": "Admin User",
  "role": "admin"
}
```

### WebSocket Token Management (2 endpoints)

API Key required via `X-API-Key` header.

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/ws-token` | Exchange API key for WebSocket tokens |
| POST | `/api/v1/auth/ws-token-refresh` | Refresh access token using refresh token |

**POST /api/v1/auth/ws-token**
```bash
# Request
curl -X POST https://backend/api/v1/auth/ws-token \
  -H "Content-Type: application/json" \
  -d '{"api_key": "your-api-key"}'

# Response
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6ImFjY2Vzcw...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6InJlZnJlc2g...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user_id": "api-key-user"
}
```

**POST /api/v1/auth/ws-token-refresh**
```bash
# Request
curl -X POST https://backend/api/v1/auth/ws-token-refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "your_refresh_token"}'

# Response
{
  "access_token": "new_access_token",
  "refresh_token": "new_refresh_token",
  "token_type": "bearer",
  "expires_in": 1800,
  "user_id": "api-key-user"
}
```

### Sessions (10 endpoints)

API Key + User JWT required (`X-API-Key` + `X-User-Token` headers).

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/sessions` | Create a new session |
| GET | `/api/v1/sessions` | List all sessions (newest first) |
| GET | `/api/v1/sessions/{id}/history` | Get session conversation history |
| PATCH | `/api/v1/sessions/{id}` | Update session properties (name) |
| DELETE | `/api/v1/sessions/{id}` | Delete a session |
| POST | `/api/v1/sessions/{id}/close` | Close a session (keep in history) |
| POST | `/api/v1/sessions/{id}/resume` | Resume a specific session by ID |
| POST | `/api/v1/sessions/batch-delete` | Delete multiple sessions at once |
| POST | `/api/v1/sessions/resume` | Resume previous session |
| WS | `/api/v1/ws/chat` | WebSocket chat connection |

**POST /api/v1/sessions** - Create Session
```bash
# Request
curl -X POST https://backend/api/v1/sessions \
  -H "X-API-Key: your-api-key" \
  -H "X-User-Token: user_identity_jwt" \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "claude-sonnet-4"}'

# Response
{
  "session_id": "uuid",
  "status": "ready",
  "resumed": false
}
```

**GET /api/v1/sessions** - List Sessions
```bash
# Request
curl https://backend/api/v1/sessions \
  -H "X-API-Key: your-api-key" \
  -H "X-User-Token: user_identity_jwt"

# Response
[
  {
    "session_id": "uuid",
    "name": "Session Name",
    "first_message": "Hello...",
    "created_at": "2025-01-15T10:30:00Z",
    "turn_count": 5,
    "agent_id": "claude-sonnet-4"
  }
]
```

**GET /api/v1/sessions/{id}/history** - Get Session History
```bash
# Request
curl https://backend/api/v1/sessions/uuid/history \
  -H "X-API-Key: your-api-key" \
  -H "X-User-Token: user_identity_jwt"

# Response
{
  "session_id": "uuid",
  "messages": [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi there!"}
  ],
  "turn_count": 1,
  "first_message": "Hello"
}
```

**PATCH /api/v1/sessions/{id}** - Update Session
```bash
# Request
curl -X PATCH https://backend/api/v1/sessions/uuid \
  -H "X-API-Key: your-api-key" \
  -H "X-User-Token: user_identity_jwt" \
  -H "Content-Type: application/json" \
  -d '{"name": "New Session Name"}'

# Response
{
  "session_id": "uuid",
  "name": "New Session Name",
  "first_message": "Hello...",
  "created_at": "2025-01-15T10:30:00Z",
  "turn_count": 5
}
```

**DELETE /api/v1/sessions/{id}** - Delete Session
```bash
# Request
curl -X DELETE https://backend/api/v1/sessions/uuid \
  -H "X-API-Key: your-api-key" \
  -H "X-User-Token: user_identity_jwt"

# Response
{
  "status": "deleted"
}
```

**POST /api/v1/sessions/{id}/close** - Close Session
```bash
# Request
curl -X POST https://backend/api/v1/sessions/uuid/close \
  -H "X-API-Key: your-api-key" \
  -H "X-User-Token: user_identity_jwt"

# Response
{
  "status": "closed"
}
```

**POST /api/v1/sessions/{id}/resume** - Resume Session by ID
```bash
# Request
curl -X POST https://backend/api/v1/sessions/uuid/resume \
  -H "X-API-Key: your-api-key" \
  -H "X-User-Token: user_identity_jwt" \
  -H "Content-Type: application/json" \
  -d '{"initial_message": "Let\'s continue..."}'

# Response
{
  "session_id": "uuid",
  "status": "ready",
  "resumed": true
}
```

**POST /api/v1/sessions/batch-delete** - Batch Delete
```bash
# Request
curl -X POST https://backend/api/v1/sessions/batch-delete \
  -H "X-API-Key: your-api-key" \
  -H "X-User-Token: user_identity_jwt" \
  -H "Content-Type: application/json" \
  -d '{"session_ids": ["uuid1", "uuid2", "uuid3"]}'

# Response
{
  "status": "deleted"
}
```

**POST /api/v1/sessions/resume** - Resume Previous Session
```bash
# Request
curl -X POST https://backend/api/v1/sessions/resume \
  -H "X-API-Key: your-api-key" \
  -H "X-User-Token: user_identity_jwt" \
  -H "Content-Type: application/json" \
  -d '{"resume_session_id": "previous-uuid"}'

# Response
{
  "session_id": "previous-uuid",
  "status": "ready",
  "resumed": true
}
```

### Conversations (2 endpoints)

API Key + User JWT required (`X-API-Key` + `X-User-Token` headers).

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/conversations` | Create new conversation with SSE streaming |
| POST | `/api/v1/conversations/{session_id}/stream` | Send message in existing session with SSE streaming |

**POST /api/v1/conversations** - Create Conversation
```bash
# Request
curl -X POST https://backend/api/v1/conversations \
  -H "X-API-Key: your-api-key" \
  -H "X-User-Token: user_identity_jwt" \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello, how can you help me?", "agent_id": "claude-sonnet-4"}'

# Response (SSE stream)
event: session_id
data: {"session_id": "uuid", "found_in_cache": false}

event: sdk_session_id
data: {"sdk_session_id": "sdk-uuid"}

event: text_delta
data: {"text": "Hello"}

event: text_delta
data: {"text": "!"}

event: done
data: {"turn_count": 1}
```

**POST /api/v1/conversations/{session_id}/stream** - Stream Conversation
```bash
# Request
curl -X POST https://backend/api/v1/conversations/uuid/stream \
  -H "X-API-Key: your-api-key" \
  -H "X-User-Token: user_identity_jwt" \
  -H "Content-Type: application/json" \
  -d '{"content": "What is 2 + 2?"}'

# Response (SSE stream)
event: session_id
data: {"session_id": "uuid", "found_in_cache": true}

event: text_delta
data: {"text": "2"}

event: text_delta
data: {"text": " + "}

event: text_delta
data: {"text": "2"}

event: text_delta
data: {"text": " = "}

event: text_delta
data: {"text": "4"}

event: done
data: {"turn_count": 2}
```

### Configuration (1 endpoint)

API Key required via `X-API-Key` header.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/config/agents` | List available agents |

**GET /api/v1/config/agents**
```bash
# Request
curl https://backend/api/v1/config/agents \
  -H "X-API-Key: your-api-key"

# Response
{
  "agents": [
    {
      "agent_id": "claude-sonnet-4",
      "name": "Claude Sonnet 4",
      "description": "Balanced performance and speed",
      "model": "claude-sonnet-4-20250514"
    }
  ]
}
```

## SDK Client Persistence Principle

### Why Persistence Matters

The SDK Client requires session persistence for multi-turn conversations. When a client creates a conversation, the backend generates a session ID that must be maintained across requests. Losing the session ID breaks conversation continuity.

### Implementation Approach

**Primary: WebSocket Persistence**

WebSocket connections maintain state through the SessionManager's in-memory cache:

```
1. Client connects via WebSocket
2. SessionManager creates SDK session and returns sdk_session_id
3. Session remains in memory for the connection duration
4. Multi-turn conversations work seamlessly
```

**Fallback: Session Manager REST API**

When WebSocket is unavailable, the SDK Client falls back to REST endpoints:

```
1. Client creates session via POST /api/v1/sessions
2. Backend returns session_id
3. Client stores session_id locally
4. Client sends messages via POST /api/v1/conversations/{session_id}/stream
5. Backend resolves pending_id to SDK session ID on first message
```

### Per-User Data Isolation

All session data is isolated per-user in the filesystem:

```
backend/data/
├── users.db              # SQLite user database (shared)
├── admin/                # Admin user's isolated data
│   ├── sessions.json     # Session metadata
│   └── history/          # Conversation history
│       └── {session_id}.jsonl
└── tester/               # Tester user's isolated data
    ├── sessions.json
    └── history/
        └── {session_id}.jsonl
```

### Session Resolution

The SessionManager resolves sessions in this order:

1. **In-Memory Cache** - Active WebSocket sessions
2. **Session Storage** - Persistent session metadata from `sessions.json`
3. **History Storage** - Conversation history from `history/{session_id}.jsonl`

This ensures sessions can be resumed even after server restart, as long as they exist in storage.

## WebSocket Protocol

### Connection Flow

```
# 1. Client connects
Client → wss://host/api/v1/ws/chat?token=jwt&agent_id=xxx

# 2. Server ready
Server → {"type": "ready"}

# 3. Client sends message
Client → {"content": "Hello!"}

# 4. Server streams response
Server → {"type": "session_id", "session_id": "uuid"}
Server → {"type": "text_delta", "text": "Hi!"}
Server → {"type": "tool_use", "name": "Read", ...}
Server → {"type": "tool_result", "content": "..."}
Server → {"type": "done", "turn_count": 1}
```

### AskUserQuestion Flow

```
# 1. Server asks question
Server → {"type": "ask_user_question", "question_id": "q1", "questions": [
  {"id": "q1", "question": "Continue?", "type": "choice", "options": ["yes", "no"]}
]}

# 2. Client answers
Client → {"type": "user_answer", "question_id": "q1", "answers": {"q1": "yes"}}

# 3. Server confirms and continues
Server → {"type": "question_answered", "question_id": "q1"}
Server → {"type": "text_delta", "text": "Great! Continuing..."}
```

### Message Types

| Type | Direction | Description |
|------|-----------|-------------|
| `ready` | Server→Client | Connection ready |
| `session_id` | Server→Client | Session ID for this connection |
| `text_delta` | Server→Client | Streaming text fragment |
| `tool_use` | Server→Client | Tool being invoked |
| `tool_result` | Server→Client | Tool execution result |
| `done` | Server→Client | Response complete |
| `ask_user_question` | Server→Client | Question for user |
| `user_answer` | Client→Server | User's answer |
| `question_answered` | Server→Client | Answer received |

## CLI Commands

```bash
uv run main.py serve              # Start server (port 7001)
uv run main.py chat               # Interactive chat (prompts for password)
uv run main.py agents             # List agents
uv run main.py sessions           # List sessions
```

## Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...
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

## Data Structure

```
data/
├── users.db              # SQLite user database
├── admin/                # Admin's data
│   ├── sessions.json
│   └── history/
│       └── {session_id}.jsonl
└── tester/               # Tester's data
    └── ...
```

## Testing

```bash
# Set CLI_ADMIN_PASSWORD and CLI_TESTER_PASSWORD in .env first
pytest tests/
```

## Docker

```bash
make build && make up
```
