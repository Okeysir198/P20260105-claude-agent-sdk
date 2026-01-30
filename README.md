# Claude Agent SDK Chat

Interactive chat application with multi-agent support and user authentication, built on the [Claude Agent SDK](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/sdk).

## Features

- **Two Chat Modes** - Web UI for browser-based chat, CLI for terminal-based chat
- **Multi-Agent Support** - Switch between specialized AI agents
- **Real-time Streaming** - WebSocket-based chat with persistent connections
- **User Authentication** - SQLite-based login with per-user data isolation
- **Session Management** - Save, resume, and manage conversation history
- **Interactive Questions** - Modal dialogs for agent clarification requests
- **Tool Visualization** - View tool calls and results in chat
- **Dark Mode** - System preference detection with manual toggle

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- API key (Anthropic, ZAI, Minimax) or [Claude Code Proxy](https://github.com/Okeysir198/P20260106-claude-code-proxy)

### Backend Setup

```bash
cd backend
uv sync && source .venv/bin/activate
cp .env.example .env
# Edit .env: set your API key and generate API_KEY
# Edit config.yaml: set your preferred provider
python main.py serve --port 7001
```

### Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env.local
# Edit .env.local: set API_KEY (same as backend) and BACKEND_API_URL
npm run dev
```

### Access

**Web UI:** http://localhost:7002
- Username: `admin` / Password: value of `CLI_ADMIN_PASSWORD`
- Username: `tester` / Password: value of `CLI_TESTER_PASSWORD`

**CLI:**
```bash
cd backend && source .venv/bin/activate
python main.py chat              # Chat with default agent
python main.py chat -a agent-id  # Chat with specific agent
python main.py agents            # List available agents
python main.py sessions          # List saved sessions
```

## Architecture

```
├── backend/                    # FastAPI server (port 7001)
│   ├── main.py                 # CLI entry point
│   ├── config.yaml             # Provider configuration
│   ├── agents.yaml             # Agent definitions
│   ├── subagents.yaml          # Delegation subagents
│   ├── agent/                  # Agent utilities + storage
│   ├── api/                    # Routers, services, middleware
│   ├── cli/                    # Click CLI
│   └── data/{username}/        # Per-user sessions & history
│
└── frontend/                   # Next.js 15 (port 7002)
    ├── app/                    # Pages + API routes
    ├── components/             # Chat, session, auth UI
    ├── hooks/                  # useChat, useWebSocket, useSessions
    ├── lib/                    # Stores, utilities
    └── types/                  # TypeScript definitions
```

## Documentation

| Document | Description |
|----------|-------------|
| [CLAUDE.md](./CLAUDE.md) | Development guide for Claude Code |
| [backend/README.md](./backend/README.md) | API reference, WebSocket protocol |
| [frontend/README.md](./frontend/README.md) | Frontend architecture, components |

## Provider Configuration

Backend supports multiple AI providers. Configure in `backend/config.yaml`:

```yaml
# Set active provider: "claude", "zai", "minimax", "proxy"
provider: claude

providers:
  claude:
    env_key: ANTHROPIC_API_KEY
  zai:
    env_key: ZAI_API_KEY
    base_url_env: ZAI_BASE_URL
  minimax:
    env_key: MINIMAX_API_KEY
    base_url_env: MINIMAX_BASE_URL
  proxy:
    base_url_env: PROXY_BASE_URL
```

For proxy setup, see [claude-code-proxy](https://github.com/Okeysir198/P20260106-claude-code-proxy).

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `ZAI_API_KEY` | ZAI API key |
| `ZAI_BASE_URL` | ZAI base URL |
| `MINIMAX_API_KEY` | Minimax API key |
| `MINIMAX_BASE_URL` | Minimax base URL |
| `PROXY_BASE_URL` | Proxy server URL |
| `API_KEY` | Shared secret for API auth |
| `CLI_ADMIN_PASSWORD` | Password for admin user |
| `CLI_TESTER_PASSWORD` | Password for tester user |

### Frontend (`frontend/.env.local`)

| Variable | Description |
|----------|-------------|
| `API_KEY` | Must match backend `API_KEY` |
| `BACKEND_API_URL` | Backend URL (e.g., `http://localhost:7001/api/v1`) |

## Security

- API keys never exposed to browser (server-side only)
- Passwords hashed with bcrypt
- JWT tokens with HMAC-SHA256 signing
- Session cookies with HttpOnly flag
- Per-user data isolation

## License

MIT
