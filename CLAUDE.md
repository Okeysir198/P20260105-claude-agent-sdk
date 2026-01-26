# CLAUDE.md

Development guide for Claude Code when working with this repository.

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

All endpoints except `/health` require API key:
- **REST API:** `X-API-Key` header only (query params rejected for security)
- **WebSocket:** `api_key` query param (browser cannot send headers)

Security features:
- Timing-safe comparison (`secrets.compare_digest`)
- Auth failures logged with IP (keys never logged)
- CORS wildcard warning on startup

Backend middleware: `api/middleware/auth.py`
Frontend: `lib/api-client.ts` (header) + `hooks/use-websocket.ts` (query param for WS)

## Key Flows

**WebSocket Chat:**
```
Connect: ws://host/api/v1/ws/chat?api_key=KEY&agent_id=ID
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

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/health` | No | Health check |
| WS | `/api/v1/ws/chat` | Yes | WebSocket chat (persistent) |
| POST | `/api/v1/conversations` | Yes | Create conversation (SSE) |
| POST | `/api/v1/conversations/{id}/stream` | Yes | Follow-up message (SSE) |
| GET | `/api/v1/sessions` | Yes | List all sessions |
| GET | `/api/v1/sessions/{id}/history` | Yes | Get session history |
| DELETE | `/api/v1/sessions/{id}` | Yes | Delete session |
| POST | `/api/v1/sessions/{id}/close` | Yes | Close session (keep history) |
| POST | `/api/v1/sessions/{id}/resume` | Yes | Resume specific session |
| GET | `/api/v1/config/agents` | Yes | List available agents |

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
API_KEY=your-key
# CORS should include the frontend production URL
CORS_ORIGINS=https://claude-agent-sdk-chat.tt-ai.org
```

**Backend Production URL:** `https://claude-agent-sdk-fastapi-sg4.tt-ai.org`

**Frontend (.env.local):**
```
NEXT_PUBLIC_API_URL=https://claude-agent-sdk-fastapi-sg4.tt-ai.org/api/v1
NEXT_PUBLIC_API_KEY=your-key
```

**Important:** The frontend is configured to always connect to the production backend. Localhost connections are not supported.

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
