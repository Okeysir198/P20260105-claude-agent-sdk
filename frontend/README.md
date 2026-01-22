# Claude Chat Frontend

Next.js 16 web application for the Claude Agent SDK chat interface. Features real-time WebSocket streaming, multi-agent selection, session management, and a Claude-themed UI.

## Quick Start

```bash
npm install
cp .env.example .env.local   # Configure API URL and key
npm run dev                   # Start on port 7002
```

## Features

- **Agent Selection** - Dynamic dropdown to switch between agents
- **WebSocket Streaming** - Real-time message streaming with auto-reconnect
- **Session Management** - Sidebar with session history, resume, and delete
- **Dark/Light Mode** - System-aware theme with toggle
- **Responsive Design** - Mobile-friendly layout

## Directory Structure

```
frontend/
├── app/                    # Next.js App Router
│   ├── layout.tsx          # Root layout with ThemeProvider
│   └── page.tsx            # Main chat page
├── components/
│   ├── chat/               # Chat components
│   │   ├── chat-container.tsx
│   │   ├── chat-header.tsx     # Agent selector + session info
│   │   ├── chat-input.tsx
│   │   ├── message-list.tsx
│   │   ├── user-message.tsx
│   │   ├── assistant-message.tsx
│   │   └── welcome-screen.tsx
│   ├── session/            # Session sidebar
│   │   ├── session-sidebar.tsx
│   │   └── session-item.tsx
│   ├── providers/          # Context providers
│   │   └── theme-provider.tsx
│   └── ui/                 # UI primitives (shadcn/ui)
├── hooks/
│   ├── use-claude-chat.ts  # Main chat hook (WebSocket)
│   ├── use-agents.ts       # Fetch agents from API
│   ├── use-sessions.ts     # Session management
│   ├── use-websocket.ts    # WebSocket connection
│   └── use-theme.ts        # Theme management
├── lib/
│   ├── api-client.ts       # HTTP client with auth
│   ├── constants.ts        # API URLs
│   └── utils.ts            # Utilities (cn, etc.)
├── types/
│   ├── events.ts           # WebSocket event types
│   ├── messages.ts         # Message types
│   └── sessions.ts         # Session types
└── styles/
    └── globals.css         # Tailwind + Claude theme
```

## Configuration

### Environment Variables

Create `.env.local` for development:

```bash
NEXT_PUBLIC_API_URL=http://localhost:7001/api/v1
NEXT_PUBLIC_API_KEY=your-api-key
```

Create `.env.production` for production:

```bash
NEXT_PUBLIC_API_URL=https://your-backend-domain.com/api/v1
NEXT_PUBLIC_API_KEY=your-prod-api-key
```

## Hooks

### useClaudeChat

Main hook for chat functionality:

```tsx
import { useClaudeChat } from '@/hooks/use-claude-chat';

function Chat() {
  const {
    messages,          // Message[]
    isStreaming,       // boolean
    isLoading,         // boolean
    error,             // string | null
    sessionId,         // string | null
    turnCount,         // number
    sendMessage,       // (content: string) => Promise<void>
    interrupt,         // () => void
    clearMessages,     // () => void
    startNewSession,   // () => void
    resumeSession,     // (sessionId: string) => Promise<void>
  } = useClaudeChat({
    agentId: 'general-agent-a1b2c3d4',
    onSessionCreated: (id) => console.log('Session:', id),
    onError: (err) => console.error(err),
  });
}
```

### useAgents

Fetch available agents:

```tsx
import { useAgents } from '@/hooks/use-agents';

function AgentSelector() {
  const { agents, loading, error, defaultAgent, refresh } = useAgents();

  return (
    <select>
      {agents.map(agent => (
        <option key={agent.agent_id} value={agent.agent_id}>
          {agent.name}
        </option>
      ))}
    </select>
  );
}
```

### useSessions

Manage session history:

```tsx
import { useSessions } from '@/hooks/use-sessions';

function SessionList() {
  const {
    sessions,        // SessionInfo[]
    loading,         // boolean
    error,           // string | null
    refresh,         // () => Promise<void>
    resumeSession,   // (id: string) => Promise<MessageHistory>
    deleteSession,   // (id: string) => Promise<void>
  } = useSessions();
}
```

## Components

### ChatContainer

Main chat component with header, messages, and input:

```tsx
import { ChatContainer } from '@/components/chat';

<ChatContainer
  showHeader={true}
  selectedSessionId={sessionId}
  onSessionChange={setSessionId}
  agents={agents}
  selectedAgentId={agentId}
  onAgentChange={setAgentId}
/>
```

### ChatHeader

Header with agent selector and session info:

```tsx
import { ChatHeader } from '@/components/chat';

<ChatHeader
  sessionId={sessionId}
  turnCount={5}
  isStreaming={false}
  agents={agents}
  selectedAgentId={agentId}
  onAgentChange={setAgentId}
  onNewSession={handleNew}
  onClear={handleClear}
/>
```

### SessionSidebar

Collapsible sidebar with session list:

```tsx
import { SessionSidebar } from '@/components/session';

<SessionSidebar
  currentSessionId={sessionId}
  onSessionSelect={setSessionId}
  onNewSession={handleNew}
  onSessionDeleted={handleDeleted}
  isCollapsed={collapsed}
  onToggleCollapse={toggleCollapse}
/>
```

## Theming

Uses CSS variables with Claude design language:

```css
/* Light mode */
--claude-primary: #d97706;
--surface-primary: #ffffff;
--text-primary: #1f2937;

/* Dark mode */
--claude-primary: #f59e0b;
--surface-primary: #111827;
--text-primary: #f9fafb;
```

Toggle theme:

```tsx
import { useTheme } from '@/hooks/use-theme';

function ThemeToggle() {
  const { isDark, toggleMode } = useTheme();
  return <button onClick={toggleMode}>{isDark ? 'Light' : 'Dark'}</button>;
}
```

## Scripts

```bash
npm run dev      # Development server (port 7002)
npm run build    # Production build
npm run start    # Production server
npm run lint     # ESLint
```

## API Integration

The frontend connects directly to the backend API:

- **REST API** - Sessions, agents, history via `lib/api-client.ts`
- **WebSocket** - Chat streaming via `hooks/use-websocket.ts`

Authentication:
- REST API uses `X-API-Key` header (query params not accepted)
- WebSocket uses `api_key` query param (browsers cannot send WebSocket headers)
