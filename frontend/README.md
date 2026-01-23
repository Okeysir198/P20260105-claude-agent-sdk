# Claude Agent SDK Chat

Modern, Claude.ai-inspired chat interface for the Claude Agent SDK. Built with Next.js 16, React 19, and shadcn/ui.

## Features

- Real-time WebSocket streaming with text deltas
- Multi-agent support with dynamic switching
- Session persistence and history management
- Markdown rendering with syntax highlighting
- Tool use visualization (tool_use + tool_result)
- Dark/light mode with system preference
- Responsive design (mobile + desktop)
- Type-safe throughout (TypeScript 5)

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

1. Clone the repository and navigate to the frontend directory:

```bash
cd /home/ct-admin/Documents/Langgraph/P20260105-claude-agent-sdk/frontend
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
NEXT_PUBLIC_API_URL=https://cartrack-voice-agents-api.tt-ai.org/api/v1
NEXT_PUBLIC_API_KEY=your-api-key-here
```

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
├── app/                    # Next.js App Router
│   ├── layout.tsx         # Root layout with providers
│   ├── page.tsx           # Main page
│   ├── globals.css        # Global styles
│   ├── loading.tsx        # Loading state
│   └── error.tsx          # Error state
├── components/            # React components
│   ├── ui/               # shadcn/ui components
│   ├── chat/             # Chat-related components
│   ├── session/          # Session management components
│   ├── agent/            # Agent selection components
│   ├── providers/        # Context providers
│   └── error/            # Error handling components
├── hooks/                # Custom React hooks
│   ├── use-agents.ts     # Agent queries
│   ├── use-sessions.ts   # Session mutations
│   ├── use-chat.ts       # Chat orchestration
│   ├── use-websocket.ts  # WebSocket management
│   └── use-keyboard-shortcuts.ts  # Keyboard shortcuts
├── lib/                  # Utility libraries
│   ├── store/           # Zustand stores
│   ├── api-client.ts    # REST API client
│   ├── websocket-manager.ts  # WebSocket wrapper
│   ├── utils.ts         # Utility functions
│   ├── constants.ts     # App constants
│   └── toast.ts         # Toast helpers
├── types/               # TypeScript definitions
│   ├── api.ts          # API types
│   ├── websocket.ts    # WebSocket types
│   └── index.ts        # Type exports
└── public/             # Static assets
```

## Key Components

### Chat Components

- `ChatContainer` - Main chat wrapper
- `MessageList` - Scrollable message area
- `ChatInput` - Auto-resize input with send button
- `UserMessage` / `AssistantMessage` - Message bubbles
- `ToolUseMessage` / `ToolResultMessage` - Tool execution display

### Session Components

- `SessionSidebar` - Session list sidebar
- `SessionItem` - Individual session row
- `NewSessionButton` - Create new conversation

### Agent Components

- `AgentGrid` - Agent selection cards
- `AgentSwitcher` - Dropdown agent selector

## API Integration

The frontend integrates with the backend API at:

- Production: `https://cartrack-voice-agents-api.tt-ai.org/api/v1`

### Endpoints Used

- `GET /config/agents` - List available agents
- `GET /sessions` - List all sessions
- `POST /sessions` - Create new session
- `GET /sessions/{id}/history` - Get session history
- `DELETE /sessions/{id}` - Delete session
- `POST /sessions/{id}/close` - Close session
- `POST /sessions/{id}/resume` - Resume session
- `WS /ws/chat` - WebSocket chat connection

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API URL | Production URL |
| `NEXT_PUBLIC_API_KEY` | API authentication key | (required) |
| `NEXT_PUBLIC_WS_URL` | WebSocket URL | Derived from API_URL |

## Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm start` - Start production server
- `npm run lint` - Run ESLint

## License

MIT
