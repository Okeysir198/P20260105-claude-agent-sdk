# CLAUDE.md

Development guide for Claude Code when working with this repository.

## Development Rules

**IMPORTANT: Always use the production backend URL.** Never use localhost for backend connections.

- Backend URL: `https://claude-agent-sdk-fastapi-sg4.tt-ai.org`
- WebSocket URL: `wss://claude-agent-sdk-fastapi-sg4.tt-ai.org/api/v1/ws/chat`

## Project Overview

**Claude Agent SDK Chat** - Interactive chat application with multi-agent support and user authentication. Provides web interface and CLI with WebSocket/SSE streaming.

## Architecture

```
backend/                         # FastAPI server (port 7001)
├── agents.yaml                 # Agent definitions
├── subagents.yaml              # Delegation subagents
├── agent/core/                 # Agent utilities + per-user storage
├── api/
│   ├── db/                     # SQLite user database
│   ├── dependencies/           # Auth dependencies
│   ├── middleware/             # API key + JWT auth
│   ├── routers/                # WebSocket, SSE, sessions, user_auth
│   ├── services/               # Session, history, token services
│   └── models/                 # Pydantic models
├── cli/                        # Click CLI with user login
└── data/{username}/            # Per-user sessions + history

frontend/                        # Next.js 16 (port 7002)
├── app/
│   ├── (auth)/login/           # Login page
│   ├── api/auth/               # Login, logout, session, token routes
│   ├── api/proxy/              # REST API proxy
│   └── page.tsx                # Main chat page
├── components/
│   ├── chat/                   # Chat UI
│   ├── session/                # Session sidebar + user profile
│   ├── features/auth/          # Login form, logout button
│   └── providers/              # Auth, Query, Theme providers
├── lib/
│   ├── session.ts              # Session cookie management
│   └── websocket-manager.ts    # WebSocket with auto-token
└── middleware.ts               # Route protection
```

## Authentication

### User Authentication Flow

```
1. User visits / (unauthenticated)
   └── middleware.ts redirects to /login

2. User logs in via /api/auth/login
   └── Backend validates against SQLite (data/users.db)
   └── Returns JWT with user_identity type
   └── Frontend sets HttpOnly session cookie

3. WebSocket connection
   └── /api/auth/token creates user_identity JWT from session
   └── WebSocket connects with token containing username
   └── Backend uses username for per-user storage
```

### Default Users

| Username | Password | Role |
|----------|----------|------|
| admin | (from CLI_PASSWORD env) | admin |
| tester | (from CLI_PASSWORD env) | user |

### Per-User Data Isolation

```
backend/data/
├── users.db              # SQLite user database
├── admin/                # Admin user data
│   ├── sessions.json
│   └── history/{session_id}.jsonl
└── tester/               # Tester user data
    └── ...
```

## Commands

```bash
# Backend
cd backend && source .venv/bin/activate
python main.py serve --port 7001    # Start API server
python main.py chat                 # Interactive chat (prompts for password)
python main.py agents               # List agents

# Frontend
cd frontend
npm run dev                         # Dev server (port 7002)
npm run build                       # Production build
```

## API Endpoints

### User Authentication

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/auth/login` | API Key | User login, returns JWT |
| POST | `/api/v1/auth/logout` | API Key | User logout |
| GET | `/api/v1/auth/me` | API Key + JWT | Get current user |

### WebSocket & Sessions

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| WS | `/api/v1/ws/chat` | JWT (user_identity) | WebSocket chat |
| GET | `/api/v1/sessions` | API Key + User | List user's sessions |
| DELETE | `/api/v1/sessions/{id}` | API Key + User | Delete session |

### Configuration

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/health` | None | Health check |
| GET | `/api/v1/config/agents` | API Key | List agents |

## Environment Variables

### Backend (.env)

```bash
ANTHROPIC_API_KEY=sk-ant-...
API_KEY=your-api-key              # REST API auth + JWT derivation
CORS_ORIGINS=https://claude-agent-sdk-chat.tt-ai.org

# CLI user credentials (no hardcoded defaults)
CLI_USERNAME=admin
CLI_PASSWORD=your-password
```

### Frontend (.env.local)

```bash
# Server-only (never exposed to browser)
API_KEY=your-api-key
BACKEND_API_URL=https://claude-agent-sdk-fastapi-sg4.tt-ai.org/api/v1

# Public (browser-accessible)
NEXT_PUBLIC_WS_URL=wss://claude-agent-sdk-fastapi-sg4.tt-ai.org/api/v1/ws/chat
```

## Adding Agents

Edit `backend/agents.yaml`:

```yaml
my-agent-abc123:
  name: "My Agent"
  description: "What it does"
  system_prompt: |
    Instructions
  tools: [Read, Write, Edit, Bash, Grep, Glob]
  model: sonnet  # haiku, sonnet, opus
```

## Deployment

Production URLs:
- Backend: `https://claude-agent-sdk-fastapi-sg4.tt-ai.org`
- Frontend: `https://claude-agent-sdk-chat.tt-ai.org`
