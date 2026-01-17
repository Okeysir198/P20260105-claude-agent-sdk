# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Claude Agent SDK Application - A full-stack chat application with a Python backend (Claude Agent SDK) and Next.js frontend. The project is organized into two main directories:

- **`backend/`** - Python FastAPI server wrapping Claude Agent SDK with Skills, Subagents, and Top-level Agents support
- **`frontend/`** - Next.js chat UI with reusable components, SSE streaming, and Claude design language

## Commands

### Backend (Python)
```bash
cd backend

# Run CLI (interactive chat - default)
python main.py
python main.py --mode direct          # Explicit direct mode

# Start API server
python main.py serve                  # Default: 0.0.0.0:7001
python main.py serve --port 8080      # Custom port

# List resources
python main.py skills                 # List available skills
python main.py agents                 # List top-level agents
python main.py subagents              # List subagents (delegation agents)
python main.py sessions               # List session history

# Resume session
python main.py --session-id <id>      # Resume existing session
```

### Frontend (Next.js)
```bash
cd frontend

npm install                           # Install dependencies
npm run dev                           # Start dev server (port 7002)
npm run build                         # Production build
npm run start                         # Start production server
```

## Architecture

```
├── backend/                  # Python backend
│   ├── agent/                # Core business logic
│   │   ├── core/
│   │   │   ├── agent_options.py  # ClaudeAgentOptions builder
│   │   │   ├── session.py        # ConversationSession wrapper
│   │   │   ├── storage.py        # Session storage (sessions.json)
│   │   │   ├── agents.py         # Top-level agent definitions
│   │   │   ├── subagents.py      # Subagent definitions (delegation)
│   │   │   ├── hook.py           # Permission hooks
│   │   │   └── config.py         # Configuration loading
│   │   ├── discovery/        # Skills and MCP discovery
│   │   └── display/          # Rich console output
│   ├── api/                  # FastAPI HTTP/SSE server
│   │   ├── main.py           # FastAPI app with lifespan
│   │   ├── routers/          # API endpoints
│   │   │   ├── health.py         # Health check
│   │   │   ├── sessions.py       # Session CRUD & history
│   │   │   ├── conversations.py  # Message streaming
│   │   │   └── configuration.py  # Skills/agents listing
│   │   ├── services/         # Business logic services
│   │   │   ├── client_pool.py       # SDK client pool management
│   │   │   ├── session_manager.py   # Session lifecycle (pending->active)
│   │   │   ├── conversation_service.py  # Message handling
│   │   │   ├── history_storage.py  # Message persistence
│   │   │   └── message_utils.py    # Message formatting
│   │   ├── core/             # Error handling
│   │   └── dependencies.py   # Dependency injection
│   ├── cli/                  # Click-based CLI
│   │   ├── commands/         # CLI command handlers
│   │   └── clients/          # Direct and API clients
│   ├── data/                 # Runtime data directory
│   │   ├── sessions.json     # Session metadata
│   │   └── history/          # Message history files
│   ├── config.yaml           # Provider configuration
│   ├── agents.yaml           # Top-level agent definitions
│   ├── subagents.yaml        # Subagent definitions
│   ├── main.py               # Entry point
│   └── requirements.txt      # Python dependencies
│
├── frontend/                 # Next.js frontend
│   ├── app/                  # Next.js App Router
│   │   ├── api/              # API proxy routes (SSE)
│   │   ├── layout.tsx        # Root layout
│   │   └── page.tsx          # Main chat page
│   ├── components/
│   │   ├── chat/             # Chat components
│   │   ├── session/          # Session sidebar
│   │   ├── ui/               # shadcn/ui components
│   │   └── providers/        # Context providers
│   ├── hooks/                # React hooks
│   ├── types/                # TypeScript types
│   ├── lib/                  # Utilities
│   └── styles/               # Global CSS
│
├── .claude/                  # Claude Code config & skills
└── README.md                 # Project documentation
```

## Key Data Flows

**Backend API Mode**: `frontend/` → `frontend/app/api/*` (proxy) → `backend/api/routers/*` → `ConversationService` → `SessionManager` → `ClientPool` → `ClaudeSDKClient`

**Direct Mode (CLI)**: `backend/cli/` → `backend/cli/clients/direct.py` → `ClaudeSDKClient`

**Session Lifecycle**:
1. `POST /api/v1/sessions` → Creates pending session ID (e.g., `pending-1234567890`)
2. `POST /api/v1/conversations` → Acquires client from `ClientPool`, sends first message, converts pending→real SDK ID
3. Follow-up messages use real SDK session ID from pool client

**Client Pool Architecture**:
- Fixed-size pool of `ClaudeSDKClient` instances (configurable via `CLIENT_POOL_SIZE`)
- Each client is acquired/released by sessions using async locks
- Prevents connection overhead and limits resource usage
- Pool is initialized at startup, cleaned up at shutdown
- Sessions timeout after 1 hour of inactivity (TTL)

## Configuration

### Backend
- **Provider switching**: Edit `backend/config.yaml`
- **Skills**: Add in `.claude/skills/<name>/SKILL.md`
- **Top-level agents**: Edit `backend/agents.yaml` (complete agent configurations)
- **Subagents**: Edit `backend/subagents.yaml` (delegation agents used via Task tool)
- **MCP servers**: Configure in `backend/.mcp.json`
- **Client pool size**: Set `CLIENT_POOL_SIZE` environment variable (default: 5)

### Frontend
- **API URL**: Set `BACKEND_URL` in `frontend/.env.local`
- **Theme colors**: Override CSS variables in `frontend/styles/globals.css`
- **Components**: Import from `frontend/components/`

## Terminology

- **Session**: A conversation context with a unique ID. Sessions can be active (in-memory with a pool client) or historical (persisted to storage).
- **Conversation**: The act of exchanging messages within a session. The `/conversations` endpoints handle message streaming.
- **Top-level Agents**: Complete agent configurations defined in `agents.yaml`. Each has specific models, tools, permissions, and capabilities. Select one when creating a session.
- **Subagents**: Specialized agents defined in `subagents.yaml` used internally via the Task tool for delegation (e.g., researcher, reviewer).
- **Pending Session**: Temporary session ID (`pending-xxx`) created before the first message. Converted to real SDK ID after first message.
- **Client Pool**: Fixed-size pool of reusable `ClaudeSDKClient` instances. Sessions acquire/release clients from this pool.

## API Endpoints (Backend)

### Health
- `GET /health` - Health check

### Sessions
- `POST /api/v1/sessions` - Create new session (returns pending ID)
- `GET /api/v1/sessions` - List all sessions (active + history)
- `GET /api/v1/sessions/{id}` - Get session info
- `POST /api/v1/sessions/{id}/resume` - Resume specific session
- `POST /api/v1/sessions/resume` - Resume most recent session
- `GET /api/v1/sessions/{id}/previous` - Get previous session in history
- `POST /api/v1/sessions/{id}/close` - Close session (keeps history)
- `DELETE /api/v1/sessions/{id}` - Delete session (removes from history)
- `GET /api/v1/sessions/{id}/history` - Get session message history

### Conversations
- `POST /api/v1/conversations` - Create conversation with first message (SSE stream)
- `POST /api/v1/conversations/{id}/message` - Send message (non-streaming)
- `POST /api/v1/conversations/{id}/stream` - Send message (SSE stream)
- `POST /api/v1/conversations/{id}/interrupt` - Interrupt current task

### Configuration
- `GET /api/v1/config/skills` - List available skills
- `GET /api/v1/config/agents` - List top-level agents
- `GET /api/v1/config/subagents` - List subagents

## Frontend Features

- **Chat Components**: Reusable message bubbles for user, assistant, tool_use, tool_result
- **SSE Streaming**: Real-time token streaming with `useClaudeChat` hook
- **Session Management**: History sidebar with `useSessions` hook
- **Theming**: Claude design language with dark mode support
- **Portable**: Copy `frontend/` folder to integrate with any project

## In Planning Mode

Always plan tasks to launch multiple subagents in parallel for higher code quality and efficiency during implementation.
