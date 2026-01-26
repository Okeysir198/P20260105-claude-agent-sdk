# Claude Agent SDK Backend

FastAPI server providing REST API and WebSocket endpoints for the Claude Agent SDK chat application.

## Quick Start

```bash
uv sync && source .venv/bin/activate
cp .env.example .env   # Configure API keys
python main.py serve --port 7001
```

## Authentication

All endpoints except `/health` require API key authentication:

- **REST API:** `X-API-Key` header only (query params not accepted for security)
- **WebSocket:** `api_key` query parameter (browser limitation - cannot send headers)

Security features:
- Timing-safe comparison prevents timing attacks
- Auth failures logged with client IP (keys never logged)

## API Endpoints

### Health Check

```bash
GET /health
# Response: {"status": "ok", "service": "agent-sdk-api"}
```

### Sessions

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/sessions` | List all sessions |
| GET | `/api/v1/sessions/{id}/history` | Get message history |
| DELETE | `/api/v1/sessions/{id}` | Delete session + history |
| POST | `/api/v1/sessions/{id}/close` | Close session (keep history) |
| POST | `/api/v1/sessions/{id}/resume` | Resume session |

### Conversations (SSE)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/conversations` | Create and stream response |
| POST | `/api/v1/conversations/{id}/stream` | Send follow-up message |

### Configuration

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/config/agents` | List available agents |

### WebSocket

```
WS /api/v1/ws/chat?api_key=KEY&agent_id=AGENT_ID&session_id=SESSION_ID
```

**Query Parameters:**
- `api_key` - Required if API_KEY is configured
- `agent_id` - Optional agent to use
- `session_id` - Optional session to resume

**Protocol:**

```
Server → {"type": "ready"}
Server → {"type": "ready", "session_id": "...", "resumed": true, "turn_count": 5}  # if resuming
Client → {"content": "Hello!"}
Server → {"type": "session_id", "session_id": "uuid"}
Server → {"type": "text_delta", "text": "Hi there!"}
Server → {"type": "tool_use", "name": "Read", "input": {...}}
Server → {"type": "tool_result", "content": "..."}
Server → {"type": "ask_user_question", "question_id": "...", "questions": [...]}
Client → {"type": "user_answer", "question_id": "...", "answers": {...}}
Server → {"type": "done", "turn_count": 1}
Server → {"type": "error", "error": "message"}
```

## SSE Event Types

| Event | Description |
|-------|-------------|
| `session_id` | Session initialized |
| `text_delta` | Streaming text chunk |
| `tool_use` | Tool invocation |
| `tool_result` | Tool result |
| `done` | Turn completed |
| `error` | Error occurred |

## CLI Commands

```bash
python main.py serve              # Start API server (port 7001)
python main.py serve --reload     # Dev mode with auto-reload
python main.py chat               # Interactive chat (WebSocket)
python main.py chat --mode sse    # Interactive chat (SSE)
python main.py chat --agent ID    # Chat with specific agent
python main.py agents             # List agents
python main.py subagents          # List subagents
python main.py sessions           # List sessions
python main.py skills             # List skills
```

## Directory Structure

```
backend/
├── main.py                 # CLI entry point
├── agents.yaml             # Top-level agent definitions
├── subagents.yaml          # Subagent definitions
├── agent/
│   └── core/               # Agent utilities
│       ├── agent_options.py # create_agent_sdk_options()
│       └── storage.py       # SessionStorage + HistoryStorage
├── api/
│   ├── main.py             # FastAPI app factory
│   ├── config.py           # API configuration
│   ├── constants.py        # Event types, close codes
│   ├── dependencies.py     # Dependency injection
│   ├── middleware/         # Auth middleware
│   ├── routers/            # API routes (websocket, sessions, etc.)
│   ├── services/           # Business logic
│   └── models/             # Pydantic models
├── cli/
│   ├── main.py             # Click CLI
│   ├── commands/           # CLI commands
│   └── clients/            # API/WS clients
├── tests/                  # Test files
└── data/
    ├── sessions.json       # Session metadata
    └── history/            # Message history (JSONL)
```

## Available Agents

| Agent ID | Name | Description | Model |
|----------|------|-------------|-------|
| `general-agent-a1b2c3d4` | General Assistant | General-purpose (default) | sonnet |
| `code-reviewer-x9y8z7w6` | Code Reviewer | Code reviews (read-only) | sonnet |
| `doc-writer-m5n6o7p8` | Documentation Writer | Doc generation | sonnet |
| `research-agent-q1r2s3t4` | Code Researcher | Exploration (read-only) | haiku |
| `sandbox-agent-s4ndb0x1` | Sandbox Agent | Restricted permissions | sonnet |

## Configuration

### Environment Variables (.env)

```bash
# Claude API
ANTHROPIC_API_KEY=sk-ant-...

# API Authentication (use `openssl rand -hex 32` for secure key)
API_KEY=your-secure-key

# CORS
CORS_ORIGINS=http://localhost:7002,https://your-domain.com

# Server
API_HOST=0.0.0.0
API_PORT=7001
```

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
