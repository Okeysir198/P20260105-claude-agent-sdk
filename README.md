# Claude Agent SDK CLI

An interactive chat application that wraps the Claude Agent SDK with Skills and Subagents support. Supports multiple LLM providers and two operational modes (Direct SDK and API Server).

## Features

- **Dual Operation Modes**: Direct SDK mode or API server mode
- **Docker Support**: Production-ready Docker deployment with easy provider switching
- **Skills System**: Extensible custom skills for code analysis, documentation generation, and issue tracking
- **Subagents**: Built-in agents (researcher, reviewer, file_assistant) for specialized tasks
- **Multi-Provider Support**: Claude (Anthropic), ZAI, and MiniMax providers
- **Session Management**: Persistent conversation history with resume capability
- **Streaming Responses**: Real-time SSE streaming for both modes
- **Provider Switching**: Switch providers instantly without rebuilding

## Quick Start

### Option 1: Docker (Recommended - Production Ready)

```bash
# Configure environment
cp .env.example .env
nano .env  # Add your API key

# Build and start
make build && make up

# Or use Docker Compose directly
docker compose build
docker compose up -d claude-api

# Test the API
curl http://localhost:19830/health
```

**See [DOCKER.md](DOCKER.md) for complete Docker deployment guide, including:**
- Provider switching without rebuild
- Cloud deployment (AWS, GCP, Azure)
- Production configuration
- Troubleshooting and monitoring

### Option 2: Local Development

```bash
# Clone the repository
git clone <repository-url>
cd P20260105-claude-agent-sdk

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Add your API key

# Run interactive chat
python main.py
```

## Configuration

### Environment Variables

Set your API key for the provider you want to use:

```bash
# For Claude (Anthropic) - Recommended
ANTHROPIC_API_KEY=sk-ant-api03-...

# For Zai
ZAI_API_KEY=your_zai_key
ZAI_BASE_URL=https://api.zai-provider.com

# For MiniMax
MINIMAX_API_KEY=your_minimax_key
MINIMAX_BASE_URL=https://api.minimax-provider.com
```

### Provider Configuration

Edit `config.yaml` to switch between providers:

```yaml
provider: claude  # Options: claude, zai, minimax
```

**Docker users**: Switch providers easily without rebuilding:
```bash
./switch-provider.sh zai      # Switch to Zai
./switch-provider.sh claude   # Switch to Claude
./switch-provider.sh minimax  # Switch to MiniMax
```

## Usage

### Interactive Chat (Direct Mode - Default)

```bash
# Local development
python main.py
python main.py --mode direct

# Docker
make up-interactive
# OR
docker compose run --rm claude-interactive
```

### API Server Mode

```bash
# Local development
python main.py serve                  # Default: 0.0.0.0:19830
python main.py serve --port 8080      # Custom port

# Docker
make up
# OR
docker compose up -d claude-api

# Check logs
docker compose logs -f claude-api
```

The API will be available at `http://localhost:19830`

### List Resources

```bash
# Local
python main.py skills                 # List available skills
python main.py agents                 # List subagents
python main.py sessions               # List conversation history

# Docker
make skills
make agents
make sessions
```

### Resume Session

```bash
# Local
python main.py --session-id <id>

# Docker
docker compose run --rm claude-interactive python main.py --session-id <id>
```

## API Endpoints

When running in server mode, the following endpoints are available:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/v1/sessions` | GET | List sessions |
| `/api/v1/sessions/{id}/resume` | POST | Resume session |
| `/api/v1/conversations` | POST | Create conversation (SSE stream) |
| `/api/v1/conversations/{id}/stream` | POST | Send message (SSE stream) |
| `/api/v1/conversations/{id}/interrupt` | POST | Interrupt task |
| `/api/v1/config/skills` | GET | List skills |
| `/api/v1/config/agents` | GET | List agents |

### Example API Usage

```bash
# Create a new conversation
curl -N -X POST http://localhost:19830/api/v1/conversations \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello! Can you help me?"}'

# Send a follow-up message
curl -N -X POST http://localhost:19830/api/v1/conversations/{session_id}/stream \
  -H "Content-Type: application/json" \
  -d '{"content": "What is 2 + 2?"}'

# List sessions
curl http://localhost:19830/api/v1/sessions
```

## Custom Skills

Add custom skills in `.claude/skills/<name>/SKILL.md`. The application includes:

- **code-analyzer**: Analyze code for patterns and issues
- **doc-generator**: Generate documentation for code
- **issue-tracker**: Track and categorize code issues

Skills are automatically invoked based on context. For example:
- "Analyze this file for issues" → invokes `code-analyzer`
- "Generate documentation for this module" → invokes `doc-generator`

## Architecture

```
├── agent/                    # Core business logic
│   ├── core/
│   │   ├── options.py       # ClaudeAgentOptions builder
│   │   ├── session.py       # ConversationSession - main loop
│   │   ├── storage.py       # Session storage (data/sessions.json)
│   │   ├── config.py        # Provider configuration loader
│   │   └── agents.py        # Subagent definitions
│   ├── discovery/
│   │   ├── skills.py        # Discovers skills from .claude/skills/
│   │   └── mcp.py           # Loads MCP servers from .mcp.json
│   └── display/             # Rich console output utilities
│
├── api/                      # FastAPI HTTP/SSE server
│   ├── main.py              # FastAPI app with lifespan management
│   ├── routers/             # Endpoints: /sessions, /conversations, /config
│   └── services/
│       ├── session_manager.py     # In-memory session state + persistence
│       └── conversation_service.py # ClaudeSDKClient wrapper for streaming
│
├── cli/                      # Click-based CLI
│   ├── main.py              # CLI entry point with click commands
│   ├── clients/
│   │   ├── direct.py        # DirectClient - wraps SDK directly
│   │   └── api.py           # APIClient - HTTP/SSE client
│   └── commands/            # chat, serve, list commands
│
├── .claude/skills/           # Custom skills
├── config.yaml              # Provider configuration
├── Dockerfile               # Docker image definition
├── docker-compose.yml       # Docker orchestration
├── Makefile                 # Convenient management commands
└── data/sessions.json       # Persisted session history
```

## Data Flows

**Direct Mode**: `cli/main.py` → `cli/clients/direct.py` → `claude_agent_sdk.ClaudeSDKClient`

**API Mode**: `cli/main.py` → `cli/clients/api.py` → `api/routers/*` → `api/services/conversation_service.py` → `ClaudeSDKClient`

## Docker Commands

```bash
# Build and start
make build && make up

# View logs
make logs

# Interactive mode
make up-interactive

# Switch providers
./switch-provider.sh zai

# Stop services
make down

# Clean up
make clean
```

## Requirements

- Python 3.10+
- Docker Engine 20.10+ (for Docker deployment)
- Docker Compose v2.0+ (for Docker deployment)

## Project Status

- ✅ **Core Features**: All features implemented and tested
- ✅ **Docker Deployment**: Production-ready with multi-provider support
- ✅ **Provider Switching**: Easy switching without rebuild (MiniMax → Zai tested)
- ✅ **API Server**: FastAPI with SSE streaming working
- ✅ **Session Management**: 20+ sessions persisted
- ✅ **Documentation**: Comprehensive Docker guide included

## Performance Notes

| Provider | Response Time | Status |
|----------|---------------|--------|
| **Claude (Anthropic)** | ~2-3s | ⭐ Recommended |
| **Zai** | ~5s | ✅ Good alternative |
| **MiniMax** | >60s | ⚠️ Not recommended for production |

## License

MIT

## Documentation

- [DOCKER.md](DOCKER.md) - Complete Docker deployment guide
- [CLAUDE.md](CLAUDE.md) - Claude Code instructions
- [API Documentation](#api-endpoints) - API reference

---

## API Architecture Deep Dive

This section provides detailed documentation of the API layer, session management, and client connection handling.

### Directory Structure

```
api/
├── main.py              # FastAPI application entry point with lifespan management
├── config.py            # Application settings (host, port, API prefix)
├── dependencies.py      # FastAPI dependency injection functions
├── core/                # Core utilities (currently empty)
├── routers/             # API endpoint handlers
│   ├── health.py        # Health check endpoint
│   ├── sessions.py      # Session CRUD operations
│   ├── conversations.py # Message handling with SSE streaming
│   └── configuration.py # Skills and agents listing
└── services/            # Business logic layer
    ├── session_manager.py      # Session lifecycle and state management
    └── conversation_service.py # Claude SDK interaction wrapper
```

### Service Layer Architecture

#### 1. SessionManager (`api/services/session_manager.py`)

The `SessionManager` is responsible for managing the lifecycle of Claude SDK client sessions. It maintains both in-memory state and persistent storage.

**SessionState Dataclass:**
```python
@dataclass
class SessionState:
    session_id: str                    # Unique session identifier
    client: ClaudeSDKClient           # Persistent SDK client instance
    turn_count: int = 0               # Number of conversation turns
    status: Literal["active", "idle", "closed"] = "idle"
    created_at: datetime              # Session creation timestamp
    last_activity: datetime           # Last interaction timestamp
    first_message: Optional[str]      # First user message (for history)
    lock: asyncio.Lock                # Per-session concurrency lock
```

**Key Methods:**

| Method | Description |
|--------|-------------|
| `create_session(resume_session_id)` | Creates new client, calls `connect()`, returns `SessionState` |
| `register_session(session_id, client, first_message)` | Registers an already-connected client in memory |
| `get_session(session_id)` | Retrieves session by ID (async with lock) |
| `close_session(session_id)` | Disconnects client and removes from memory |
| `update_session_id(old_id, new_id, first_message)` | Updates pending-* IDs to real SDK IDs |
| `resume_session(session_id)` | Resumes a session from persistent history |
| `cleanup_all()` | Closes all sessions (used during shutdown) |

**Storage Architecture:**
- **In-Memory:** `_sessions: dict[str, SessionState]` for active sessions
- **Persistent:** `agent.core.storage.SessionStorage` saves to `data/sessions.json`
- **Synchronization:** Both storages are updated on session creation/update

#### 2. ConversationService (`api/services/conversation_service.py`)

The `ConversationService` wraps Claude SDK client interactions and handles message streaming.

**Key Methods:**

| Method | Description |
|--------|-------------|
| `create_and_stream(content, resume_session_id)` | Creates session + streams first message response |
| `send_message(session_id, content)` | Non-streaming message (returns complete response) |
| `stream_message(session_id, content)` | Streams response as SSE events |
| `interrupt(session_id)` | Interrupts current task execution |

---

### Session ID Management Flow

The API uses a two-phase session ID system to handle the asynchronous nature of SDK session creation.

#### Phase 1: Temporary ID (pending-*)

When a session is created without an immediate message, a temporary ID is generated:

```python
temp_id = f"pending-{id(client)}"  # e.g., "pending-140234567890"
```

#### Phase 2: Real SDK ID

The real session ID is obtained from the SDK during the first message exchange:

```python
# In SystemMessage handling
if msg.subtype == "init" and msg.data:
    sdk_session_id = msg.data.get("session_id")  # Real UUID from SDK
```

#### Session ID Flow Diagrams

**Flow A: Create Conversation (Recommended)**

```
Client                          API Server                       Claude SDK
  │                                │                                 │
  │  POST /conversations           │                                 │
  │  {content: "Hello"}            │                                 │
  │ ───────────────────────────────>                                 │
  │                                │                                 │
  │                                │  ClaudeSDKClient(options)       │
  │                                │  client.connect()               │
  │                                │ ────────────────────────────────>
  │                                │                                 │
  │                                │  client.query(content)          │
  │                                │ ────────────────────────────────>
  │                                │                                 │
  │                                │  SystemMessage(init)            │
  │                                │  {session_id: "uuid-xxx"}       │
  │                                │ <────────────────────────────────
  │                                │                                 │
  │  SSE: session_id               │  register_session(uuid, client) │
  │  {session_id: "uuid-xxx"}      │                                 │
  │ <───────────────────────────────                                 │
  │                                │                                 │
  │  SSE: text_delta               │  StreamEvent(text_delta)        │
  │  {text: "Hi there!"}           │ <────────────────────────────────
  │ <───────────────────────────────                                 │
  │                                │                                 │
  │  SSE: done                     │  ResultMessage                  │
  │  {turn_count: 1}               │ <────────────────────────────────
  │ <───────────────────────────────                                 │
```

**Flow B: Create Session First, Then Stream**

```
Client                          API Server                       Claude SDK
  │                                │                                 │
  │  POST /sessions                │                                 │
  │ ───────────────────────────────>                                 │
  │                                │  ClaudeSDKClient(options)       │
  │                                │  client.connect()               │
  │                                │ ────────────────────────────────>
  │                                │                                 │
  │                                │  register_session(pending-xxx)  │
  │  {session_id: "pending-xxx"}   │                                 │
  │ <───────────────────────────────                                 │
  │                                │                                 │
  │  POST /conversations/          │                                 │
  │       pending-xxx/stream       │                                 │
  │  {content: "Hello"}            │                                 │
  │ ───────────────────────────────>                                 │
  │                                │                                 │
  │                                │  client.query(content)          │
  │                                │ ────────────────────────────────>
  │                                │                                 │
  │                                │  SystemMessage(init)            │
  │                                │  {session_id: "uuid-xxx"}       │
  │                                │ <────────────────────────────────
  │                                │                                 │
  │                                │  update_session_id(             │
  │                                │    pending-xxx → uuid-xxx)      │
  │  SSE: session_id               │                                 │
  │  {session_id: "uuid-xxx"}      │                                 │
  │ <───────────────────────────────                                 │
  │                                │                                 │
  │  SSE: text_delta, done...      │                                 │
  │ <───────────────────────────────                                 │
```

---

### Client Connection Management

#### Connection Lifecycle

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Client Connection States                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌──────────┐    connect()    ┌──────────┐    disconnect()   ┌──────┐ │
│   │  Created │ ───────────────> │  Active  │ ─────────────────> │ Closed│ │
│   └──────────┘                 └──────────┘                   └──────┘ │
│        │                            │                                   │
│        │                            │ query() / receive_response()      │
│        │                            │ (multiple times)                  │
│        │                            ↺                                   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Key Connection Patterns

1. **Persistent Connections**: SDK clients are kept alive in `SessionState` for the duration of the session
2. **No Reconnection**: Subsequent messages reuse the existing client connection
3. **Graceful Shutdown**: The `lifespan()` context manager ensures all sessions are closed on app shutdown

```python
# From api/main.py - Lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize services
    session_manager = SessionManager()
    conversation_service = ConversationService(session_manager)
    app.state.session_manager = session_manager
    app.state.conversation_service = conversation_service

    yield

    # Shutdown: Cleanup all sessions
    for session in session_manager.list_sessions():
        await session_manager.close_session(session.session_id)
```

#### Thread Safety

- **Global Lock**: `SessionManager._lock` protects the sessions dictionary
- **Per-Session Lock**: `SessionState.lock` allows concurrent access to different sessions
- **Async-Safe**: All operations use `async with self._lock` pattern

---

### SSE Event Types

The streaming endpoints emit Server-Sent Events (SSE) with the following event types:

| Event Type | Description | Data Schema |
|------------|-------------|-------------|
| `session_id` | Real session ID from SDK (first message only) | `{"session_id": "uuid-xxx"}` |
| `text_delta` | Streaming text chunk | `{"text": "..."}` |
| `tool_use` | Tool invocation started | `{"tool_name": "...", "input": {...}}` |
| `tool_result` | Tool execution completed | `{"tool_use_id": "...", "content": "...", "is_error": false}` |
| `done` | Conversation turn completed | `{"session_id": "...", "turn_count": N, "total_cost_usd": 0.0}` |
| `error` | Error occurred | `{"error": "error message"}` |

**SSE Event Generator Pattern:**

```python
async def create_sse_event_generator(stream_func, error_prefix):
    try:
        async for event_data in stream_func():
            yield {
                "event": event_data.get("event", "message"),
                "data": json.dumps(event_data.get("data", {}))
            }
    except Exception as e:
        yield {"event": "error", "data": json.dumps({"error": str(e)})}
```

---

### Dependency Injection

The API uses FastAPI's dependency injection system to provide services to endpoint handlers:

```python
# api/dependencies.py
def get_session_manager(request: Request) -> SessionManager:
    return request.app.state.session_manager

def get_conversation_service(request: Request) -> ConversationService:
    return request.app.state.conversation_service

# Usage in routers
@router.post("")
async def create_conversation(
    request: CreateConversationRequest,
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    ...
```

---

### API Endpoint Details

#### Sessions Router (`/api/v1/sessions`)

| Endpoint | Method | Description | Request | Response |
|----------|--------|-------------|---------|----------|
| `/` | POST | Create session (no message) | - | `{session_id, status}` |
| `/` | GET | List all sessions | - | `{active_sessions[], history_sessions[]}` |
| `/{id}` | GET | Get session info | - | `{session_id, is_active}` |
| `/{id}/resume` | POST | Resume from history | - | `{session_id, message}` |
| `/{id}` | DELETE | Close session | - | `{session_id, message}` |

#### Conversations Router (`/api/v1/conversations`)

| Endpoint | Method | Description | Request | Response |
|----------|--------|-------------|---------|----------|
| `/` | POST | Create + first message | `{content, resume_session_id?}` | SSE Stream |
| `/{id}/message` | POST | Send (non-streaming) | `{content}` | `{session_id, response, tool_uses[], ...}` |
| `/{id}/stream` | POST | Send (streaming) | `{content}` | SSE Stream |
| `/{id}/interrupt` | POST | Interrupt task | - | `{session_id, message}` |

#### Configuration Router (`/api/v1/config`)

| Endpoint | Method | Description | Response |
|----------|--------|-------------|----------|
| `/skills` | GET | List available skills | `{skills[], total}` |
| `/agents` | GET | List available agents | `{agents[], total}` |

---

### Example Client Implementation

```python
import httpx
import json

async def chat_with_streaming():
    async with httpx.AsyncClient() as client:
        # Create conversation with first message
        async with client.stream(
            "POST",
            "http://localhost:19830/api/v1/conversations",
            json={"content": "Hello, what can you help me with?"}
        ) as response:
            session_id = None
            async for line in response.aiter_lines():
                if line.startswith("event:"):
                    event_type = line[6:].strip()
                elif line.startswith("data:"):
                    data = json.loads(line[5:])

                    if event_type == "session_id":
                        session_id = data["session_id"]
                        print(f"Session: {session_id}")
                    elif event_type == "text_delta":
                        print(data["text"], end="", flush=True)
                    elif event_type == "done":
                        print(f"\n[Done - {data['turn_count']} turns]")

        # Send follow-up message
        async with client.stream(
            "POST",
            f"http://localhost:19830/api/v1/conversations/{session_id}/stream",
            json={"content": "Tell me more about that"}
        ) as response:
            async for line in response.aiter_lines():
                # Process events...
                pass
```

---

## Support

For Docker deployment issues:
1. Check [DOCKER.md](DOCKER.md) troubleshooting section
2. Verify logs: `docker compose logs -f claude-api`
3. Check health: `curl http://localhost:19830/health`
