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

frontend/                        # Next.js 15 (port 7002)
├── app/
│   ├── (auth)/login/           # Login page
│   ├── api/auth/               # Login, logout, session, token routes
│   ├── api/proxy/              # REST API proxy
│   └── page.tsx                # Main chat page
├── components/
│   ├── chat/                   # Chat UI components
│   ├── session/                # Session sidebar + user profile
│   ├── features/auth/          # Login form, logout button
│   └── providers/              # Auth, Query, Theme providers
├── lib/
│   ├── store/                  # Zustand stores (chat, question, plan)
│   ├── session.ts              # Session cookie management
│   ├── websocket-manager.ts    # WebSocket with auto-token refresh
│   └── constants.ts            # Query keys, API constants
└── middleware.ts               # Route protection
```

## Commands

### Backend

```bash
cd backend && source .venv/bin/activate
python main.py serve --port 7001    # Start API server
python main.py chat                 # Interactive chat (prompts for password)
python main.py agents               # List agents
python main.py sessions             # List sessions
```

### Frontend

```bash
cd frontend
npm run dev                         # Dev server with Turbopack (port 7002)
npm run build                       # Production build
npm run lint                        # ESLint
```

## Code Patterns

### Frontend: WebSocket Message Handling

Located in `frontend/hooks/use-chat.ts`:
1. All WebSocket events handled in single switch statement
2. Use `useChatStore.getState()` to avoid closure staleness
3. Message creation: `{id, role, content, timestamp}` + optional fields
4. Store updates: `setPendingMessage()`, `updateLastMessage()`, `addMessage()`
5. Always invalidate queries after session changes

### Frontend: Component Organization

- **UI Components**: `/components/ui/` - Radix UI primitives
- **Feature Components**: `/components/{feature}/` - Domain-specific (chat, session, agent)
- **Providers**: `/components/providers/` - Context providers
- Use `'use client'` directive for client-side components

### Backend: Per-User Data Isolation

All user data stored in `backend/data/{username}/`:
- `sessions.json` - Active sessions metadata
- `history/{session_id}.jsonl` - Message history per session

Use `agent/core/storage.py` utilities for file operations. Never hardcode paths - use username from JWT token.

### Backend: Agent Configuration

Agents defined in `backend/agents.yaml`:

```yaml
agent-id-xyz123:
  name: "Display Name"
  description: "What this agent does"
  system_prompt: |
    Multi-line instructions (appended to default prompt)
  subagents:
    - reviewer
  tools:
    - Read
    - Write
    - Edit
    - Bash
    - Grep
    - Glob
    - Skill
    - Task
  model: sonnet  # haiku, sonnet, opus
```

**Important**: `system_prompt` is APPENDED to default prompt, not replacing it.

## Common Workflows

### Adding a New Agent

1. Edit `backend/agents.yaml`
2. Add agent entry with unique ID (format: `{name}-{random-suffix}`)
3. Define tools, model, and optional subagents
4. Restart backend server to reload config
5. Agent appears in frontend dropdown automatically

### Debugging WebSocket Issues

1. Check connection status indicator in chat header
2. Browser console for WebSocket errors
3. Backend logs for connection/auth errors
4. Common issues:
   - Session not found → Backend auto-recovers, starts new session
   - Token expired → Frontend auto-refreshes via `/api/auth/token`
   - Agent not found → Check `agents.yaml` and restart backend

### Modifying Chat UI

1. Message display: `frontend/components/chat/*-message.tsx`
2. Input handling: `frontend/components/chat/chat-input.tsx`
3. Store updates: `frontend/hooks/use-chat.ts`

### Adding New WebSocket Events

1. Backend: Add event to `backend/api/routers/websocket.py`
2. Frontend types: Add type to `frontend/types/index.ts`
3. Frontend handler: Add case to switch statement in `use-chat.ts`
4. Test with dev environment

### Session Search

Two search modes:
1. **Name Search** (MagnifyingGlass icon): Client-side by session name and first message
2. **Content Search** (FileSearch icon): Backend full-text search through history

**Content Search:**
- Searches all message types: `user`, `assistant`, `tool_use`, `tool_result`
- Case-insensitive, relevance-based ranking
- Returns contextual snippets with match counts
- API: `GET /api/v1/sessions/search?query=<term>&max_results=20`

### Adding User Authentication to API Routes

All authenticated routes require:
1. API key via `X-API-Key` header
2. User JWT via `Authorization: Bearer <token>` header
3. Dependency: `get_current_user()` from `backend/api/dependencies/auth.py`

## Testing

### Backend Tests

```bash
cd backend
pytest tests/ -v                    # Run all tests
pytest tests/test_websocket.py      # Run specific test file
```

Test files use pytest-asyncio for async WebSocket testing.

### Frontend Testing

Currently manual testing:
1. Start dev servers: `backend (7001)` and `frontend (7002)`
2. Login at `http://localhost:7002`
3. Test WebSocket connection, message flow, tool calls
4. Check browser console for errors

## Key Files Reference

### Backend Core

- `backend/main.py` - CLI entry point
- `backend/agents.yaml` - Agent definitions
- `backend/api/routers/websocket.py` - WebSocket handler
- `backend/agent/core/storage.py` - Per-user storage utilities
- `backend/api/services/session_service.py` - Session management

### Frontend Core

- `frontend/app/page.tsx` - Main chat page
- `frontend/hooks/use-chat.ts` - Chat WebSocket handler
- `frontend/hooks/use-websocket.ts` - WebSocket connection manager
- `frontend/lib/store/chat-store.ts` - Chat state management
- `frontend/lib/websocket-manager.ts` - WebSocket with token refresh
- `frontend/types/index.ts` - TypeScript types

## Deployment

Production URLs:
- Backend: `https://claude-agent-sdk-fastapi-sg4.tt-ai.org`
- Frontend: `https://claude-agent-sdk-chat.tt-ai.org`

See individual README files in `/backend/` and `/frontend/` for deployment details.
