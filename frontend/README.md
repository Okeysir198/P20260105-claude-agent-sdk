# Claude Agent SDK - Frontend

Next.js 16 chat interface with user authentication, WebSocket streaming, and per-user sessions.

## Quick Start

```bash
npm install
cp .env.example .env.local   # Configure API_KEY and BACKEND_API_URL
npm run dev   # http://localhost:7002
```

## Features

- User login with route protection
- Real-time WebSocket streaming
- Multi-agent selection
- Session sidebar with search (name + full-text content search)
- Kanban task board panel (synced from agent tool calls)
- Email integration management (Gmail OAuth, universal IMAP for Yahoo/Outlook/iCloud/Zoho/custom)
- File upload and preview (images, PDFs, Excel, code)
- Plan approval modal
- AskUserQuestion modal
- Dark/light mode
- Keyboard shortcuts (Ctrl+K, Ctrl+Enter, Escape)

## Architecture

```
app/
├── (auth)/
│   ├── login/             # Login page (public)
│   └── profile/           # Email integration management
├── s/[sessionId]/         # Session detail page
├── api/
│   ├── auth/              # Login, logout, session, token, refresh, OAuth callback routes
│   ├── files/             # File upload proxy
│   └── proxy/             # REST API proxy (adds API key)
├── page.tsx               # Main chat (protected)
└── layout.tsx             # Root layout with providers

components/
├── agent/                 # Agent selector grid + switcher
├── chat/                  # Chat UI components
│   ├── tools/             # Tool-specific display components
│   ├── connection-*.tsx   # Connection state components
│   └── chat-*.tsx         # Chat core components
├── email/                 # Email connection buttons, status badge, shared constants
├── files/                 # File upload zone, preview modal, file cards, type-specific previewers
├── kanban/                # Task board panel
│   ├── kanban-board.tsx   # Board container, tab bar, view toggles
│   ├── kanban-card.tsx    # Task card (status icon, owner badge)
│   ├── kanban-column.tsx  # Collapsible status column
│   ├── agent-activity.tsx # Tool call timeline (grouped/timeline views)
│   ├── agent-colors.ts   # Shared agent color mapping
│   ├── kanban-detail-modal.tsx # Resizable detail modal
│   └── kanban-sync.tsx    # Message-to-kanban sync wrapper
├── session/               # Sidebar with session list + user profile
├── features/auth/         # Login form, logout button
├── providers/             # Auth, Query, Theme providers
└── ui/                    # Radix UI primitives

hooks/
├── use-chat.ts             # Main chat orchestration (WebSocket events)
├── use-websocket.ts        # WebSocket manager wrapper
├── use-sessions.ts         # Session CRUD (React Query mutations)
├── use-agents.ts           # Agent list fetching
├── use-history-loading.ts  # History loading with retry
├── use-session-search.ts   # Backend full-text search
├── use-image-upload.ts     # Image file handling
├── use-files.ts            # File management
├── use-connection-tracking.ts # Connection state tracking
├── chat-event-handlers.ts  # WebSocket event handler functions
├── chat-message-factory.ts # Message creation helpers
├── chat-store-types.ts     # Chat store type definitions
└── chat-text-utils.ts      # Text processing utilities

lib/
├── store/
│   ├── chat-store.ts        # Messages, sessionId, agentId, streaming state
│   ├── ui-store.ts          # Sidebar, theme, mobile state
│   ├── kanban-store.ts      # Tasks, tool calls, subagents
│   ├── question-store.ts    # AskUserQuestion modal state
│   ├── plan-store.ts        # Plan approval modal state
│   ├── file-store.ts        # File management state
│   └── file-preview-store.ts # File preview modal state
├── websocket-manager.ts    # Singleton WebSocket with auto-reconnect
├── auth.ts                 # Token service (JWT fetch/refresh)
├── session.ts              # Server-side session cookie management
├── jwt-utils.ts            # JWT creation and verification
├── api-client.ts           # REST API client with auth
├── config.ts               # Centralized config constants
├── constants.ts            # Re-exports from config
├── content-utils.ts        # Content normalization (multi-part messages)
├── message-utils.ts        # Message creation helpers
├── progress-utils.ts       # Progress tracking utilities
├── question-utils.ts       # Question modal utilities
├── history-utils.ts        # History loading utilities
├── tool-output-parser.ts   # Tool output parsing
├── tool-config.ts          # Tool configuration
├── code-highlight.ts       # Syntax highlighting
├── server-auth.ts          # Server-side auth utilities
└── utils.ts                # General utilities

types/
├── index.ts               # ChatMessage, ContentBlock, Agent, Session
├── api.ts                 # API request/response types
└── websocket.ts           # WebSocket event type definitions

middleware.ts              # Route protection (redirect to /login)
```

## Authentication Flow

1. User visits `/` → middleware redirects to `/login`
2. Login form submits to `/api/auth/login` → forwards to backend → sets HttpOnly session cookie with JWT
3. Protected routes check session cookie via middleware
4. WebSocket connection: `/api/auth/token` creates user_identity JWT → WebSocket connects with token

## Environment Variables

```bash
# Server-only (never exposed to browser)
API_KEY=your-api-key
BACKEND_API_URL=https://claude-agent-sdk-api.leanwise.ai/api/v1

# Public (browser-accessible)
NEXT_PUBLIC_WS_URL=wss://claude-agent-sdk-api.leanwise.ai/api/v1/ws/chat
```

**Security:** API_KEY and BACKEND_API_URL are server-only. Only NEXT_PUBLIC_WS_URL is exposed to browser.

## Proxy Routes

| Route | Purpose |
|-------|---------|
| `/api/auth/login` | Forward login to backend |
| `/api/auth/logout` | Clear session cookie |
| `/api/auth/session` | Get current user from cookie |
| `/api/auth/token` | Create user_identity JWT for WebSocket |
| `/api/auth/refresh` | Refresh expired tokens |
| `/api/files/upload` | File upload proxy |
| `/api/proxy/*` | Forward REST calls with API key (includes email endpoints) |

## Key Components

| Component | Description |
|-----------|-------------|
| `AuthProvider` | User context and logout |
| `ChatContainer` | Main chat with WebSocket |
| `SessionSidebar` | Sessions list + user profile |
| `AgentGrid` | Agent selection interface |
| `KanbanBoard` | Task tracking panel |
| `LoginForm` | Username/password form |
| `QuestionModal` | AskUserQuestion UI |
| `FilePreviewModal` | File preview (images, PDF, Excel, code) |
| `EmailStatusBadge` | Email connection status display |

## Tool Message Components

Specialized components for displaying tool calls and results:

**Tool Display Components** (`components/chat/tools/`):
- `ask-user-question-display.tsx` - Question modal content
- `plan-mode-display.tsx` - Plan mode entry/exit display
- `todo-write-display.tsx` - Todo list display
- `tool-input-display.tsx` - Tool parameters
- `tool-status-badge.tsx` - Status badge
- `tool-card.tsx` - Card container
- `diff-view.tsx` - Code diff visualization
- `tool-use-message.tsx` - Tool invocations with parameters

**Connection State Components**:
- `connection-error.tsx` - Error display with reconnect
- `connection-banner.tsx` - Reconnection status
- `initial-loading.tsx` - Initial loading spinner
- `history-load-error.tsx` - History loading error with retry

**Image Upload Components**:
- `image-attachment.tsx` - Image preview with remove

## Utility Libraries

### Content Utilities (`lib/content-utils.ts`)
- `normalizeContent()` - Convert string to ContentBlock array
- `extractText()` - Extract text from any format
- `extractImages()` - Get image blocks
- `hasImages()` - Check for images
- `isMultipartContent()` - Type guard
- `toPreviewText()` - Generate preview text

### Message Utilities (`lib/message-utils.ts`)
- `validateMessageContent()` - Validate with error messages
- `createTextBlock()` - Create text blocks
- `createImageUrlBlock()` - Create URL image blocks
- `createImageBase64Block()` - Create base64 image blocks
- `createMultipartMessage()` - Build multi-part messages
- `fileToImageBlock()` - Convert File to image block
- `prepareMessageContent()` - Validate and normalize

### Tool Output Parser (`lib/tool-output-parser.ts`)
- `extractJsonContent()` - Extract JSON from output
- `detectLanguage()` - Detect programming language
- `detectContentType()` - Classify content type
- `formatJson()` - Format JSON

### Code Highlight (`lib/code-highlight.ts`)
- `highlightCodeHtml()` - Syntax highlighting for code
- `highlightJsonHtml()` - JSON highlighting

## Custom Hooks

### Chat Hooks (`hooks/chat-*.ts`)
- **`chat-event-handlers.ts`** - WebSocket event handlers (text_delta, tool_use, plan_approval, etc.)
- **`chat-message-factory.ts`** - Message creation factories
- **`chat-text-utils.ts`** - Text processing
- **`chat-store-types.ts`** - Type definitions

### UI Hooks
- **`use-history-loading.ts`** - History loading with retry
- **`use-connection-tracking.ts`** - Connection state tracking
- **`use-image-upload.ts`** - Image upload state and validation
- **`use-files.ts`** - File CRUD operations
- **`use-agents.ts`** - Agent list fetching
- **`use-session-search.ts`** - Full-text session search

## Scripts

```bash
npm run dev      # Development (turbopack)
npm run build    # Production build
npm run start    # Production server
npm run lint     # ESLint
npx tsc --noEmit # Type check
```

## State Management

Uses **Zustand** for client-side state. All stores in `lib/store/`:

| Store | Purpose | Persistence |
|-------|---------|-------------|
| **chat-store** | Messages, session ID, agent ID, streaming, connection | Partial (sessionId, agentId) |
| **ui-store** | Sidebar state, theme, mobile detection | Full localStorage |
| **kanban-store** | Tasks, tool calls, subagents, session usage | None (session-only) |
| **question-store** | AskUserQuestion modal state, timeout | None (session-only) |
| **plan-store** | Plan approval modal state, feedback, steps | None (session-only) |
| **file-store** | File list, upload state | None (session-only) |
| **file-preview-store** | File preview modal state | None (session-only) |

**Chat Store Behaviors:**
- Messages stored in memory (not persisted) for privacy
- Session and agent IDs persisted to localStorage
- `updateLastMessage` uses functional updates for safe concurrent modifications
- `pendingMessage` supports welcome page "quick start"

## WebSocket Manager

Singleton class (`lib/websocket-manager.ts`) managing connection lifecycle:

- **Auto-reconnection**: Up to 5 attempts with 2-second delay
- **Token refresh**: Automatic refresh on auth failures
- **Deduplication**: Prevents duplicate connections
- **Connection tracking**: Prevents stale handlers with connection ID
- **Message handling**: Support for text, answers, plan approvals, and cancellation

## Key Hooks

### useChat (`hooks/use-chat.ts`)
Main chat hook orchestrating WebSocket events, store updates, and message lifecycle.

**Responsibilities:**
- WebSocket connection lifecycle
- Incoming WebSocket event handling
- Chat store updates with messages
- Session ID synchronization
- Session recovery (session not found errors)

**Key features:**
- Automatic message streaming (text_delta accumulation)
- Tool call visualization
- Pending message support
- Session recovery with toast notifications
- Connection status tracking

### useSessions (`hooks/use-sessions.ts`)
React Query hooks for session CRUD operations.

Provides hooks for:
- Fetch sessions list
- Create/delete/close/update session
- Resume session
- Batch delete sessions

All mutations automatically invalidate cache and show toast notifications on error.

### useWebSocket (`hooks/use-websocket.ts`)
React hook wrapper around WebSocketManager singleton.

Returns memoized functions for:
- connect/disconnect/forceReconnect
- sendMessage/sendAnswer/sendPlanApproval
- onMessage/onStatus/onError callbacks
- getReadyState

## Theming

Uses semantic color token system following Claude.ai's warm terracotta design.

**Color Categories:**
- **Brand**: Primary terracotta color
- **Status**: Success, warning, error, info states
- **Code**: Code block styling
- **Diff**: Code diff highlighting
- **Tool**: Tool-specific accents

**Customization:** Override CSS variables in `:root` and `.dark` for light/dark modes. All colors use HSL format.

See `app/globals.css` for complete token list.
