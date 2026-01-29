# Claude Agent SDK Chat

Interactive chat application with multi-agent support and user authentication, built on the [Claude Agent SDK](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/sdk).

## Features

- **Two Chat Modes** - Web UI for browser-based chat, CLI for terminal-based chat
- **Multi-Agent Support** - Switch between specialized AI agents with different capabilities
- **Real-time Streaming** - WebSocket-based chat with persistent connections
- **User Authentication** - SQLite-based login with per-user data isolation
- **Session Management** - Save, resume, and manage conversation history
- **Interactive Questions** - Modal dialogs for agent clarification requests
- **Tool Visualization** - View tool calls and results in the chat
- **Dark Mode** - System preference detection with manual toggle

## Architecture

```
├── backend/                    # FastAPI server with Claude Agent SDK
│   ├── main.py                 # CLI entry point
│   ├── config.yaml             # Provider configuration (claude/zai/minimax/proxy)
│   ├── agents.yaml             # Agent definitions
│   ├── subagents.yaml          # Delegation subagents
│   ├── agent/
│   │   ├── core/               # Agent utilities (config, session, storage)
│   │   └── display/            # Console display formatting
│   ├── api/
│   │   ├── db/                 # SQLite user database
│   │   ├── middleware/         # API key + JWT authentication
│   │   ├── routers/            # WebSocket, sessions, auth endpoints
│   │   ├── services/           # Session, history, token services
│   │   └── models/             # Pydantic request/response models
│   ├── cli/
│   │   ├── commands/           # chat, serve, list commands
│   │   └── clients/            # API/WebSocket clients
│   └── data/{username}/        # Per-user sessions & history
│
└── frontend/                   # Next.js 15 web application
    ├── app/
    │   ├── (auth)/login/       # Login page
    │   ├── api/auth/           # Auth API routes (login, logout, token)
    │   ├── api/proxy/          # Backend API proxy
    │   ├── s/[sessionId]/      # Session URL routing
    │   └── page.tsx            # Main chat page
    ├── components/
    │   ├── chat/               # Message list, input, modals
    │   ├── agent/              # Agent grid & switcher
    │   ├── session/            # Session sidebar
    │   ├── features/auth/      # Login form, logout button
    │   ├── providers/          # Auth, Query, Theme providers
    │   └── ui/                 # Radix UI primitives
    ├── hooks/                  # useChat, useWebSocket, useSessions
    ├── lib/
    │   ├── store/              # Zustand stores (chat, ui, question)
    │   └── websocket-manager.ts
    └── types/                  # TypeScript definitions
```

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- API key (Anthropic, ZAI, Minimax) or a [Claude Code Proxy](https://github.com/Okeysir198/P20260106-claude-code-proxy)

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

**Web UI:** Open http://localhost:7002 and log in with credentials configured in backend `.env`:
- Username: `admin` / Password: value of `CLI_ADMIN_PASSWORD`
- Username: `tester` / Password: value of `CLI_TESTER_PASSWORD`

**CLI:** Run interactive chat directly from terminal:
```bash
cd backend && source .venv/bin/activate
python main.py chat              # Chat with default agent
python main.py chat -a agent-id  # Chat with specific agent
python main.py agents            # List available agents
python main.py sessions          # List saved sessions
```

## Documentation

| Document | Description |
|----------|-------------|
| [CLAUDE.md](./CLAUDE.md) | Development guide for Claude Code - architecture, patterns, workflows |
| [backend/README.md](./backend/README.md) | API reference, WebSocket protocol, CLI commands |
| [frontend/README.md](./frontend/README.md) | Frontend architecture, components, theming |

## Provider Configuration

The backend supports multiple AI providers. Configure in `backend/config.yaml`:

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

### Using a Proxy

For self-hosted or custom proxy setups, see [claude-code-proxy](https://github.com/Okeysir198/P20260106-claude-code-proxy).

Set `provider: proxy` in `config.yaml` and configure `PROXY_BASE_URL` in `.env`.

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic API key (if using `claude` provider) |
| `ZAI_API_KEY` | ZAI API key (if using `zai` provider) |
| `ZAI_BASE_URL` | ZAI base URL: `https://api.z.ai/api/anthropic` |
| `MINIMAX_API_KEY` | Minimax API key (if using `minimax` provider) |
| `MINIMAX_BASE_URL` | Minimax base URL: `https://api.minimax.io/anthropic` |
| `PROXY_BASE_URL` | Proxy server URL (if using `proxy` provider) |
| `API_KEY` | Shared secret for API authentication (generate with `openssl rand -hex 32`) |
| `CLI_ADMIN_PASSWORD` | Password for admin user |
| `CLI_TESTER_PASSWORD` | Password for tester user |

### Frontend (`frontend/.env.local`)

| Variable | Description |
|----------|-------------|
| `API_KEY` | Must match backend `API_KEY` |
| `BACKEND_API_URL` | Backend URL (e.g., `http://localhost:7001/api/v1`) |

## Security

- API keys are never exposed to the browser (server-side only)
- Passwords are hashed with bcrypt
- JWT tokens with HMAC-SHA256 signing
- Session cookies with HttpOnly flag
- Per-user data isolation

## License

MIT
