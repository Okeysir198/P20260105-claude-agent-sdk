# Claude Agent SDK Chat

Interactive chat application with multi-agent support and user authentication, built on the Claude Agent SDK.

## Features

- **User Authentication** - SQLite-based login with per-user data isolation
- **Multi-Agent Support** - Switch between specialized agents
- **WebSocket Streaming** - Real-time chat with persistent connections
- **Session Management** - Save, resume, and manage conversation history
- **Interactive Questions** - AskUserQuestion modal for clarification
- **Dark Mode** - System preference detection with manual toggle

## Quick Start

### Backend

```bash
cd backend
uv sync && source .venv/bin/activate
cp .env.example .env   # Configure API keys and CLI_PASSWORD
python main.py serve --port 7001
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local   # Configure API_KEY and BACKEND_API_URL
npm run dev   # Starts on port 7002
```

### Login

Open http://localhost:7002 and login with:
- Username: `admin`
- Password: (value of CLI_PASSWORD from backend .env)

## Architecture

```
backend/                         # FastAPI (port 7001)
├── api/db/                     # SQLite user database
├── api/routers/                # WebSocket, REST, auth endpoints
├── data/{username}/            # Per-user sessions + history
└── agents.yaml                 # Agent definitions

frontend/                        # Next.js 16 (port 7002)
├── app/(auth)/login/           # Login page
├── app/api/                    # Proxy routes (auth, REST)
├── middleware.ts               # Route protection
└── components/                 # Chat UI, session sidebar
```

## Environment Variables

### Backend (.env)

```bash
ANTHROPIC_API_KEY=sk-ant-...
API_KEY=your-api-key              # Generate: openssl rand -hex 32
CORS_ORIGINS=https://your-frontend-url.com

# User credentials for CLI
CLI_USERNAME=admin
CLI_PASSWORD=your-secure-password
```

### Frontend (.env.local)

```bash
API_KEY=your-api-key
BACKEND_API_URL=https://claude-agent-sdk-fastapi-sg4.tt-ai.org/api/v1
NEXT_PUBLIC_WS_URL=wss://claude-agent-sdk-fastapi-sg4.tt-ai.org/api/v1/ws/chat
```

## Available Agents

| Agent | Description | Model |
|-------|-------------|-------|
| General Assistant | General-purpose coding (default) | sonnet |
| Code Reviewer | Code reviews and security | sonnet |
| Documentation Writer | Documentation generation | sonnet |
| Code Researcher | Codebase exploration (read-only) | haiku |
| Sandbox Agent | Restricted permissions | sonnet |

## Documentation

- [Backend README](backend/README.md) - API details, WebSocket protocol
- [Frontend README](frontend/README.md) - UI components, hooks
- [CLAUDE.md](CLAUDE.md) - Development guide for Claude Code

## License

MIT
