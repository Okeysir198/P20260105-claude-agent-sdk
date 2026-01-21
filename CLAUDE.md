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
├── server.js                # Custom Express server with WebSocket proxy
├── app/
│   └── api/                 # Next.js API routes (sessions, config, interrupt)
├── hooks/
│   ├── use-websocket.ts     # WebSocket connection management
│   ├── use-claude-chat.ts   # Main chat hook (uses WebSocket)
│   └── use-sessions.ts      # Session management
├── types/
│   └── events.ts            # WebSocket/SSE event types
└── lib/
    ├── constants.ts         # API/WebSocket URLs
    └── api-proxy.ts         # Shared proxyToBackend() utility
```

## Key Concepts

**Agent Selection:**
- Agents defined in `agents.yaml` with unique IDs: `{type}-{suffix}` (e.g., `code-reviewer-x9y8z7w6`)
- System prompt is APPENDED to default `claude_code` preset (not replaced)
- Select via `agent_id` query parameter in WebSocket connection

**WebSocket Flow (Frontend):**
```
Browser connects: ws://localhost:7002/ws/chat?agent_id=xxx
    ↓
Custom server.js proxies to: ws://localhost:7001/api/v1/ws/chat?agent_id=xxx
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
npm run dev              # Custom server with WebSocket proxy (recommended)
npm run dev:next         # Next.js only (no WebSocket proxy)

# Production
npm run build && npm start

# Docker (backend only)
cd backend && make build && make up
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
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

## Frontend WebSocket Proxy

The frontend uses a custom Express server (`server.js`) to proxy WebSocket connections:

```
Browser                    Frontend (server.js)              Backend
   │                              │                              │
   ├── /ws/chat ────────────────►├── /api/v1/ws/chat ─────────►│
   │   (WebSocket)                │   (WebSocket proxy)          │
   │                              │                              │
   ├── /api/proxy/* ────────────►├── /api/v1/* ───────────────►│
   │   (REST)                     │   (HTTP proxy)               │
   │                              │                              │
   ├── /* ──────────────────────►├── Next.js ──────────────────►│
       (Pages)                        (SSR/Static)
```

**Single Tunnel Deployment (Cloudflare):**
```bash
# Start both servers
cd backend && python main.py serve --port 7001
cd frontend && npm run dev

# Single tunnel for everything
cloudflare tunnel --url http://localhost:7002
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

Environment variables in `.env`:
- `ANTHROPIC_API_KEY` (for claude)
- `ZAI_API_KEY`, `ZAI_BASE_URL` (for zai)
- `MINIMAX_API_KEY`, `MINIMAX_BASE_URL` (for minimax)
- `PROXY_BASE_URL` (for proxy, default: `http://localhost:4000`)

Frontend environment (`.env.local`):
- `BACKEND_URL` - Backend URL for proxy (default: `http://localhost:7001`)
- `NEXT_PUBLIC_WS_URL` - Override WebSocket URL (auto-detected by default)
