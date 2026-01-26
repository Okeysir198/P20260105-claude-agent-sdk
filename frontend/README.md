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
NEXT_PUBLIC_API_URL=https://claude-agent-sdk-fastapi-sg4.tt-ai.org/api/v1
NEXT_PUBLIC_API_KEY=your-api-key-here
```

**Important:** Always use the production API URL. Never use localhost for backend connections.

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
│   ├── api-client.ts      # REST API client
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

The frontend integrates with the backend API:

### Endpoints Used

- `GET /config/agents` - List available agents
- `GET /sessions` - List all sessions
- `POST /sessions` - Create new session
- `GET /sessions/{id}/history` - Get session history
- `DELETE /sessions/{id}` - Delete session
- `POST /sessions/{id}/close` - Close session
- `POST /sessions/{id}/resume` - Resume session
- `WS /ws/chat` - WebSocket chat connection

### Authentication

- REST API: `X-API-Key` header
- WebSocket: `api_key` query parameter

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API URL (production only) | `https://claude-agent-sdk-fastapi-sg4.tt-ai.org/api/v1` |
| `NEXT_PUBLIC_API_KEY` | API authentication key | (required) |
| `NEXT_PUBLIC_WS_URL` | WebSocket URL | Derived from API_URL |

**Important:** The frontend is configured to always connect to the production backend. Localhost connections are not supported.

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
