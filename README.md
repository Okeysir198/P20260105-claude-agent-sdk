# Claude Agent SDK Chat

Interactive chat application with multi-agent support and user authentication, built on the [Claude Agent SDK](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/sdk).

## Features

- **Multi-Agent Support** - Switch between specialized AI agents with different capabilities
- **Real-time Streaming** - WebSocket-based chat with persistent connections
- **User Authentication** - SQLite-based login with per-user data isolation
- **Session Management** - Save, resume, and manage conversation history
- **Interactive Questions** - Modal dialogs for agent clarification requests
- **Tool Visualization** - View tool calls and results in the chat
- **Dark Mode** - System preference detection with manual toggle

## Architecture

```
├── backend/          # FastAPI server with Claude Agent SDK
│   ├── agents.yaml   # Agent definitions
│   ├── api/          # REST & WebSocket endpoints
│   └── cli/          # Command-line interface
│
└── frontend/         # Next.js 15 web application
    ├── app/          # App router pages & API routes
    ├── components/   # React components
    └── hooks/        # Custom React hooks
```

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Anthropic API key

### Backend Setup

```bash
cd backend
uv sync && source .venv/bin/activate
cp .env.example .env
# Edit .env: set ANTHROPIC_API_KEY and generate API_KEY
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

Open http://localhost:7002 and log in with credentials configured in backend `.env`:
- Username: `admin` / Password: value of `CLI_ADMIN_PASSWORD`
- Username: `tester` / Password: value of `CLI_TESTER_PASSWORD`

## Documentation

| Document | Description |
|----------|-------------|
| [CLAUDE.md](./CLAUDE.md) | Development guide for Claude Code - architecture, patterns, workflows |
| [backend/README.md](./backend/README.md) | API reference, WebSocket protocol, CLI commands |
| [frontend/README.md](./frontend/README.md) | Frontend architecture, components, theming |

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key |
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
