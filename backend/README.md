# Claude Agent SDK Backend

FastAPI backend server for the Claude Agent SDK CLI application. Provides REST API and WebSocket endpoints for managing conversations with Claude agents.

## Quick Start

```bash
# Install dependencies
uv sync && source .venv/bin/activate

# Configure environment
cp .env.example .env
# Add your API key to .env (depends on provider in config.yaml)

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
  "agent_id": "general-agent-a1b2c3d4",  # Optional: agent to use
  "resume_session_id": "uuid-..."        # Optional: session to resume
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
  "agent_id": "general-agent-a1b2c3d4",  # Optional
  "session_id": "uuid-..."               # Optional: use existing session
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
      "agent_id": "general-agent-a1b2c3d4",
      "name": "General Assistant",
      "type": "general",
      "description": "General-purpose coding assistant for everyday tasks",
      "is_default": true,
      "read_only": false
    },
    {
      "agent_id": "code-reviewer-x9y8z7w6",
      "name": "Code Reviewer",
      "type": "reviewer",
      "description": "Specialized agent for thorough code reviews and security analysis",
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

# Interactive chat with specific agent
python main.py chat --agent code-reviewer-x9y8z7w6

# List available skills
python main.py skills

# List top-level agents
python main.py agents

# List subagents
python main.py subagents

# List sessions
python main.py sessions
```

---

## Directory Structure

```
backend/
├── main.py                 # CLI entry point
├── config.yaml             # Provider configuration
├── agent/
│   ├── agents.yaml         # Top-level agent definitions
│   ├── subagents.yaml      # Delegation subagent definitions
│   └── core/
│       ├── session.py      # ConversationSession (is_connected property)
│       ├── agent_options.py # create_agent_sdk_options(agent_id, resume_session_id)
│       ├── agents.py       # Agent loading utilities
│       ├── subagents.py    # Subagent loading utilities
│       ├── storage.py      # SessionStorage + HistoryStorage
│       ├── config.py       # Provider config loading
│       ├── hook.py         # Permission hooks
│       └── yaml_utils.py   # YAML utilities
├── api/
│   ├── main.py             # FastAPI app factory with exception handlers
│   ├── config.py           # API configuration
│   ├── constants.py        # API constants
│   ├── dependencies.py     # FastAPI dependencies
│   ├── routers/
│   │   ├── websocket.py    # WebSocket endpoint for persistent chat
│   │   ├── conversations.py # SSE streaming (legacy)
│   │   ├── sessions.py     # Session CRUD + history
│   │   ├── configuration.py # List agents
│   │   └── health.py       # Health check
│   ├── services/
│   │   ├── session_manager.py  # get_or_create_conversation_session()
│   │   ├── history_tracker.py  # Track and save conversation history
│   │   └── message_utils.py    # Message utilities
│   └── models/
│       ├── requests.py     # Pydantic request models
│       └── responses.py    # Pydantic response models
├── cli/
│   ├── main.py             # Click CLI definition
│   ├── commands/
│   │   ├── chat.py         # Interactive chat command
│   │   ├── serve.py        # Server command
│   │   ├── list.py         # List commands (agents, skills, etc.)
│   │   └── handlers.py     # Chat event handlers
│   └── clients/            # CLI client implementations
├── tests/
│   ├── test_api_agent_selection.py
│   ├── test_claude_agent_sdk.py
│   ├── test_claude_agent_sdk_multi_turn.py
│   └── test_websocket_timing.py
└── data/
    ├── sessions.json       # Session metadata
    └── history/            # Message history (JSONL per session)
```

---

## Available Agents

Defined in `agent/agents.yaml`:

| Agent ID | Name | Description |
|----------|------|-------------|
| `general-agent-a1b2c3d4` | General Assistant | General-purpose coding assistant (default) |
| `code-reviewer-x9y8z7w6` | Code Reviewer | Code reviews and security analysis (read-only) |
| `doc-writer-m5n6o7p8` | Documentation Writer | Documentation generation |
| `research-agent-q1r2s3t4` | Code Researcher | Read-only codebase exploration |
| `sandbox-agent-s4ndb0x1` | Sandbox Agent | Restricted file permissions for testing |

---

## Available Subagents

Defined in `agent/subagents.yaml` (used for delegation within conversations):

| Subagent | Name | Description |
|----------|------|-------------|
| `researcher` | Research Specialist | Finding and analyzing code |
| `reviewer` | Code Reviewer | Code quality and security reviews |
| `file_assistant` | File Assistant | File navigation and search |

---

## Configuration

### Provider Selection

Set the active provider in `config.yaml`:

```yaml
provider: claude  # claude, zai, minimax, proxy
```

### Environment Variables

Configure in `.env` (see `.env.example`):

```bash
# Claude API (Official Anthropic API)
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# ZAI API
ZAI_API_KEY=your_zai_api_key_here
ZAI_BASE_URL=https://api.z.ai/api/anthropic

# Minimax API
MINIMAX_API_KEY=your_minimax_api_key_here
MINIMAX_BASE_URL=your_minimax_base_url_here

# Proxy API (local claude-code-proxy)
PROXY_BASE_URL=http://localhost:4000
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
