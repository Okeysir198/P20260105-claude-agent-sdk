# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Claude Agent SDK Application - A full-stack chat application with a Python backend (Claude Agent SDK) and Next.js frontend. The project is organized into two main directories:

- **`backend/`** - Python FastAPI server wrapping Claude Agent SDK with Skills and Subagents support
- **`frontend/`** - Next.js chat UI with reusable components, SSE streaming, and Claude design language

## Commands

### Backend (Python)
```bash
cd backend

# Run CLI (interactive chat - default)
python main.py
python main.py --mode direct          # Explicit direct mode
python main.py --mode api             # API mode (requires running server)

# Start API server
python main.py serve                  # Default: 0.0.0.0:7001
python main.py serve --port 8080      # Custom port
python main.py serve --reload         # Auto-reload for development

# List resources
python main.py skills                 # List available skills
python main.py agents                 # List subagents
python main.py sessions               # List conversation history

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
│   │   │   ├── options.py    # ClaudeAgentOptions builder
│   │   │   ├── session.py    # ConversationSession
│   │   │   ├── storage.py    # Session storage
│   │   │   └── agents.py     # Subagent definitions
│   │   ├── discovery/        # Skills and MCP discovery
│   │   └── display/          # Rich console output
│   ├── api/                  # FastAPI HTTP/SSE server
│   │   ├── main.py           # FastAPI app
│   │   ├── routers/          # API endpoints
│   │   └── services/         # Business logic services
│   ├── cli/                  # Click-based CLI
│   ├── config.yaml           # Provider configuration
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

**Backend API Mode**: `frontend/` → `frontend/app/api/*` (proxy) → `backend/api/` → `ClaudeSDKClient`

**Direct Mode (CLI)**: `backend/cli/` → `backend/cli/clients/direct.py` → `ClaudeSDKClient`

## Configuration

### Backend
- **Provider switching**: Edit `backend/config.yaml`
- **Skills**: Add in `.claude/skills/<name>/SKILL.md`
- **Subagents**: Modify `backend/agent/core/agents.py`
- **MCP servers**: Configure in `backend/.mcp.json`

### Frontend
- **API URL**: Set `BACKEND_URL` in `frontend/.env.local`
- **Theme colors**: Override CSS variables in `frontend/styles/globals.css`
- **Components**: Import from `frontend/components/`

## API Endpoints (Backend)

- `GET /health` - Health check
- `GET /api/v1/sessions` - List sessions
- `POST /api/v1/sessions/{id}/resume` - Resume session
- `POST /api/v1/conversations` - Create conversation (SSE stream)
- `POST /api/v1/conversations/{id}/stream` - Send message (SSE stream)
- `POST /api/v1/conversations/{id}/interrupt` - Interrupt task
- `GET /api/v1/config/skills` - List skills
- `GET /api/v1/config/agents` - List agents

## Frontend Features

- **Chat Components**: Reusable message bubbles for user, assistant, tool_use, tool_result
- **SSE Streaming**: Real-time token streaming with `useClaudeChat` hook
- **Session Management**: History sidebar with `useSessions` hook
- **Theming**: Claude design language with dark mode support
- **Portable**: Copy `frontend/` folder to integrate with any project

## In Planning Mode

Always plan tasks to launch multiple subagents in parallel for higher code quality and efficiency during implementation.
