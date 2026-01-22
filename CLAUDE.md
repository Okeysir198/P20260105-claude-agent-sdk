# CLAUDE.md

Guidance for Claude Code when working with this repository.

## Project Overview

**Claude Agent SDK CLI** - Interactive chat application wrapping the Claude Agent SDK with multi-agent support. Provides CLI and web interfaces with WebSocket/SSE streaming.

## Architecture

```
backend/
├── agent/
│   ├── agents.yaml          # Top-level agents (general, reviewer, doc-writer, researcher)
│   ├── subagents.yaml       # Delegation subagents
│   └── core/
│       ├── session.py       # ConversationSession (is_connected property)
│       ├── agent_options.py # create_agent_sdk_options(agent_id, resume_session_id)
│       └── storage.py       # SessionStorage + HistoryStorage (data/sessions.json, data/history/)
├── api/                     # FastAPI server (port 7001)
│   ├── main.py              # App factory with global exception handlers
│   ├── routers/
│   │   ├── websocket.py     # WebSocket endpoint for persistent multi-turn chat
│   │   ├── conversations.py # SSE streaming with agent_id support (legacy)
│   │   ├── sessions.py      # Session CRUD + history
│   │   └── configuration.py # List agents
│   ├── services/
│   │   ├── session_manager.py  # get_or_create_conversation_session(session_id, agent_id)
│   │   └── history_tracker.py  # Track and save conversation history
│   └── models/              # Pydantic request/response models
├── cli/                     # Click CLI
├── tests/                   # test_claude_agent_sdk*.py, test_api_agent_selection.py
└── data/
    ├── sessions.json        # Session metadata
    └── history/             # Message history (JSONL per session)

frontend/                    # Next.js 16 (port 7002)
├── app/                     # Next.js App Router pages
├── hooks/
│   ├── use-websocket.ts     # WebSocket connection management
│   ├── use-claude-chat.ts   # Main chat hook (uses WebSocket)
│   └── use-sessions.ts      # Session management
├── types/
│   └── events.ts            # WebSocket/SSE event types
└── lib/
    └── constants.ts         # API/WebSocket URLs
```

**Direct API Architecture:**
```
Development:
  Browser → http://localhost:7001/api/v1/* (direct)
  Browser → ws://localhost:7001/api/v1/ws/chat (direct)

Production:
  Frontend: https://claude-agent-sdk-chat.tt-ai.org (port 7002)
  Backend:  https://claude-agent-sdk-fastapi-sg4.tt-ai.org (port 7001)
  Browser → https://claude-agent-sdk-fastapi-sg4.tt-ai.org/api/v1/* (direct)
```

## Key Concepts

**Agent Selection:**
- Agents defined in `agents.yaml` with unique IDs: `{type}-{suffix}` (e.g., `code-reviewer-x9y8z7w6`)
- System prompt is APPENDED to default `claude_code` preset (not replaced)
- Select via `agent_id` query parameter in WebSocket connection

**WebSocket Flow:**
```
Browser connects: ws://localhost:7001/api/v1/ws/chat?agent_id=xxx
    ↓
Server sends: { type: 'ready' }
    ↓
Client sends: { content: 'user message' }
    ↓
Server streams: { type: 'text_delta', text: '...' }
Server sends: { type: 'done', turn_count: N }
```

**SSE Flow (Legacy/Direct API):**
```
POST /api/v1/conversations {content, agent_id}
  → SessionManager.get_or_create_conversation_session(session_id, agent_id)
  → create_agent_sdk_options(agent_id=agent_id)
  → Loads agent config from agents.yaml
  → SSE streaming response
```

**Message History:**
- Stored locally in `data/history/{session_id}.jsonl`
- Roles: `user`, `assistant`, `tool_use`, `tool_result`
- Retrieved via `GET /api/v1/sessions/{id}/history`

## Commands

```bash
# Backend Development
cd backend
uv sync && source .venv/bin/activate
cp .env.example .env  # Add ANTHROPIC_API_KEY
python main.py serve --port 7001

# CLI
python main.py agents    # List agents
python main.py sessions  # List sessions

# Tests
python tests/test_api_agent_selection.py  # API test (requires server)

# Frontend Development
cd frontend
npm install
npm run dev              # Next.js dev server (port 7002)

# Production
npm run build && npm start

# Docker (backend only)
cd backend && make build && make up
```

## API Endpoints

**Authentication:** All endpoints except `/health` require the `X-API-Key` header.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check (no auth required) |
| **WS** | `/api/v1/ws/chat` | **WebSocket for persistent multi-turn chat** |
| POST | `/api/v1/conversations` | Create conversation with `agent_id` (SSE) |
| POST | `/api/v1/conversations/{id}/stream` | Follow-up message (SSE) |
| POST | `/api/v1/conversations/{id}/interrupt` | Interrupt task |
| POST | `/api/v1/sessions` | Create session |
| GET | `/api/v1/sessions` | List sessions |
| GET | `/api/v1/sessions/{id}/history` | Get message history |
| POST | `/api/v1/sessions/{id}/resume` | Resume session |
| DELETE | `/api/v1/sessions/{id}` | Delete session + history |
| GET | `/api/v1/config/agents` | List available agents |

## Deployment

**Separate Tunnel Deployment (Cloudflare):**
```bash
# Start both servers
cd backend && python main.py serve --port 7001
cd frontend && npm run dev

# Backend tunnel
cloudflare tunnel --url http://localhost:7001 --hostname claude-agent-sdk-fastapi-sg4.tt-ai.org

# Frontend tunnel
cloudflare tunnel --url http://localhost:7002 --hostname claude-agent-sdk-chat.tt-ai.org
```

## Adding Agents

Edit `backend/agent/agents.yaml`:

```yaml
my-agent-abc123:
  name: "My Agent"
  type: "custom"
  description: "What this agent does"
  system_prompt: |
    Role-specific instructions (appended to claude_code preset)
  tools: [Skill, Task, Read, Write, Bash, Grep, Glob]
  subagents: [researcher, reviewer]
  model: sonnet  # haiku, sonnet, opus
  read_only: false
```

## Configuration

Provider in `backend/config.yaml`:
```yaml
provider: claude  # claude, zai, minimax, proxy
```

**Backend environment variables** (`.env`):
- `ANTHROPIC_API_KEY` - Anthropic API key (for claude provider)
- `API_KEY` - API key for authenticating requests to the backend
- `CORS_ORIGINS` - Comma-separated list of allowed CORS origins
- `ZAI_API_KEY`, `ZAI_BASE_URL` - (for zai provider)
- `MINIMAX_API_KEY`, `MINIMAX_BASE_URL` - (for minimax provider)
- `PROXY_BASE_URL` - (for proxy provider, default: `http://localhost:4000`)

**Frontend environment variables** (`.env.local`):
- `NEXT_PUBLIC_API_URL` - Backend API URL (e.g., `http://localhost:7001` or production URL)
- `NEXT_PUBLIC_API_KEY` - API key for authenticating requests to the backend
