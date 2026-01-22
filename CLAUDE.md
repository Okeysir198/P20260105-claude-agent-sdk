# CLAUDE.md

Development guide for Claude Code when working with this repository.

## Project Overview

**Claude Agent SDK Chat** - Interactive chat application with multi-agent support. Provides web interface and CLI with WebSocket/SSE streaming.

## Architecture

```
backend/                         # FastAPI server (port 7001)
├── agent/
│   ├── agents.yaml              # Agent definitions
│   ├── subagents.yaml           # Delegation subagents
│   └── core/
│       ├── agent_options.py     # create_agent_sdk_options()
│       └── storage.py           # SessionStorage + HistoryStorage
├── api/
│   ├── main.py                  # FastAPI app factory
│   ├── middleware/auth.py       # API key authentication
│   ├── routers/
│   │   ├── websocket.py         # WebSocket endpoint
│   │   ├── conversations.py     # SSE streaming
│   │   ├── sessions.py          # Session CRUD
│   │   └── configuration.py     # List agents
│   └── services/
│       ├── session_manager.py   # Session management
│       └── history_tracker.py   # Message history
├── cli/
│   ├── main.py                  # Click CLI
│   ├── commands/                # chat, serve, list commands
│   └── clients/                 # API + WebSocket clients
└── data/
    ├── sessions.json            # Session metadata
    └── history/                 # JSONL per session

frontend/                        # Next.js 16 (port 7002)
├── app/
│   └── page.tsx                 # Main chat page
├── components/
│   ├── chat/                    # Chat UI components
│   └── session/                 # Session sidebar
├── hooks/
│   ├── use-claude-chat.ts       # Chat hook (WebSocket)
│   ├── use-agents.ts            # Fetch agents from API
│   ├── use-sessions.ts          # Session management
│   └── use-websocket.ts         # WebSocket connection
└── lib/
    ├── api-client.ts            # HTTP client with auth
    └── constants.ts             # API URLs
```

## Authentication

All endpoints except `/health` require API key:
- **REST API:** `X-API-Key` header only (query params rejected for security)
- **WebSocket:** `api_key` query param (browser cannot send headers)

Security features:
- Timing-safe comparison (`secrets.compare_digest`)
- Auth failures logged with IP (keys never logged)
- CORS wildcard warning on startup

Backend middleware: `api/middleware/auth.py`
Frontend: `lib/api-client.ts` (header) + `hooks/use-claude-chat.ts` (query param for WS)

## Key Flows

**WebSocket Chat:**
```
Connect: ws://host/api/v1/ws/chat?api_key=KEY&agent_id=ID
← {"type": "ready"}
→ {"content": "Hello"}
← {"type": "session_id", "session_id": "uuid"}
← {"type": "text_delta", "text": "..."}
← {"type": "done", "turn_count": 1}
```

**Agent Selection (Frontend):**
```
page.tsx
  └─ useAgents() → GET /api/v1/config/agents
  └─ useState(selectedAgentId)
  └─ ChatContainer
       └─ useClaudeChat({ agentId })
            └─ WebSocket with agent_id param
```

## Commands

```bash
# Backend
cd backend && source .venv/bin/activate
python main.py serve --port 7001
python main.py chat
python main.py agents

# Frontend
cd frontend
npm run dev
npm run build
```

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/health` | No | Health check |
| WS | `/api/v1/ws/chat` | Yes | WebSocket chat |
| POST | `/api/v1/conversations` | Yes | SSE streaming |
| GET | `/api/v1/sessions` | Yes | List sessions |
| GET | `/api/v1/sessions/{id}/history` | Yes | Message history |
| DELETE | `/api/v1/sessions/{id}` | Yes | Delete session |
| GET | `/api/v1/config/agents` | Yes | List agents |

## Adding Agents

Edit `backend/agent/agents.yaml`:

```yaml
my-agent-abc123:
  name: "My Agent"
  description: "What it does"
  system_prompt: |
    Instructions (appended to claude_code preset)
  tools: [Read, Write, Bash, Grep, Glob]
  model: sonnet
  is_default: false
```

## Environment Variables

**Backend (.env):**
```
ANTHROPIC_API_KEY=sk-ant-...
# Generate secure key: openssl rand -hex 32
API_KEY=your-key
CORS_ORIGINS=http://localhost:7002
```

**Frontend (.env.local):**
```
NEXT_PUBLIC_API_URL=http://localhost:7001/api/v1
NEXT_PUBLIC_API_KEY=your-key
```

## Deployment

```bash
# Backend tunnel
cloudflare tunnel --url http://localhost:7001 --hostname api.domain.com

# Frontend tunnel
cloudflare tunnel --url http://localhost:7002 --hostname app.domain.com
```

Production URLs:
- Backend: `https://claude-agent-sdk-fastapi-sg4.tt-ai.org`
- Frontend: `https://claude-agent-sdk-chat.tt-ai.org`
