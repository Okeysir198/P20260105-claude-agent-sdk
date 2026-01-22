# Claude Agent SDK Chat

Interactive chat application with multi-agent support, built on the Claude Agent SDK. Provides a web interface and CLI with WebSocket/SSE streaming.

## Features

- **Multi-Agent Support** - Switch between specialized agents (General, Code Reviewer, Doc Writer, Researcher)
- **WebSocket Streaming** - Real-time, low-latency chat with persistent connections
- **Session Management** - Save, resume, and manage conversation history
- **API Key Authentication** - Secure header-based auth with timing-safe comparison

## Quick Start

### Backend

```bash
cd backend
uv sync && source .venv/bin/activate
cp .env.example .env   # Add ANTHROPIC_API_KEY and API_KEY
python main.py serve --port 7001
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local   # Set NEXT_PUBLIC_API_URL and NEXT_PUBLIC_API_KEY
npm run dev   # Starts on port 7002
```

### Verify

```bash
# Health check (no auth)
curl http://localhost:7001/health

# List agents (with auth)
curl -H "X-API-Key: your-api-key" http://localhost:7001/api/v1/config/agents
```

## Architecture

```
├── backend/                 # FastAPI server (Python)
│   ├── api/                 # REST + WebSocket endpoints
│   ├── agent/               # Agent configurations (agents.yaml)
│   ├── cli/                 # Command-line interface
│   └── data/                # Session storage
│
└── frontend/                # Next.js 16 application
    ├── app/                 # Pages (App Router)
    ├── components/          # React components
    └── hooks/               # Custom hooks (useClaudeChat, useAgents, useSessions)
```

## API Endpoints

All endpoints except `/health` require authentication:
- **REST API:** `X-API-Key` header (query params rejected for security)
- **WebSocket:** `api_key` query parameter (browser limitation)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check (no auth) |
| **WS** | `/api/v1/ws/chat` | WebSocket for multi-turn chat |
| POST | `/api/v1/conversations` | Create conversation (SSE) |
| POST | `/api/v1/conversations/{id}/stream` | Follow-up message (SSE) |
| GET | `/api/v1/sessions` | List sessions |
| GET | `/api/v1/sessions/{id}/history` | Get message history |
| DELETE | `/api/v1/sessions/{id}` | Delete session |
| GET | `/api/v1/config/agents` | List available agents |

## WebSocket Protocol

```
Connect: ws://localhost:7001/api/v1/ws/chat?api_key=KEY&agent_id=AGENT_ID

← {"type": "ready"}
→ {"content": "Hello!"}
← {"type": "session_id", "session_id": "uuid"}
← {"type": "text_delta", "text": "Hi"}
← {"type": "text_delta", "text": " there!"}
← {"type": "done", "turn_count": 1}
```

## Available Agents

| Agent ID | Name | Description |
|----------|------|-------------|
| `general-agent-a1b2c3d4` | General Assistant | General-purpose coding assistant (default) |
| `code-reviewer-x9y8z7w6` | Code Reviewer | Code reviews and security analysis |
| `doc-writer-m5n6o7p8` | Documentation Writer | Documentation generation |
| `research-agent-q1r2s3t4` | Code Researcher | Codebase exploration (read-only) |

## Configuration

### Backend (.env)

```bash
ANTHROPIC_API_KEY=sk-ant-...     # Required for Claude provider
# API authentication (generate with: openssl rand -hex 32)
API_KEY=your-secure-key
CORS_ORIGINS=http://localhost:7002,https://your-domain.com
```

### Frontend (.env.local)

```bash
NEXT_PUBLIC_API_URL=http://localhost:7001/api/v1
NEXT_PUBLIC_API_KEY=your-secure-key
```

## CLI Commands

```bash
cd backend

python main.py serve              # Start API server
python main.py chat               # Interactive chat (WebSocket)
python main.py chat --mode sse    # Interactive chat (HTTP SSE)
python main.py agents             # List agents
python main.py sessions           # List sessions
```

## Custom Agents

Add to `backend/agent/agents.yaml`:

```yaml
my-agent-abc123:
  name: "My Agent"
  description: "What this agent does"
  system_prompt: |
    Your instructions here
  tools: [Read, Write, Bash, Grep, Glob]
  model: sonnet
  is_default: false
```

## Deployment

### Cloudflare Tunnels

```bash
# Backend
cloudflare tunnel --url http://localhost:7001 --hostname api.your-domain.com

# Frontend
cloudflare tunnel --url http://localhost:7002 --hostname app.your-domain.com
```

### Docker (Backend)

```bash
cd backend
make build && make up
```

## Documentation

- [Backend README](backend/README.md) - API details and configuration
- [Frontend README](frontend/README.md) - UI components and hooks
- [CLAUDE.md](CLAUDE.md) - Development guide for Claude Code

## License

MIT
