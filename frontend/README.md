# Claude Agent SDK Chat - Frontend

Modern, Claude.ai-inspired chat interface for the Claude Agent SDK. Built with Next.js 16, React 19, and shadcn/ui.

## Features

- Real-time WebSocket streaming with text deltas
- Multi-agent support with dynamic switching
- Session persistence and history management
- Markdown rendering with syntax highlighting
- Tool use visualization (tool_use + tool_result)
- AskUserQuestion modal for interactive clarification
- Dark/light mode with system preference
- Resizable session sidebar (240-500px)
- Keyboard shortcuts (Ctrl+K, Ctrl+Enter, Escape)
- Responsive design (mobile + desktop)

## Tech Stack

- **Framework**: Next.js 16 (App Router)
- **React**: 19
- **UI Library**: shadcn/ui (Radix UI primitives)
- **Styling**: Tailwind CSS 3
- **State Management**: Zustand 5
- **Data Fetching**: TanStack Query 5
- **Markdown**: react-markdown + remark-gfm + rehype-highlight
- **Icons**: Lucide React
- **Theme**: next-themes

## Prerequisites

- Node.js 18+
- npm or yarn

## Installation

1. Navigate to the frontend directory:

```bash
cd frontend
```

2. Install dependencies:

```bash
npm install
```

3. Create environment variables:

```bash
cp .env.example .env.local
```

4. Configure your environment variables in `.env.local`:

```env
# Server-only variables (NEVER exposed to browser)
API_KEY=your-api-key
BACKEND_API_URL=https://claude-agent-sdk-fastapi-sg4.tt-ai.org

# Public variables (safe for browser)
NEXT_PUBLIC_WS_URL=wss://claude-agent-sdk-fastapi-sg4.tt-ai.org/api/v1/ws/chat
```

**Important:**
- `API_KEY` and `BACKEND_API_URL` are server-only (no `NEXT_PUBLIC_` prefix) - they are NEVER sent to the browser
- REST API calls go through proxy routes (`/api/proxy/*`) which add the API key server-side
- WebSocket uses JWT obtained via `/api/auth/token` proxy, then connects directly to backend

## Development

Start the development server:

```bash
npm run dev
```

Open [http://localhost:7002](http://localhost:7002) in your browser.

## Build for Production

```bash
npm run build
npm start
```

## Project Structure

```
frontend/
├── app/
│   ├── layout.tsx         # Root layout with providers
│   ├── page.tsx           # Main page
│   ├── globals.css        # Global styles
│   ├── loading.tsx        # Loading state
│   └── error.tsx          # Error state
├── components/
│   ├── agent/             # Agent selection UI
│   │   ├── agent-grid.tsx
│   │   └── agent-switcher.tsx
│   ├── chat/              # Chat UI components
│   │   ├── chat-container.tsx
│   │   ├── chat-header.tsx
│   │   ├── chat-input.tsx
│   │   ├── message-list.tsx
│   │   ├── user-message.tsx
│   │   ├── assistant-message.tsx
│   │   ├── tool-use-message.tsx
│   │   ├── tool-result-message.tsx
│   │   ├── question-modal.tsx
│   │   ├── code-block.tsx
│   │   ├── status-indicator.tsx
│   │   ├── typing-indicator.tsx
│   │   ├── welcome-screen.tsx
│   │   └── error-message.tsx
│   ├── session/           # Session management
│   │   ├── session-sidebar.tsx
│   │   ├── session-item.tsx
│   │   └── new-session-button.tsx
│   ├── ui/                # shadcn/ui components
│   └── providers/         # Context providers
├── hooks/
│   ├── use-chat.ts        # Chat orchestration
│   ├── use-websocket.ts   # WebSocket management
│   ├── use-agents.ts      # Agent queries
│   ├── use-sessions.ts    # Session mutations
│   ├── use-session-history.ts  # History retrieval
│   └── use-keyboard-shortcuts.ts
├── lib/
│   ├── api-client.ts      # REST API client (JWT auth)
│   ├── auth.ts            # JWT token service
│   ├── websocket-manager.ts  # WebSocket manager (JWT auth)
│   └── constants.ts       # App constants
└── types/                 # TypeScript definitions
```

## Key Components

### Chat Components

- `ChatContainer` - Main chat wrapper with state management
- `MessageList` - Scrollable message area with auto-scroll
- `ChatInput` - Auto-resize textarea with send button
- `UserMessage` / `AssistantMessage` - Message bubbles
- `ToolUseMessage` / `ToolResultMessage` - Tool execution display
- `QuestionModal` - AskUserQuestion interactive modal

### Session Components

- `SessionSidebar` - Resizable session list (240-500px)
- `SessionItem` - Individual session row with metadata
- `NewSessionButton` - Create new conversation

### Agent Components

- `AgentGrid` - Agent selection cards grid
- `AgentSwitcher` - Dropdown agent selector

## API Integration

The frontend uses a **proxy architecture** to keep the API key secure on the server.

### Architecture

```
REST API:
  Browser ──────> /api/proxy/* ──────> Backend /api/v1/*
    (no secrets)   (adds API_KEY)       claude-agent-sdk-fastapi-sg4.tt-ai.org

WebSocket:
  Browser ──────> /api/auth/token ──────> JWT created locally (no backend call)
    │               (derives JWT_SECRET
    │                from API_KEY)
    └───────────> wss://backend/ws/chat?token=JWT (DIRECT)
```

### JWT Secret Derivation

JWT tokens are created **locally** on the Next.js server - no backend call needed:

```typescript
// JWT secret derived from API_KEY using HMAC-SHA256
const salt = 'claude-agent-sdk-jwt-v1';
const jwtSecret = createHmac('sha256', salt).update(apiKey).digest('hex');
```

Both frontend and backend use the same derivation, ensuring tokens are valid across both.

### Proxy Routes

| Frontend Route | Purpose | Description |
|----------------|---------|-------------|
| `/api/proxy/*` | REST API proxy | Forwards to `/api/v1/*` with X-API-Key header |
| `/api/auth/token` | Create JWT | Creates JWT locally using derived secret |
| `/api/auth/refresh` | Refresh JWT | Creates new JWT using refresh token |

### API Calls (via Proxy)

- `GET /api/proxy/config/agents` - List available agents
- `GET /api/proxy/sessions` - List all sessions
- `GET /api/proxy/sessions/{id}/history` - Get session history
- `DELETE /api/proxy/sessions/{id}` - Delete session
- `POST /api/proxy/sessions/{id}/close` - Close session
- `POST /api/proxy/sessions/{id}/resume` - Resume session

### Authentication Flow

1. **REST API**: Browser calls `/api/proxy/*` routes, which add `X-API-Key` header server-side
2. **WebSocket JWT**: Browser calls `/api/auth/token` which creates JWT locally (derives secret from API_KEY)
3. **WebSocket Connect**: Browser connects directly to backend with JWT: `wss://backend/ws/chat?token=JWT`
4. **JWT Refresh**: Before token expires, call `/api/auth/refresh` to get new JWT (also created locally)

**Security:**
- API key is NEVER exposed to the browser
- JWT secret derived from API_KEY using HMAC-SHA256 (cannot reverse to get API_KEY)
- JWT tokens are short-lived (30 min access, 7 day refresh)
- JWT is only used for WebSocket authentication
- No network call needed for token creation - happens locally on Next.js server

## Environment Variables

| Variable | Scope | Description |
|----------|-------|-------------|
| `API_KEY` | Server only | API key for backend authentication |
| `BACKEND_API_URL` | Server only | Backend URL (e.g., `https://claude-agent-sdk-fastapi-sg4.tt-ai.org`) |
| `NEXT_PUBLIC_WS_URL` | Public | WebSocket URL (e.g., `wss://...tt-ai.org/api/v1/ws/chat`) |

**Security Model:**
- Variables WITHOUT `NEXT_PUBLIC_` prefix are server-only (never sent to browser)
- Only `NEXT_PUBLIC_WS_URL` is exposed to the browser
- API key stays on the Next.js server, used by proxy routes

## Keyboard Shortcuts

- `Ctrl/Cmd + K` - Focus input
- `Ctrl/Cmd + Enter` - Send message
- `Escape` - Close modal

## Scripts

- `npm run dev` - Start development server (turbopack)
- `npm run build` - Build for production
- `npm start` - Start production server
- `npm run lint` - Run ESLint

## License

MIT
