# Claude Agent SDK Backend

FastAPI backend server for the Claude Agent SDK CLI application. Provides REST API and WebSocket endpoints for managing conversations with Claude agents.

## Quick Start

```bash
# Install dependencies
uv sync && source .venv/bin/activate

# Configure environment
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env

# Start server
python main.py serve --port 7001
```

## API Endpoints

Base URL: `http://localhost:7001`

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |

**Response:**
```json
{"status": "ok", "service": "agent-sdk-api"}
```

---

### Sessions

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/sessions` | Create a new session |
| GET | `/api/v1/sessions` | List all sessions |
| POST | `/api/v1/sessions/{id}/close` | Close a session (keeps in history) |
| DELETE | `/api/v1/sessions/{id}` | Delete a session and its history |
| GET | `/api/v1/sessions/{id}/history` | Get conversation history |
| POST | `/api/v1/sessions/{id}/resume` | Resume a specific session |
| POST | `/api/v1/sessions/resume` | Resume with session ID in body |

#### Create Session

```bash
POST /api/v1/sessions
Content-Type: application/json

{
  "agent_id": "general-abc123",      # Optional: agent to use
  "resume_session_id": "uuid-..."    # Optional: session to resume
}
```

**Response:**
```json
{
  "session_id": "uuid-...",
  "status": "ready",
  "resumed": false
}
```

#### List Sessions

```bash
GET /api/v1/sessions
```

**Response:**
```json
[
  {
    "session_id": "uuid-...",
    "first_message": "Hello, how can you help?",
    "created_at": "2026-01-21T17:25:32.151735",
    "turn_count": 3,
    "user_id": null
  }
]
```

#### Get Session History

```bash
GET /api/v1/sessions/{id}/history
```

**Response:**
```json
{
  "session_id": "uuid-...",
  "messages": [
    {
      "role": "user",
      "content": "Hello",
      "timestamp": "2026-01-21T17:25:32.151735"
    },
    {
      "role": "assistant",
      "content": "Hi! How can I help?",
      "timestamp": "2026-01-21T17:25:33.123456"
    }
  ],
  "turn_count": 1,
  "first_message": "Hello"
}
```

---

### Conversations (SSE Streaming)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/conversations` | Create conversation and stream response |
| POST | `/api/v1/conversations/{id}/stream` | Send message to existing session |
| POST | `/api/v1/conversations/{id}/interrupt` | Interrupt current task |

#### Create Conversation

```bash
POST /api/v1/conversations
Content-Type: application/json

{
  "content": "Hello, how can you help me?",
  "agent_id": "general-abc123",    # Optional
  "session_id": "uuid-..."         # Optional: use existing session
}
```

**SSE Response Events:**
```
event: session_id
data: {"session_id": "uuid-...", "found_in_cache": false}

event: text_delta
data: {"text": "Hello"}

event: text_delta
data: {"text": "! How can"}

event: text_delta
data: {"text": " I help you?"}

event: tool_use
data: {"tool_name": "Read", "input": {"file_path": "/path/to/file"}}

event: tool_result
data: {"tool_use_id": "...", "content": "file contents...", "is_error": false}

event: done
data: {"turn_count": 1, "total_cost_usd": 0.001234}
```

#### Stream Follow-up Message

```bash
POST /api/v1/conversations/{session_id}/stream
Content-Type: application/json

{
  "content": "What is 2 + 2?"
}
```

---

### Configuration

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/config/agents` | List available agents |

#### List Agents

```bash
GET /api/v1/config/agents
```

**Response:**
```json
{
  "agents": [
    {
      "agent_id": "general-abc12345",
      "name": "General Assistant",
      "type": "general",
      "description": "General-purpose coding assistant",
      "is_default": true,
      "read_only": false
    },
    {
      "agent_id": "code-reviewer-xyz789",
      "name": "Code Reviewer",
      "type": "reviewer",
      "description": "Reviews code for quality and best practices",
      "is_default": false,
      "read_only": true
    }
  ]
}
```

---

### WebSocket

| Protocol | Endpoint | Description |
|----------|----------|-------------|
| WS | `/api/v1/ws/chat` | Persistent WebSocket for multi-turn chat |

#### Connection URL

```
ws://localhost:7001/api/v1/ws/chat?agent_id=<agent_id>&session_id=<session_id>
```

**Query Parameters:**
- `agent_id` (optional): Agent to use for the conversation
- `session_id` (optional): Session ID to resume

#### Protocol

**Client sends:**
```json
{"content": "user message"}
```

**Server sends:**
```json
{"type": "ready"}
{"type": "ready", "session_id": "uuid-...", "resumed": true, "turn_count": 5}  // if resuming
{"type": "session_id", "session_id": "uuid-..."}
{"type": "text_delta", "text": "Hello"}
{"type": "tool_use", "name": "Read", "input": {...}}
{"type": "tool_result", "content": "...", "is_error": false}
{"type": "done", "turn_count": 1, "total_cost_usd": 0.001234}
{"type": "error", "error": "error message"}
```

#### Session Resumption

When connecting with `session_id` parameter:
1. Server looks up the session in storage
2. If found, creates SDK client with `resume_session_id` option
3. Sends ready signal with `resumed: true` and `turn_count`
4. Conversation context is maintained from previous messages

If session not found, server sends error and closes connection:
```json
{"type": "error", "error": "Session 'invalid-id' not found"}
```
Close code: 4004

---

## Event Types

| Event | Description |
|-------|-------------|
| `ready` | WebSocket connection established |
| `session_id` | Session ID assigned (first message) |
| `text_delta` | Streaming text chunk |
| `tool_use` | Agent is using a tool |
| `tool_result` | Tool execution result |
| `done` | Turn completed |
| `error` | Error occurred |

---

## CLI Commands

```bash
# Start API server
python main.py serve --port 7001

# Interactive chat (WebSocket mode)
python main.py chat

# Interactive chat (HTTP SSE mode)
python main.py chat --mode sse

# List agents
python main.py agents

# List sessions
python main.py sessions
```

---

## Data Storage

```
data/
├── sessions.json       # Session metadata (ID, first_message, turn_count)
└── history/
    └── {session_id}.jsonl  # Message history per session (JSONL format)
```

---

## Docker

```bash
# Build and run with Docker Compose
make build
make up

# View logs
make logs

# Stop
make down
```
