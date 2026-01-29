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

The WebSocket event handling follows a strict pattern in `frontend/hooks/use-chat.ts`:

1. **Event Type Switch**: All WebSocket events are handled in a single switch statement
2. **State Isolation**: Use `useChatStore.getState()` to avoid closure staleness
3. **Message Creation Pattern**:
   ```typescript
   const message: ChatMessage = {
     id: crypto.randomUUID(),
     role: 'user' | 'assistant' | 'tool_use' | 'tool_result',
     content: string,
     timestamp: new Date(),
     // Optional: toolName, toolInput, toolUseId, isError
   };
   addMessage(message);
   ```

### Frontend: Zustand Store Updates

When updating stores:
- Use `setPendingMessage()` for values that need to be sent after connection
- Use `updateLastMessage()` for streaming content accumulation
- Use `addMessage()` for new messages
- Always invalidate queries after session changes: `queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.SESSIONS] })`

### Frontend: Component Organization

- **UI Components**: `/components/ui/` - Reusable Radix UI primitives (button, dialog, etc.)
- **Feature Components**: `/components/{feature}/` - Domain-specific components (chat, session, agent)
- **Providers**: `/components/providers/` - Context providers (Auth, Query, Theme)
- Always use `'use client'` directive for client-side components

### Backend: Per-User Data Isolation

All user data is stored in `backend/data/{username}/`:
- `sessions.json` - Active sessions metadata
- `history/{session_id}.jsonl` - Message history per session

When working with storage:
- Use `agent/core/storage.py` utilities for file operations
- Never hardcode paths - use username from JWT token
- Session IDs are UUIDs

### Backend: Agent Configuration

Agents are defined in `backend/agents.yaml`:

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

**Important**: `system_prompt` is APPENDED to the default Claude Code prompt, not replacing it.

## Common Workflows

### Adding a New Agent

1. Edit `backend/agents.yaml`
2. Add agent entry with unique ID (format: `{name}-{random-suffix}`)
3. Define tools, model, and optional subagents
4. Restart backend server to reload config
5. Agent appears in frontend dropdown automatically

### Debugging WebSocket Issues

1. **Check Connection Status**: Look at the status indicator in chat header
2. **Browser Console**: Check for WebSocket errors
3. **Backend Logs**: Look for WebSocket connection/auth errors
4. **Common Issues**:
   - Session not found → Backend auto-recovers, starts new session
   - Token expired → Frontend auto-refreshes via `/api/auth/token`
   - Agent not found → Check `agents.yaml` and restart backend

### Modifying Chat UI

1. **Message Display**: Edit components in `frontend/components/chat/`
2. **Message Types**: `user-message.tsx`, `assistant-message.tsx`, `tool-use-message.tsx`, `tool-result-message.tsx`
3. **Input Handling**: `frontend/components/chat/chat-input.tsx`
4. **Store Updates**: Modify `frontend/hooks/use-chat.ts` for new message types

### Adding New WebSocket Events

1. **Backend**: Add event to `backend/api/routers/websocket.py`
2. **Frontend Types**: Add type to `frontend/types/index.ts`
3. **Frontend Handler**: Add case to switch statement in `use-chat.ts`
4. **Test**: Connect to dev environment and send message triggering event

### Adding User Authentication to API Routes

All authenticated routes require:
1. API key via `X-API-Key` header
2. User JWT via `Authorization: Bearer <token>` header
3. Dependency: `get_current_user()` from `backend/api/dependencies/auth.py`

Example:
```python
@router.get("/api/v1/sessions")
async def list_sessions(
    current_user: User = Depends(get_current_user),
    api_key: str = Depends(verify_api_key)
):
    # current_user.username available here
    pass
```

## Testing

### Backend Tests

```bash
cd backend
pytest tests/ -v                    # Run all tests
pytest tests/test_websocket.py      # Run specific test file
```

Test files use pytest-asyncio for async WebSocket testing.

### Frontend Testing

Currently no automated frontend tests. Manual testing:
1. Start dev servers: `backend (7001)` and `frontend (7002)`
2. Login at `http://localhost:7002`
3. Test WebSocket connection, message flow, tool calls
4. Check browser console for errors

### Integration Testing

Test full flow:
1. Start backend: `cd backend && python main.py serve --port 7001`
2. Start frontend: `cd frontend && npm run dev`
3. Login with admin/tester credentials
4. Send message, verify WebSocket streaming works
5. Check tool calls render correctly
6. Verify session persistence

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
