# Frontend CLAUDE.md

Next.js 16 chat application with WebSocket streaming, Zustand state management, and JWT authentication.

## Commands

```bash
npm run dev          # Dev server with Turbopack (port 7002)
npm run build        # Production build
npm run start        # Production server (port 7002)
npm run lint         # ESLint
npx tsc --noEmit     # Type check without emitting
npm run cf:build     # Build for Cloudflare Workers
npm run cf:preview   # Build + local preview with Wrangler
npm run cf:deploy    # Build + deploy to Cloudflare Workers
```

**Cloudflare Deployment Prerequisites:**
- Run `npx wrangler login` to authenticate before deploying
- Ensure environment variables are set: `CLOUDFLARE_ACCOUNT_ID`, `API_KEY`, `BACKEND_API_URL`, `NEXT_PUBLIC_WS_URL`, `NEXT_PUBLIC_APP_URL`

## Environment Variables

```bash
API_KEY=<same-as-backend>                                    # Required: shared secret for API proxy
BACKEND_API_URL=https://claude-agent-sdk-api.leanwise.ai/api/v1  # Backend API base
NEXT_PUBLIC_WS_URL=wss://claude-agent-sdk-api.leanwise.ai/api/v1/ws/chat  # WebSocket URL (browser)
```

`API_KEY` and `BACKEND_API_URL` are server-only. Only `NEXT_PUBLIC_WS_URL` is exposed to the browser.

## Architecture

```
app/
├── (auth)/login/page.tsx       # Login page (public route)
├── (auth)/profile/page.tsx     # Email integration management page
├── privacy/page.tsx            # Privacy policy page
├── s/[sessionId]/page.tsx      # Session detail page
├── page.tsx                    # Main chat page (protected)
├── layout.tsx                  # Root layout with providers
├── globals.css                 # CSS variables, theme colors
├── api/
│   ├── auth/login/             # POST: authenticate, set cookies
│   ├── auth/logout/            # POST: clear session cookies
│   ├── auth/session/           # GET: check auth status
│   ├── auth/token/             # GET: create WebSocket JWT
│   ├── auth/callback/email/    # OAuth callback proxy (Gmail)
│   └── proxy/[...path]/        # Generic backend proxy (adds API key)
components/
├── agent/                      # Agent selector grid
├── chat/                       # Chat UI (messages, input, modals, tools/)
├── kanban/                     # Task board panel
│   ├── kanban-board.tsx        # Board container, tab bar, view toggles
│   ├── kanban-card.tsx         # Task card (status icon, owner badge, timestamp)
│   ├── kanban-column.tsx       # Collapsible status column
│   ├── agent-activity.tsx      # Tool call timeline (grouped/timeline views)
│   ├── agent-colors.ts         # Shared agent→color mapping
│   ├── kanban-detail-modal.tsx # Resizable detail modal (task + tool call)
│   └── kanban-sync.tsx         # Message-to-kanban sync wrapper
├── email/                      # Email connection UI (Gmail OAuth, universal IMAP, shared constants)
├── session/                    # Sidebar (session list, search)
├── features/auth/              # Login form
├── providers/                  # AuthProvider, QueryProvider, ThemeProvider
└── ui/                         # Radix UI primitives
hooks/
├── use-chat.ts                 # Main chat orchestration (WebSocket events)
├── use-websocket.ts            # WebSocket manager wrapper
├── use-sessions.ts             # Session CRUD (React Query mutations)
├── use-agents.ts               # Agent list fetching
├── use-history-loading.ts      # History loading with retry
├── use-session-search.ts       # Backend full-text search
├── use-image-upload.ts         # Image file handling
├── use-files.ts                # File handling
├── use-connection-tracking.ts  # Connection state tracking
├── chat-event-handlers.ts      # WebSocket event handler functions
├── chat-message-factory.ts     # Message creation helpers
├── chat-store-types.ts         # Chat store type definitions
└── chat-text-utils.ts          # Text processing utilities
lib/
├── store/
│   ├── chat-store.ts           # Messages, sessionId, agentId, streaming state
│   ├── ui-store.ts             # Sidebar, theme, mobile state
│   ├── kanban-store.ts         # Tasks, tool calls, subagents, session usage
│   ├── question-store.ts       # AskUserQuestion modal state
│   ├── plan-store.ts           # Plan approval modal state
│   ├── file-store.ts           # File management state
│   └── file-preview-store.ts   # File preview modal state
├── websocket-manager.ts        # Singleton WebSocket with auto-reconnect
├── auth.ts                     # Token service (JWT fetch/refresh)
├── server-auth.ts              # Server-side auth utilities
├── session.ts                  # Server-side session cookie management
├── jwt-utils.ts                # JWT creation and verification
├── api-client.ts               # REST API client
├── message-utils.ts            # Message validation + content preparation
├── content-utils.ts            # Content block utilities
├── history-utils.ts            # History loading/parsing utilities
├── question-utils.ts           # Question modal utilities
├── code-highlight.ts           # Syntax highlighting configuration
├── tool-config.ts              # Tool display configuration
├── tool-output-parser.ts       # Tool output parsing
├── config.ts                   # Centralized config constants
├── constants.ts                # Re-exports from config
├── utils.ts                    # General utilities
└── utils/file-utils.ts         # File handling utilities
types/
├── index.ts                    # ChatMessage, ContentBlock, Agent, Session
├── api.ts                      # API request/response types
├── websocket.ts                # WebSocket event type definitions
└── diff.d.ts                   # Diff display type declarations
proxy.ts                       # Route protection (Next.js 16 renamed from middleware.ts)
```

## Key Patterns

### Authentication Flow

1. **Login**: POST `/api/auth/login` → backend validates → HttpOnly cookies set (`claude_agent_session` + `claude_agent_refresh`)
2. **REST calls**: All go through `/api/proxy/[...path]` which adds `X-API-Key` + `X-User-Token` headers server-side
3. **WebSocket**: Fetches fresh JWT via `/api/auth/token`, connects with `?token={jwt}` query param
4. **Proxy** (`proxy.ts`): Checks `claude_agent_session` cookie, redirects unauthenticated to `/login?from={path}`

### WebSocket Manager (Singleton)

```typescript
import { webSocketManager } from '@/lib/websocket-manager';

webSocketManager.connect(agentId, sessionId);
webSocketManager.sendMessage(content);           // string | ContentBlock[]
webSocketManager.sendAnswer(questionId, answers);
webSocketManager.sendPlanApproval(planId, approved, feedback);
webSocketManager.sendCancel();
webSocketManager.sendCompact();
```

- Auto-reconnects up to 5 attempts (3s delay)
- Auto-refreshes JWT on token expiry (5-min buffer)
- Prevents duplicate connections via pending tracking
- Connection ID prevents stale handler execution

### Zustand Stores

**chat-store** — Messages in memory only (not persisted). `sessionId` and `agentId` persisted to localStorage.

```typescript
// Always use getState() in callbacks to avoid closure staleness
const { messages, sessionId } = useChatStore.getState();
useChatStore.getState().addMessage(msg);
```

**ui-store** — Sidebar open/close, theme, mobile detection.

**question-store** / **plan-store** — Modal state with countdown timers.

### WebSocket Event Handling

All events handled in `hooks/chat-event-handlers.ts` via switch statement:

| Event | Action |
|-------|--------|
| `ready` | Set sessionId, send pending message if queued |
| `text_delta` | Append to last assistant message |
| `tool_use` | Add tool use message |
| `tool_result` | Add tool result message |
| `done` | Set streaming=false, invalidate session queries |
| `error` | Display error, set streaming=false |
| `ask_user_question` | Open question modal |
| `plan_approval` | Open plan approval modal |
| `cancelled` | Set streaming=false |
| `compact_completed` | Set compacting=false |

### Component Organization

- **UI primitives**: `components/ui/` — Radix UI, don't modify
- **Feature components**: `components/{feature}/` — Domain-specific
- **Barrel exports**: `components/chat/index.ts` — Import from barrel
- All client components need `'use client'` directive

### API Proxy Pattern

All REST calls go through Next.js API route `/api/proxy/[...path]`:
- Client calls `/api/proxy/sessions` → proxy adds auth headers → forwards to `${BACKEND_API_URL}/sessions`
- Keeps `API_KEY` server-side only
- Auto-refreshes session token if expired

### Message Content Format

```typescript
// String (simple text)
content: "Hello, world!"

// Multi-part (text + images)
content: [
  { type: "text", text: "Look at this:" },
  { type: "image", source: { type: "base64", data: "...", media_type: "image/png" } }
]
```

Both formats supported throughout. Use `prepareMessageContent()` from `lib/message-utils.ts` to normalize.

### Kanban Board Patterns

- **Responsive via width prop** (not CSS container queries): `page.tsx` passes `panelWidth` → `KanbanBoard` derives `isNarrow`/`isCompact` from `config.kanban.breakpoints` (narrow: 320, compact: 400, standard: 500)
- **Agent colors**: `agent-colors.ts` exports `getAgentColor()` (badge classes) and `getAgentTextColor()` (icon color). Same mapping used by task cards and activity timeline.
- **Task sync**: `kanban-store.syncFromMessages()` parses TaskCreate, TaskUpdate, TodoWrite, Task tool_use messages into `KanbanTask[]`. Dedup pass matches Task delegations to TaskCreate cards.
- **View modes**: Tasks tab has stack/columns toggle. Activity tab has grouped/timeline toggle. Both controlled by `kanban-board.tsx`, passed as props.
- **Detail modal**: Resizable via drag handles. Uses `getGridColsClass(modalWidth)` for responsive metadata grid (1/2/3 cols).

## Gotchas

- **Messages are in-memory only** — Page refresh clears messages. History reloaded from backend on session resume.
- **Pending message pattern** — Welcome page queues message before WebSocket connected. Sent on `ready` event.
- **Session name from first message** — First user message in a session becomes the session name.
- **500ms delay on agent switch** — Allows backend cleanup before reconnecting with new agent.
- **Mobile sidebar** — Fixed 280px width with backdrop overlay. Auto-collapses on initial mobile load.
- **Token stored in memory only** — WebSocket JWT not persisted. Fresh token fetched on each page load.
- **Two search modes** — Magnifying glass = client-side name search. File search icon = backend full-text content search.
- **`useChatStore.getState()`** — Always use this in WebSocket callbacks, never use hook values directly (closure staleness).
- **Email proxy routes** — Email API calls go through `/api/proxy/email/*` (same proxy pattern as other REST calls).
- **Edge-compatible crypto** — `lib/jwt-utils.ts` uses Web Crypto API (`crypto.subtle`), not Node.js `crypto`. All crypto functions are async. Required for Cloudflare Workers deployment.
- **CF build renames proxy.ts** — `scripts/cf-prepare.mjs` renames `proxy.ts` → `middleware.ts` during CF build (OpenNext doesn't support `proxy.ts` yet), then `cf-restore.mjs` reverts it.
- **TypeScript imageRendering gotcha** — CSS `imageRendering` property only accepts `'auto'`, `'crisp-edges'`, or `'pixelated'`. Not `'high-quality'` or other values.

## Theming

CSS variables in `globals.css`. Primary color: `#C15F3C` (terracotta) in both light/dark modes.

Tool-specific colors available: `--tool-bash`, `--tool-read`, `--tool-write`, `--tool-search`, `--tool-web`, `--tool-task`, `--tool-plan`, `--tool-mcp`.
