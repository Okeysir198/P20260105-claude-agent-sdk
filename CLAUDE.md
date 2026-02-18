# CLAUDE.md

Development guide for Claude Code when working with this repository.

## Development Rules

**IMPORTANT: Always use the production backend URL.** Never use localhost for backend connections. Frontend code must always call the backend via its production URL, never `localhost:7001`.

- Frontend URL: `https://claude-agent-sdk-chat.leanwise.ai` (Cloudflare Tunnel → local port 7002)
- Backend URL: `https://claude-agent-sdk-api.leanwise.ai` (Cloudflare Tunnel → local port 7001)
- WebSocket URL: `wss://claude-agent-sdk-api.leanwise.ai/api/v1/ws/chat`

## Project Overview

**Claude Agent SDK Chat** - Interactive chat application with multi-agent support and user authentication. Provides web interface and CLI with WebSocket/SSE streaming.

## Architecture

```
backend/                         # FastAPI server (port 7001)
├── agents.yaml                 # Agent definitions
├── subagents.yaml              # Delegation subagents
├── config.yaml                 # Runtime configuration
├── agent/
│   ├── core/                   # Agent utilities + per-user storage
│   ├── display/                # Console output formatting
│   └── tools/email/            # Gmail OAuth + universal IMAP email tools (MCP server)
├── platforms/                   # Multi-platform messaging integration
│   ├── adapters/               # Telegram, WhatsApp, Zalo adapters
│   ├── worker.py               # Message processing worker
│   ├── session_bridge.py       # Platform-to-session bridge
│   └── identity.py             # Platform user identity mapping
├── api/
│   ├── core/                   # Base router, shared API utilities
│   ├── db/                     # SQLite user database
│   ├── dependencies/           # Auth dependencies
│   ├── middleware/             # API key + JWT auth
│   ├── routers/                # WebSocket, SSE, sessions, user_auth, email_auth, files, webhooks
│   ├── services/               # Session, history, token, search, text extraction services
│   ├── models/                 # Pydantic models
│   └── utils/                  # API helper utilities
├── cli/                        # Click CLI with user login
│   ├── commands/               # CLI command handlers (chat, serve, list)
│   └── clients/                # CLI clients (WebSocket, API, auth, config)
└── data/{username}/            # Per-user sessions + history + email credentials

frontend/                        # Next.js 15 (port 7002)
├── app/
│   ├── (auth)/login/           # Login page
│   ├── (auth)/profile/         # Email integration management page
│   ├── privacy/                # Privacy policy page
│   ├── s/[sessionId]/          # Session detail page
│   ├── api/auth/               # Login, logout, session, token, OAuth callback routes
│   ├── api/proxy/              # REST API proxy
│   └── page.tsx                # Main chat page
├── components/
│   ├── agent/                  # Agent selector + configuration
│   ├── chat/                   # Chat UI components
│   ├── email/                  # Email connection buttons + status badge
│   ├── kanban/                 # Task board (cards, columns, activity, detail modal)
│   ├── session/                # Session sidebar + user profile
│   ├── features/auth/          # Login form, logout button
│   └── providers/              # Auth, Query, Theme providers
├── lib/
│   ├── store/                  # Zustand stores (chat, kanban, question, plan, ui, file, file-preview)
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
- `email_credentials/{key}.json` - Email account credentials (OAuth or app password)

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

### Modifying Kanban Board

- Width-prop responsive: `page.tsx` passes `panelWidth` → `KanbanBoard` derives size tiers from `config.kanban.breakpoints`
- Agent colors: Add new agent colors in `components/kanban/agent-colors.ts` — shared by task cards + activity
- Task data: `KanbanTask` interface in `lib/store/kanban-store.ts`, synced from messages via `syncFromMessages()`
- Activity has two view modes: `grouped` (by agent) and `timeline` (chronological) — controlled by `kanban-board.tsx`

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

### Email Integration

Email tools (Gmail OAuth, universal IMAP) are registered as MCP tools in the agent SDK. Two connection paths:

1. **Env-var auto-seed (admin only)**: `EMAIL_ACCOUNT_N_*` vars in `.env` → auto-connected at startup for admin user only. PDF auto-decryption also admin-only.
2. **UI manual (all users)**: Profile page → Connect Gmail (OAuth) or Connect Email (IMAP). Any authenticated user can connect/disconnect accounts.

Both paths write to the same credential store (`data/{username}/email_credentials/{key}.json`). See `docs/EMAIL_SETUP.md` for full setup guide.

- Backend OAuth + IMAP router: `backend/api/routers/email_auth.py`
- Email tools: `backend/agent/tools/email/` (credential store, attachment store, Gmail/IMAP clients, MCP server)
- Frontend profile page: `frontend/app/(auth)/profile/page.tsx`
- Per-user credentials stored in `data/{username}/email_credentials/{key}.json`
- Per-user attachments stored in `data/{username}/email_attachments/{provider}/{message_id}/`

OAuth state uses in-memory store with 10-min TTL and CSRF validation.

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
pytest tests/test_09_history_tracker.py -v  # Run specific test file
```

Test files use pytest-asyncio. 15 test files (test_00 through test_09, test_12 through test_14, test_agent_team, test_sensitive_data_filter).

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
- `backend/api/services/history_tracker.py` - JSONL history persistence + message ordering
- `backend/agent/core/storage.py` - Per-user storage utilities
- `backend/api/services/session_manager.py` - Session management

### Frontend Core

- `frontend/components/kanban/` - Task board UI (kanban-board, kanban-card, agent-activity, detail modal)
- `frontend/components/kanban/agent-colors.ts` - Shared agent color utilities
- `frontend/lib/store/kanban-store.ts` - Kanban state (tasks, tool calls, subagents)
- `frontend/lib/config.ts` - Centralized config (kanban breakpoints, API URLs, storage keys)
- `frontend/app/page.tsx` - Main chat page
- `frontend/hooks/use-chat.ts` - Chat WebSocket handler
- `frontend/hooks/use-websocket.ts` - WebSocket connection manager
- `frontend/lib/store/chat-store.ts` - Chat state management
- `frontend/lib/websocket-manager.ts` - WebSocket with token refresh
- `frontend/types/index.ts` - TypeScript types

## Dev Environment

Backend and frontend run in tmux sessions:
- Backend: `tmux send-keys -t claude_sdk_backend C-c && sleep 1 && tmux send-keys -t claude_sdk_backend "source .venv/bin/activate && python main.py serve --port 7001" Enter`
- Frontend: tmux session `claude_sdk_frontend`

## Deployment

Production URLs (served via Cloudflare Tunnel):
- Frontend: `https://claude-agent-sdk-chat.leanwise.ai` → local port 7002
- Backend: `https://claude-agent-sdk-api.leanwise.ai` → local port 7001

Both services run locally and are exposed to the internet through Cloudflare Tunnel. Frontend code must reference the backend production URL (`https://claude-agent-sdk-api.leanwise.ai`), never `localhost:7001`.

See individual README files in `/backend/` and `/frontend/` for deployment details.
