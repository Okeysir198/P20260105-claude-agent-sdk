# Claude Chat UI

A React component library for building chat interfaces with the Claude Agent SDK. Features a complete set of chat components, session management, theming support, and SSE streaming utilities.

## Quick Start

```tsx
import {
  ChatContainer,
  ThemeProvider,
  useClaudeChat,
} from 'claude-chat-ui';

function App() {
  return (
    <ThemeProvider>
      <ChatContainer />
    </ThemeProvider>
  );
}
```

## Installation

```bash
npm install claude-chat-ui
# or
yarn add claude-chat-ui
# or
pnpm add claude-chat-ui
```

## Components

### Chat Components

The core building blocks for chat interfaces:

```tsx
import {
  ChatContainer,    // Main chat container with header, messages, and input
  ChatHeader,       // Header with title and controls
  ChatInput,        // Message input with auto-resize
  MessageList,      // Scrollable message list
  MessageItem,      // Individual message wrapper
  UserMessage,      // User message bubble
  AssistantMessage, // Assistant response bubble
  ToolUseMessage,   // Tool invocation display
  ToolResultMessage,// Tool result display
  TypingIndicator,  // Animated typing dots
  ErrorMessage,     // Error display component
} from 'claude-chat-ui';
```

### Session Components

Components for managing conversation sessions:

```tsx
import {
  SessionSidebar,   // Sidebar with session list
  SessionItem,      // Individual session item
  NewSessionButton, // Button to create new session
} from 'claude-chat-ui';
```

### UI Primitives

Reusable UI components based on shadcn/ui:

```tsx
import {
  Button,
  Badge,
  Textarea,
  ScrollArea,
  Skeleton,
  Tooltip,
  TooltipProvider,
} from 'claude-chat-ui';
```

## Hooks

### useClaudeChat

Main hook for managing chat state and interactions:

```tsx
import { useClaudeChat } from 'claude-chat-ui';

function ChatComponent() {
  const {
    messages,
    isLoading,
    error,
    sendMessage,
    clearMessages,
    interruptTask,
  } = useClaudeChat({
    apiBaseUrl: 'http://localhost:7001/api/v1',
    onError: (err) => console.error(err),
  });

  const handleSend = async (text: string) => {
    await sendMessage(text);
  };

  return (
    <div>
      {messages.map((msg) => (
        <MessageItem key={msg.id} message={msg} />
      ))}
      <ChatInput onSend={handleSend} disabled={isLoading} />
    </div>
  );
}
```

### useSessions

Hook for managing session history:

```tsx
import { useSessions } from 'claude-chat-ui';

function SessionList() {
  const {
    sessions,
    isLoading,
    error,
    refresh,
    resumeSession,
    deleteSession,
  } = useSessions({
    autoRefresh: true,
    refreshInterval: 30000,
  });

  return (
    <ul>
      {sessions.map((session) => (
        <li key={session.id} onClick={() => resumeSession(session.id)}>
          {session.title}
        </li>
      ))}
    </ul>
  );
}
```

### useTheme

Hook for theme management (standalone, without provider):

```tsx
import { useTheme } from 'claude-chat-ui';

function ThemeToggle() {
  const { isDark, toggleMode, setMode, colors } = useTheme();

  return (
    <button onClick={toggleMode}>
      {isDark ? 'Light Mode' : 'Dark Mode'}
    </button>
  );
}
```

### useAutoResize

Hook for auto-resizing textareas:

```tsx
import { useAutoResize } from 'claude-chat-ui';

function AutoResizeInput() {
  const textareaRef = useAutoResize<HTMLTextAreaElement>();

  return (
    <textarea
      ref={textareaRef}
      placeholder="Type a message..."
    />
  );
}
```

### useSSEStream

Low-level hook for SSE streaming:

```tsx
import { useSSEStream, parseSSEStream } from 'claude-chat-ui';

function StreamingComponent() {
  const { startStream, stopStream, isStreaming } = useSSEStream({
    onEvent: (event) => {
      console.log('Received:', event);
    },
    onError: (error) => {
      console.error('Stream error:', error);
    },
  });

  return (
    <button onClick={() => startStream('/api/stream')}>
      {isStreaming ? 'Stop' : 'Start'} Stream
    </button>
  );
}
```

## Theming

### ThemeProvider

Wrap your app with ThemeProvider for theme context:

```tsx
import { ThemeProvider, useThemeContext } from 'claude-chat-ui';

function App() {
  return (
    <ThemeProvider
      initialTheme={{ mode: 'system' }}
      storageKey="my-app-theme"
    >
      <MyApp />
    </ThemeProvider>
  );
}

function ThemeToggle() {
  const { isDark, toggleMode, setMode } = useThemeContext();

  return (
    <div>
      <button onClick={toggleMode}>Toggle</button>
      <button onClick={() => setMode('light')}>Light</button>
      <button onClick={() => setMode('dark')}>Dark</button>
      <button onClick={() => setMode('system')}>System</button>
    </div>
  );
}
```

### Theme Customization

Override default colors and settings:

```tsx
<ThemeProvider
  initialTheme={{
    mode: 'dark',
    borderRadius: 'lg',
    fontFamily: 'mono',
    colorOverrides: {
      '--primary': '#ff6b6b',
      '--background': '#1a1a2e',
    },
  }}
>
  <App />
</ThemeProvider>
```

### CSS Variables

The theme system uses CSS custom properties that can be used directly:

```css
.my-component {
  background: var(--claude-background);
  color: var(--claude-foreground);
  border: 1px solid var(--claude-border);
}

.my-button {
  background: var(--claude-primary);
}

.my-button:hover {
  background: var(--claude-primary-hover);
}
```

Available CSS variables:
- `--claude-primary`, `--claude-primary-hover`
- `--claude-background`, `--claude-background-secondary`
- `--claude-foreground`, `--claude-foreground-muted`
- `--claude-border`, `--claude-border-muted`
- `--claude-accent`, `--claude-accent-foreground`
- `--claude-success`, `--claude-warning`, `--claude-error`, `--claude-info`

## Types

All TypeScript types are exported for type-safe development:

```tsx
import type {
  // Messages
  Message,
  UserMessageType,
  AssistantMessageType,
  ToolUseMessageType,
  ToolResultMessageType,

  // Sessions
  SessionInfo,
  SessionListResponse,

  // Events
  ParsedSSEEvent,
  SSEEventType,

  // Theme
  ThemeConfig,
  ThemeMode,
  ClaudeThemeColors,
} from 'claude-chat-ui';
```

## Utilities

### cn (className merger)

Utility for merging Tailwind classes:

```tsx
import { cn } from 'claude-chat-ui';

function Component({ className }: { className?: string }) {
  return (
    <div className={cn('base-class', className)}>
      Content
    </div>
  );
}
```

### Animation Variants

Pre-built Framer Motion animation variants:

```tsx
import {
  messageVariants,
  fadeVariants,
  slideVariants,
  springTransition,
} from 'claude-chat-ui';
import { motion } from 'framer-motion';

function AnimatedMessage() {
  return (
    <motion.div
      variants={messageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
    >
      Message content
    </motion.div>
  );
}
```

### Constants

```tsx
import {
  CLAUDE_COLORS,      // Claude design language colors
  DEFAULT_API_URL,    // Default API endpoint
  ANIMATION_DURATION, // Standard animation timings
  BREAKPOINTS,        // Responsive breakpoints
} from 'claude-chat-ui';
```

## Environment Configuration

Configure the API endpoint via environment variables:

```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:7001/api/v1
```

Or pass directly to hooks:

```tsx
const chat = useClaudeChat({
  apiBaseUrl: 'https://api.example.com/v1',
});
```

## License

MIT
