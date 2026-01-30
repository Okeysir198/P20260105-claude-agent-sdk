# Claude Agent SDK - Frontend

Next.js 15 chat interface with user authentication, WebSocket streaming, and per-user sessions.

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
- Session sidebar with user profile
- AskUserQuestion modal
- Dark/light mode
- Keyboard shortcuts (Ctrl+K, Ctrl+Enter, Escape)

## Architecture

```
app/
├── (auth)/login/           # Login page (public)
├── api/
│   ├── auth/               # Login, logout, session, token routes
│   └── proxy/              # REST API proxy (adds API key)
├── page.tsx                # Main chat (protected)
└── layout.tsx              # Root layout with providers

components/
├── chat/                   # Chat UI components
│   ├── tools/              # Tool-specific display components
│   ├── connection-*.tsx    # Connection state components
│   └── chat-*.tsx          # Chat core components
├── session/                # Sidebar with user profile
├── features/auth/          # Login form, logout button
└── providers/              # Auth, Query, Theme providers

lib/
├── session.ts              # HttpOnly session cookie
├── websocket-manager.ts    # Auto-fetch JWT for WebSocket
├── auth.ts                 # Token service
├── content-utils.ts        # Content normalization (multi-part messages)
├── message-utils.ts        # Message creation helpers
├── tool-output-parser.ts   # Tool output parsing
├── code-highlight.ts       # Syntax highlighting
└── api-client.ts           # REST API client with auth

hooks/
├── use-chat.ts             # Main chat hook (204 lines)
├── chat-event-handlers.ts  # WebSocket event handlers
├── chat-message-factory.ts # Message creation utilities
├── use-websocket.ts        # WebSocket wrapper
├── use-sessions.ts         # Session CRUD operations
├── use-history-loading.ts  # History loading logic
├── use-connection-tracking.ts # Connection state tracking
└── use-image-upload.ts     # Image upload handling

middleware.ts               # Route protection
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
BACKEND_API_URL=https://claude-agent-sdk-fastapi-sg4.tt-ai.org/api/v1

# Public (browser-accessible)
NEXT_PUBLIC_WS_URL=wss://claude-agent-sdk-fastapi-sg4.tt-ai.org/api/v1/ws/chat
```

**Security:** API_KEY and BACKEND_API_URL are server-only. Only NEXT_PUBLIC_WS_URL is exposed to browser.

## Proxy Routes

| Route | Purpose |
|-------|---------|
| `/api/auth/login` | Forward login to backend |
| `/api/auth/logout` | Clear session cookie |
| `/api/auth/session` | Get current user from cookie |
| `/api/auth/token` | Create user_identity JWT for WebSocket |
| `/api/proxy/*` | Forward REST calls with API key |

## Key Components

| Component | Description |
|-----------|-------------|
| `AuthProvider` | User context and logout |
| `ChatContainer` | Main chat with WebSocket |
| `SessionSidebar` | Sessions list + user profile |
| `LoginForm` | Username/password form |
| `QuestionModal` | AskUserQuestion UI |

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
- `tool-result-message.tsx` - Tool execution results with syntax highlighting
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
- **`chat-event-handlers.ts`** - WebSocket event handlers
- **`chat-message-factory.ts`** - Message creation factories
- **`chat-text-utils.ts`** - Text processing
- **`chat-store-types.ts`** - Type definitions

### UI Hooks
- **`use-history-loading.ts`** - History loading with retry
- **`use-connection-tracking.ts`** - Connection state tracking
- **`use-image-upload.ts`** - Image upload state and validation

## Scripts

```bash
npm run dev      # Development (turbopack)
npm run build    # Production build
npm run start    # Production server
npm run lint     # ESLint
```

## State Management

Uses **Zustand** for client-side state. All stores in `lib/store/`:

| Store | Purpose | Persistence |
|-------|---------|-------------|
| **chat-store** | Messages, session ID, agent ID, streaming, connection | Partial (sessionId, agentId) |
| **ui-store** | Sidebar state, theme, mobile detection | Full localStorage |
| **question-store** | AskUserQuestion modal state, timeout | None (session-only) |
| **plan-store** | Plan approval modal state, feedback, steps | None (session-only) |

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
- **Message handling**: Support for text, answers, and plan approvals

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
