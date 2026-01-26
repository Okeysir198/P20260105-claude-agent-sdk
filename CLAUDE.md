# CLAUDE.md

Development guide for Claude Code when working with this repository.

## Development Rules

**IMPORTANT: Always use the production backend URL.** Never use localhost for backend connections.

- Backend URL: `https://claude-agent-sdk-fastapi-sg4.tt-ai.org`
- WebSocket URL: `wss://claude-agent-sdk-fastapi-sg4.tt-ai.org/api/v1/ws/chat`

This applies to all environment files (`.env.local`, `.env.example`, etc.) and any code changes.

## Project Overview

**Claude Agent SDK Chat** - Interactive chat application with multi-agent support. Provides web interface and CLI with WebSocket/SSE streaming. Features resizable sidebar, agent switching, session management, and interactive question handling.

## Architecture

```
backend/                         # FastAPI server (port 7001)
├── agents.yaml                 # Agent definitions (root level)
├── subagents.yaml              # Delegation subagents (root level)
├── agent/
│   └── core/
│       ├── agent_options.py     # create_agent_sdk_options()
│       └── storage.py           # SessionStorage + HistoryStorage
├── api/
│   ├── main.py                  # FastAPI app factory
│   ├── config.py                # API configuration
│   ├── constants.py             # Event types, close codes
│   ├── dependencies.py          # Dependency injection
│   ├── middleware/auth.py       # API key authentication
│   ├── routers/
│   │   ├── websocket.py         # WebSocket endpoint
│   │   ├── conversations.py     # SSE streaming
│   │   ├── sessions.py          # Session CRUD + close/resume
│   │   ├── configuration.py     # List agents
│   │   └── health.py            # Health check
│   ├── services/
│   │   ├── session_manager.py   # Session management
│   │   ├── history_tracker.py   # Message history
│   │   └── question_manager.py  # AskUserQuestion handling
│   └── models/                  # Request/response models
├── cli/
│   ├── main.py                  # Click CLI entry point
│   ├── commands/                # chat, serve, list commands
│   └── clients/                 # API + WebSocket clients
└── data/
    ├── sessions.json            # Session metadata
    └── history/                 # JSONL per session

frontend/                        # Next.js 16 (port 7002)
├── app/
│   ├── page.tsx                 # Main chat page
│   ├── layout.tsx               # Root layout with providers
│   └── globals.css              # Global styles + dark mode
├── components/
│   ├── agent/                   # Agent selection UI
│   │   ├── agent-grid.tsx       # Agent card grid
│   │   └── agent-switcher.tsx   # Agent dropdown
│   ├── chat/                    # Chat UI components
│   │   ├── chat-container.tsx   # Main chat wrapper
│   │   ├── chat-header.tsx      # Header with agent/status
│   │   ├── chat-input.tsx       # Message input
│   │   ├── message-list.tsx     # Message rendering
│   │   ├── user-message.tsx     # User message bubble
│   │   ├── assistant-message.tsx # Assistant message bubble
│   │   ├── tool-use-message.tsx # Tool use display
│   │   ├── tool-result-message.tsx # Tool result display
│   │   ├── question-modal.tsx   # AskUserQuestion modal
│   │   ├── code-block.tsx       # Syntax-highlighted code
│   │   ├── status-indicator.tsx # Connection status
│   │   ├── typing-indicator.tsx # Typing animation
│   │   ├── welcome-screen.tsx   # Welcome message
│   │   └── error-message.tsx    # Error display
│   ├── session/
│   │   ├── session-sidebar.tsx  # Resizable session list
│   │   ├── session-item.tsx     # Session list item
│   │   └── new-session-button.tsx # New session button
│   ├── ui/                      # shadcn/ui components
│   │   └── resizable.tsx        # Resizable panels
│   └── providers/
│       ├── query-provider.tsx   # React Query provider
│       └── theme-provider.tsx   # Dark mode provider
├── hooks/
│   ├── use-chat.ts              # Chat hook (WebSocket)
│   ├── use-websocket.ts         # WebSocket connection
│   ├── use-agents.ts            # Fetch agents from API
│   ├── use-sessions.ts          # Session management
│   ├── use-session-history.ts   # Session history retrieval
│   └── use-keyboard-shortcuts.ts # Keyboard shortcuts
└── lib/
    ├── api-client.ts            # HTTP client with auth
    └── constants.ts             # API URLs
```

## Authentication

The system uses a secure proxy architecture to protect API keys from browser exposure.

### Architecture Overview

```
REST API:
  Browser ──────> /api/proxy/* ──────> Backend API
    (no secrets)   (adds API_KEY)       claude-agent-sdk-fastapi-sg4.tt-ai.org

WebSocket:
  Browser ──────> /api/auth/token ──────> JWT created locally (Next.js server)
    │               (derives JWT_SECRET     (no backend call needed)
    │                from API_KEY)
    └───────────> wss://backend/ws/chat?token=JWT (DIRECT connection)
```

### JWT Secret Derivation

The JWT secret is **derived** from `API_KEY` using HMAC-SHA256 - no separate `JWT_SECRET_KEY` needed:

```
API_KEY ────────────────────────────────────────────────────► REST API Auth
    │                                                          (X-API-Key header)
    │
    ▼
HMAC-SHA256(salt, API_KEY) = JWT_SECRET ────────────────────► JWT Signing
                                                              (cannot reverse to API_KEY)
```

- **Salt**: `claude-agent-sdk-jwt-v1`
- **Algorithm**: HS256
- **Same derivation** used by both frontend (Next.js) and backend (FastAPI)
- **JWT tokens created locally** on Next.js server - no backend call for token creation

### Security Model

- **API key is NEVER exposed to the browser** - stored only on the Next.js server
- **REST API calls** go through Next.js proxy routes (`/api/proxy/*`) which inject the API key
- **JWT secret derived from API_KEY** using HMAC-SHA256 (cannot recover API_KEY from JWT secret)
- **JWT tokens created locally** on Next.js server (no network call to backend)
- Timing-safe comparison (`secrets.compare_digest`) for all key validation
- Auth failures logged with IP (keys never logged)

### Frontend Proxy Routes

| Route | Purpose | Description |
|-------|---------|-------------|
| `/api/proxy/*` | REST API proxy | Forwards to `/api/v1/*` with X-API-Key header |
| `/api/auth/token` | Create JWT | Creates JWT locally using derived secret |
| `/api/auth/refresh` | Refresh JWT | Creates new JWT using refresh token |

### Backend Auth Endpoints

| Endpoint | Auth | Description |
|----------|------|-------------|
| `POST /auth/ws-token` | API Key | Exchange API key for WebSocket JWT (alternative to local creation) |
| `POST /auth/ws-token-refresh` | JWT | Refresh WebSocket JWT |

**Note:** The frontend creates JWT tokens locally without calling backend auth endpoints.

Backend middleware: `api/middleware/auth.py` (API key), `api/middleware/jwt_auth.py` (JWT)
Frontend: `lib/api-client.ts` (proxy), `lib/auth.ts` (JWT management)

## Key Flows

**WebSocket Chat (JWT Authentication):**
```
1. Get JWT token (created locally on Next.js server):
   POST /api/auth/token (no backend call - JWT derived from API_KEY)
   Response: {"access_token": "jwt...", "expires_in": 1800}

2. Connect with JWT:
   Connect: wss://backend/api/v1/ws/chat?token=JWT&agent_id=ID
   ← {"type": "ready"}
   → {"content": "Hello"}
   ← {"type": "session_id", "session_id": "uuid"}
   ← {"type": "text_delta", "text": "..."}
   ← {"type": "ask_user_question", "question_id": "...", "questions": [...]}
   → {"type": "user_answer", "question_id": "...", "answers": {...}}
   ← {"type": "done", "turn_count": 1}
```

**AskUserQuestion Flow:**
```
Agent triggers AskUserQuestion tool
← {"type": "ask_user_question", "question_id": "uuid", "questions": [...]}
Frontend shows modal with questions
User selects options
→ {"type": "user_answer", "question_id": "uuid", "answers": {...}}
← {"type": "question_answered", "question_id": "uuid"}
Agent continues with answers
```

**Agent Selection (Frontend):**
```
page.tsx
  └─ useAgents() → GET /api/v1/config/agents
  └─ useState(selectedAgentId)
  └─ ChatContainer
       └─ useChat({ agentId })
            └─ WebSocket with agent_id param
```

**Session Resumption:**
```
POST /api/v1/sessions/{id}/resume
  Returns existing session context
  Continues conversation with preserved history
```

## Commands

```bash
# Backend
cd backend
source .venv/bin/activate
python main.py serve --port 7001    # Start API server
python main.py chat                 # Interactive WebSocket chat
python main.py chat --mode sse      # Interactive SSE chat
python main.py agents               # List available agents
python main.py subagents            # List delegation subagents
python main.py sessions             # List conversation sessions
python main.py skills               # List available skills

# Frontend
cd frontend
npm run dev                         # Dev server (port 7002)
npm run build                       # Production build
npm run lint                        # ESLint check
```

## API Endpoints

### Backend API (requires API key via X-API-Key header)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/health` | No | Health check |
| POST | `/auth/ws-token` | API Key | Get WebSocket JWT token |
| POST | `/auth/ws-token-refresh` | JWT | Refresh WebSocket JWT |
| WS | `/api/v1/ws/chat` | JWT | WebSocket chat (persistent) |
| POST | `/api/v1/conversations` | API Key | Create conversation (SSE) |
| POST | `/api/v1/conversations/{id}/stream` | API Key | Follow-up message (SSE) |
| GET | `/api/v1/sessions` | API Key | List all sessions |
| GET | `/api/v1/sessions/{id}/history` | API Key | Get session history |
| DELETE | `/api/v1/sessions/{id}` | API Key | Delete session |
| POST | `/api/v1/sessions/{id}/close` | API Key | Close session (keep history) |
| POST | `/api/v1/sessions/{id}/resume` | API Key | Resume specific session |
| GET | `/api/v1/config/agents` | API Key | List available agents |

### Frontend Proxy Routes (no secrets required)

| Route | Proxies To | Description |
|-------|-----------|-------------|
| `/api/proxy/*` | `/api/v1/*` | REST API proxy (adds API key) |
| `/api/auth/token` | `/auth/ws-token` | Get WebSocket JWT |
| `/api/auth/refresh` | `/auth/ws-token-refresh` | Refresh JWT |

## Communication Protocols

### WebSocket (Persistent Connection)

**Best for:** Multi-turn conversations, real-time interaction, AskUserQuestion support.

**Connection Flow:**
```
1. Client obtains JWT (created locally on Next.js server):
   POST /api/auth/token (derives JWT secret from API_KEY, no backend call)
   Response: {"access_token": "jwt...", "expires_in": 1800}

2. Client connects directly to backend with JWT:
   wss://backend/api/v1/ws/chat?token=JWT&agent_id=ID&session_id=OPTIONAL

3. Server validates JWT token

4. Server accepts connection and sends ready event:
   ← {"type": "ready", "session_id": "...", "resumed": true, "turn_count": N}
   (If resuming existing session, includes session_id, resumed=true, turn_count)

5. Client sends messages:
   → {"content": "user message"}

6. Server streams response events (see Event Types below)

7. Connection remains open for multiple turns until client disconnects
```

**Message Loop:**
```
For each user message:
→ {"content": "What is 2+2?"}
← {"type": "text_delta", "text": "2"}  // Streaming response
← {"type": "text_delta", "text": "+"}
← {"type": "text_delta", "text": "2"}
← {"type": "text_delta", "text": " is"}
← {"type": "text_delta", "text": " 4"}
← {"type": "done", "turn_count": 1}

// Next message can be sent immediately
→ {"content": "What about 3+3?"}
← {"type": "text_delta", "text": "3+3"}
...
```

**AskUserQuestion Flow (WebSocket only):**
```
// Agent triggers AskUserQuestion tool
← {"type": "ask_user_question", "question_id": "uuid", "questions": [...], "timeout": 60}

// Frontend shows modal, user selects options
→ {"type": "user_answer", "question_id": "uuid", "answers": {"question": "option"}}

// Server acknowledges and agent continues
← {"type": "question_answered", "question_id": "uuid"}
...response continues...
```

**Event Types (WebSocket):**
| Type | Direction | Description |
|------|-----------|-------------|
| `ready` | Server→Client | Connection ready, includes session info if resuming |
| `session_id` | Server→Client | SDK session identifier (first message only) |
| `text_delta` | Server→Client | Streaming text chunk |
| `tool_use` | Server→Client | Tool invocation details |
| `tool_result` | Server→Client | Tool execution result |
| `ask_user_question` | Server→Client | Interactive question (requires user_answer) |
| `question_answered` | Server→Client | Question processed acknowledgment |
| `done` | Server→Client | Response complete, includes turn_count |
| `error` | Server→Client | Error occurred |
| `content` | Client→Server | User message content |
| `user_answer` | Client→Server | Answer to ask_user_question |

**Session Resumption (WebSocket):**
```
// Connect with existing session_id and JWT
wss://backend/api/v1/ws/chat?token=JWT&session_id=EXISTING_ID

// Server responds with resumed session info
← {"type": "ready", "session_id": "EXISTING_ID", "resumed": true, "turn_count": 5}

// Context preserved, can continue conversation
→ {"content": "What were we talking about?"}
← {"type": "text_delta", "text": "We were discussing..."}
```

**Close Codes:**
| Code | Name | Description |
|------|------|-------------|
| 1000 | NORMAL | Normal closure |
| 1008 | AUTH_FAILED | Invalid or missing JWT token |
| 1003 | SESSION_NOT_FOUND | Session to resume not found |
| 1011 | SDK_CONNECTION_FAILED | Failed to initialize SDK client |

---

### SSE (Server-Sent Events - One-shot)

**Best for:** Single-turn requests, stateless operations, HTTP-friendly environments.

**Connection Flow:**
```
1. Client sends HTTP POST with auth header:
   POST /api/v1/conversations
   Headers: X-API-Key: KEY
   Body: {"content": "Hello", "agent_id": "OPTIONAL_ID", "session_id": "OPTIONAL_ID"}

2. Server returns EventSourceResponse with text/event-stream

3. Server streams SSE events:
   event: session_id
   data: {"session_id": "uuid", "found_in_cache": false}

   event: text_delta
   data: {"text": "Hello"}

   event: sdk_session_id
   data: {"sdk_session_id": "sdk-uuid"}

   event: text_delta
   data: {"text": " there!"}

   event: done
   data: {"turn_count": 1}

4. Connection closes when done
```

**Follow-up Message:**
```
POST /api/v1/conversations/{session_id}/stream
Headers: X-API-Key: KEY
Body: {"content": "What is 2+2?"}

// Streams response events
event: session_id
data: {"session_id": "uuid", "found_in_cache": true}

event: text_delta
data: {"text": "2+2"}

event: text_delta
data: {"text": " is 4"}

event: done
data: {"turn_count": 2}
```

**SSE Event Types:**
| Event | Data | Description |
|-------|------|-------------|
| `session_id` | `{"session_id": "...", "found_in_cache": bool}` | Session identifier |
| `sdk_session_id` | `{"sdk_session_id": "..."}` | SDK session identifier |
| `text_delta` | `{"text": "..."}` | Streaming text chunk |
| `tool_use` | `{...tool details...}` | Tool invocation |
| `tool_result` | `{...result details...}` | Tool result |
| `done` | `{"turn_count": N}` | Response complete |
| `error` | `{"error": "...", "type": "..."}` | Error occurred |

**Key Differences - SSE vs WebSocket:**
| Feature | WebSocket | SSE |
|---------|-----------|-----|
| **Connection** | Persistent, bi-directional | One-shot HTTP, server→client only |
| **Use case** | Multi-turn conversations | Single requests |
| **AskUserQuestion** | Full support (user_answer event) | Not supported (timeout fallback) |
| **Session context** | Maintained in connection | Resumed via session_id parameter |
| **Browser support** | Full | Full (via EventSource) |
| **Reconnection** | Manual reconnection needed | Automatic browser reconnection |
| **Complexity** | Higher (connection management) | Lower (standard HTTP) |

**Choosing a Protocol:**
- Use **WebSocket** when building an interactive chat interface with multi-turn conversations
- Use **SSE** for one-off queries, simple integrations, or when WebSocket overhead isn't needed

## Available Agents

| Agent ID | Name | Description | Model |
|----------|------|-------------|-------|
| `general-agent-a1b2c3d4` | General Assistant | General-purpose coding assistant (default) | sonnet |
| `code-reviewer-x9y8z7w6` | Code Reviewer | Code reviews and security analysis | sonnet |
| `doc-writer-m5n6o7p8` | Documentation Writer | Documentation generation | sonnet |
| `research-agent-q1r2s3t4` | Code Researcher | Codebase exploration (read-only) | haiku |
| `sandbox-agent-s4ndb0x1` | Sandbox Agent | Restricted file permissions for testing | sonnet |

## Subagents (Delegation)

Available for task delegation via Task tool:
- **researcher** - Code exploration and analysis
- **reviewer** - Code review and quality checks
- **file_assistant** - File operations assistance

## Adding Agents

Edit `backend/agents.yaml`:

```yaml
my-agent-abc123:
  name: "My Agent"
  description: "What it does"
  system_prompt: |
    Instructions (appended to claude_code preset)
  tools: [Skill, Task, Read, Write, Edit, Bash, Grep, Glob]
  model: sonnet
  subagents: [researcher, reviewer, file_assistant]
  permission_mode: acceptEdits
  with_permissions: true
  allowed_directories: [/tmp]
```

## Frontend Features

**Resizable Sidebar:**
- Adjustable width (240-500px) with drag handle
- Persistent width stored in localStorage
- Smooth resize animations

**Agent Switching:**
- Grid view with agent cards
- Dropdown selector in chat header
- Visual agent selection indicators

**AskUserQuestion Integration:**
- Modal UI for interactive questions
- Multi-option question support
- Timeout handling for user responses
- Keyboard shortcut support

**Keyboard Shortcuts:**
- `Ctrl/Cmd + K` - Focus input
- `Ctrl/Cmd + Enter` - Send message
- `Escape` - Close modal

**Dark Mode:**
- System preference detection
- Manual toggle in theme provider
- Custom color scheme for low-light environments

## Environment Variables

**Backend (.env):**
```
ANTHROPIC_API_KEY=sk-ant-...
# Generate secure key: openssl rand -hex 32
API_KEY=your-api-key
# CORS should include the frontend production URL
CORS_ORIGINS=https://claude-agent-sdk-chat.tt-ai.org
```

**Note:** No separate `JWT_SECRET_KEY` needed - JWT secret is derived from `API_KEY` using HMAC-SHA256.

**Backend Production URL:** `https://claude-agent-sdk-fastapi-sg4.tt-ai.org`

**Frontend (.env.local):**
```
# Server-only variables (NEVER exposed to browser)
API_KEY=your-api-key                    # Used by proxy routes and JWT creation
BACKEND_API_URL=https://claude-agent-sdk-fastapi-sg4.tt-ai.org

# Public variables (safe for browser)
NEXT_PUBLIC_WS_URL=wss://claude-agent-sdk-fastapi-sg4.tt-ai.org/api/v1/ws/chat
```

**Security Notes:**
- `API_KEY` and `BACKEND_API_URL` are server-only (no `NEXT_PUBLIC_` prefix)
- Only `NEXT_PUBLIC_WS_URL` is exposed to the browser (WebSocket connects directly with JWT)
- JWT secret is derived from API_KEY using HMAC-SHA256 (same derivation on frontend and backend)
- JWT tokens are short-lived (30 min access, 7 day refresh) and can be revoked

## Deployment

```bash
# Backend tunnel
cloudflare tunnel --url http://localhost:7001 --hostname api.domain.com

# Frontend tunnel
cloudflare tunnel --url http://localhost:7002 --hostname app.domain.com
```

Production URLs:
- Backend: `https://claude-agent-sdk-fastapi-sg4.tt-ai.org`
- Frontend: `https://claude-agent-sdk-chat.tt-ai.org`
