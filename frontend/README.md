# TT-Bot - Frontend

Next.js chat interface with user authentication, WebSocket streaming, and per-user sessions.

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
├── session/                # Sidebar with user profile
├── features/auth/          # Login form, logout button
└── providers/              # Auth, Query, Theme providers

lib/
├── session.ts              # HttpOnly session cookie
├── websocket-manager.ts    # Auto-fetch JWT for WebSocket
└── auth.ts                 # Token service

middleware.ts               # Route protection
```

## Authentication Flow

```
1. User visits / → middleware redirects to /login

2. Login form submits to /api/auth/login
   → Forwards to backend /api/v1/auth/login
   → Sets HttpOnly session cookie with JWT

3. Protected routes check session cookie via middleware

4. WebSocket connection:
   → /api/auth/token creates user_identity JWT from session
   → WebSocket connects with token containing username
```

## Environment Variables

```bash
# Server-only (never exposed to browser)
API_KEY=your-api-key
BACKEND_API_URL=https://claude-agent-sdk-fastapi-sg4.tt-ai.org/api/v1

# Public (browser-accessible)
NEXT_PUBLIC_WS_URL=wss://claude-agent-sdk-fastapi-sg4.tt-ai.org/api/v1/ws/chat
```

**Security:**
- `API_KEY` and `BACKEND_API_URL` are server-only
- Only `NEXT_PUBLIC_WS_URL` is exposed to browser
- JWT secret derived from API_KEY (same as backend)
- Session stored in HttpOnly cookie

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

## Scripts

```bash
npm run dev      # Development (turbopack)
npm run build    # Production build
npm run start    # Production server
npm run lint     # ESLint
```

## State Management

The application uses **Zustand** for client-side state management, providing a lightweight and performant solution for managing application state without prop drilling.

### Store Architecture

All stores are located in `lib/store/` and follow Zustand's best practices:

| Store | Purpose | Persistence |
|-------|---------|-------------|
| **chat-store** | Messages, session ID, agent ID, streaming state, connection status | Partial (sessionId, agentId) |
| **ui-store** | Sidebar state, theme preference, mobile detection | Full localStorage |
| **question-store** | AskUserQuestion modal state, timeout countdown | None (session-only) |
| **plan-store** | Plan approval modal state, feedback, steps | None (session-only) |

### Chat Store (`lib/store/chat-store.ts`)

Core chat state management:

```typescript
interface ChatState {
  // State
  messages: ChatMessage[];
  sessionId: string | null;
  agentId: string | null;
  isStreaming: boolean;
  connectionStatus: ConnectionStatus;
  pendingMessage: string | null;

  // Actions
  addMessage: (message: ChatMessage) => void;
  updateLastMessage: (updater: (msg: ChatMessage) => ChatMessage) => void;
  setMessages: (messages: ChatMessage[]) => void;
  setSessionId: (id: string | null) => void;
  setAgentId: (id: string | null) => void;
  setStreaming: (streaming: boolean) => void;
  setConnectionStatus: (status: ConnectionStatus) => void;
  setPendingMessage: (message: string | null) => void;
  clearMessages: () => void;
}
```

**Key behaviors:**
- Messages are stored in memory (not persisted) for privacy
- Session and agent IDs are persisted to localStorage for session recovery
- `updateLastMessage` uses functional updates for safe concurrent modifications
- `pendingMessage` supports the welcome page "quick start" feature

### UI Store (`lib/store/ui-store.ts`)

Global UI preferences:

```typescript
interface UIState {
  sidebarOpen: boolean;
  theme: 'light' | 'dark' | 'system';
  isMobile: boolean;

  setSidebarOpen: (open: boolean) => void;
  setTheme: (theme: 'light' | 'dark' | 'system') => void;
  setIsMobile: (mobile: boolean) => void;
}
```

**Key behaviors:**
- Fully persisted to localStorage
- Theme preference integrates with `next-themes` provider
- Mobile state affects responsive layout behavior

### Question Store (`lib/store/question-store.ts`)

AskUserQuestion modal state:

```typescript
interface QuestionState {
  isOpen: boolean;
  questionId: string | null;
  questions: UIQuestion[];
  timeoutSeconds: number;
  remainingSeconds: number;
  answers: Record<string, string | string[]>;

  openModal: (questionId: string, questions: UIQuestion[], timeout: number) => void;
  closeModal: () => void;
  setAnswer: (question: string, answer: string | string[]) => void;
  tick: () => void;
  reset: () => void;
}
```

**Key behaviors:**
- Not persisted (modal state is session-only)
- `tick()` function decrements timeout every second
- Answers map question text to selected values

### Plan Store (`lib/store/plan-store.ts`)

Plan approval modal state:

```typescript
interface PlanState {
  isOpen: boolean;
  planId: string | null;
  title: string;
  summary: string;
  steps: UIPlanStep[];
  timeoutSeconds: number;
  remainingSeconds: number;
  feedback: string;

  openModal: (planId: string, title: string, summary: string, steps: UIPlanStep[], timeout: number) => void;
  closeModal: () => void;
  setFeedback: (feedback: string) => void;
  tick: () => void;
  reset: () => void;
}
```

**Key behaviors:**
- Not persisted (modal state is session-only)
- Steps support status tracking: `pending`, `in_progress`, `completed`
- Feedback is optional user commentary on plan approval/rejection

### State Flow Between Components

```
1. User selects agent
   └─> useChatStore.setAgentId()

2. useChat() hook detects agentId change
   └─> WebSocketManager.connect(agentId, sessionId)

3. WebSocket ready event
   └─> useChatStore.setSessionId(event.session_id)
   └─> React Query cache invalidated (refresh sessions list)

4. User sends message
   └─> useChat().sendMessage(content)
       └─> ChatStore.addMessage(userMessage)
       └─> WebSocketManager.sendMessage(content)

5. WebSocket streaming response
   └─> text_delta event
       └─> ChatStore.updateLastMessage() (append content)

6. Tool execution
   └─> tool_use event
       └─> ChatStore.addMessage(toolUseMessage)
   └─> tool_result event
       └─> ChatStore.addMessage(toolResultMessage)

7. User question/plan modal
   └─> ask_user_question / plan_approval event
       └─> QuestionStore.openModal() / PlanStore.openModal()
   └─> User submits response
       └─> WebSocketManager.sendAnswer() / sendPlanApproval()
```

### Usage Example

```typescript
// In component
import { useChatStore } from '@/lib/store/chat-store';

function ChatComponent() {
  const { messages, addMessage, isStreaming } = useChatStore();

  // Selector optimization (prevents re-renders)
  const agentId = useChatStore((state) => state.agentId);

  return <div>{messages.map(...)}</div>;
}
```

## WebSocket Manager

The WebSocket manager (`lib/websocket-manager.ts`) is a singleton class that manages the WebSocket connection lifecycle, including auto-reconnection, token refresh, and message handling.

### Architecture

```typescript
class WebSocketManager {
  // Private state
  private ws: WebSocket | null = null;
  private connectionId: number = 0;           // Prevents stale handlers
  private isConnecting: boolean = false;       // Tracks async connection phase
  private pendingAgentId: string | null = null;
  private pendingSessionId: string | null = null;
  private reconnectAttempts: number = 0;
  private manualClose: boolean = false;

  // Callback registries (Set for automatic cleanup)
  private onMessageCallbacks: Set<EventCallback>;
  private onErrorCallbacks: Set<ErrorCallback>;
  private onStatusCallbacks: Set<StatusCallback>;
}
```

### Connection Lifecycle

#### 1. Initial Connection

```typescript
connect(agentId: string, sessionId: string | null)
  └─> Check if already connected (deduplication)
  └─> Cancel pending connections
  └─> Close existing connection if different agent/session
  └─> _doConnect(agentId, sessionId)
      ├─> Set isConnecting = true (includes async token fetch)
      ├─> tokenService.getAccessToken() // Auto-fetch if missing
      ├─> Create WebSocket with token in URL params
      ├─> Set isConnecting = false (WebSocket object created)
      └─> Register event handlers
```

#### 2. Connection Deduplication

The manager prevents duplicate connections with three checks:

1. **Already connected** to same agent/session
   ```typescript
   if (ws?.readyState === WebSocket.OPEN &&
       agentId === currentAgentId &&
       sessionId === currentSessionId) {
     return; // Ignore
   }
   ```

2. **Already connecting** to same agent/session
   ```typescript
   if (isConnecting &&
       pendingAgentId === agentId &&
       pendingSessionId === sessionId) {
     return; // Ignore
   }
   ```

3. **Connection ID increment** prevents stale handlers
   ```typescript
   connectionId++; // Invalidate old connection's event handlers
   ```

#### 3. Agent/Session Switching

```typescript
connect(newAgentId, newSessionId)
  └─> Detect different agent/session
      ├─> Set manualClose = true
      ├─> connectionId++ (invalidate old handlers)
      ├─> ws.close()
      └─> setTimeout(500ms) // Backend cleanup grace period
          └─> _doConnect(newAgentId, newSessionId)
```

**Why the delay?** Prevents race conditions when backend hasn't cleaned up the old connection yet.

#### 4. Auto-Reconnection

```typescript
ws.onclose = (event) => {
  // Check for auth failure
  if (event.code === 1008 || reason.includes('expired')) {
    └─> tokenService.refreshToken()
        └─> On success: reconnect
        └─> On failure: tokenService.fetchTokens()
  }

  // Reconnect if not manual close
  if (!manualClose && reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
    └─> setTimeout(RECONNECT_DELAY, connect(pendingAgentId, pendingSessionId))
  }
}
```

**Reconnect behavior:**
- Maximum attempts: 5 (configurable via `MAX_RECONNECT_ATTEMPTS`)
- Delay: 2 seconds (configurable via `RECONNECT_DELAY`)
- Uses `pendingAgentId/pendingSessionId` (values at connection start)
- Auth failures trigger automatic token refresh before reconnect

### Auto-Token Refresh

The WebSocket manager integrates with `tokenService` to maintain authentication:

```typescript
// During connection
let accessToken = await tokenService.getAccessToken();
if (!accessToken) {
  await tokenService.fetchTokens(); // Auto-fetch from session
}
wsUrl.searchParams.set('token', accessToken);

// On close with auth failure
if (event.code === 1008 || reason.includes('expired')) {
  const newToken = await tokenService.refreshToken();
  if (!newToken) {
    await tokenService.fetchTokens();
  }
  // Reconnect with new token
}
```

**Key features:**
- Token fetched async before connection (`isConnecting` flag prevents race conditions)
- Auth failures trigger automatic refresh + reconnect
- Token refresh falls back to full token fetch if refresh fails
- No manual token management required in components

### Message Handling

#### Sending Messages

```typescript
// Simple text message
sendMessage(content: string)

// User question answer
sendAnswer(questionId: string, answers: Record<string, string | string[]>)

// Plan approval response
sendPlanApproval(planId: string, approved: boolean, feedback?: string)
```

#### Receiving Messages

```typescript
// Register callback
const unsubscribe = wsManager.onMessage((event: WebSocketEvent) => {
  switch (event.type) {
    case 'text_delta': /* ... */
    case 'tool_use': /* ... */
    case 'ask_user_question': /* ... */
    // etc.
  }
});

// Cleanup
unsubscribe(); // Removes callback from Set
```

### Status Tracking

```typescript
wsManager.onStatus((status: 'connecting' | 'connected' | 'disconnected') => {
  // Update UI based on connection state
});
```

### Force Reconnect

```typescript
// Immediate reconnect without delays (e.g., after session deletion)
forceReconnect(agentId: string | null, sessionId: string | null)
  └─> Cancel pending connections
  └─> connectionId++
  └─> Close existing WebSocket
  └─> Reset stored IDs (prevent deduplication)
  └─> _doConnect() immediately (no 500ms delay)
```

### Usage in Components

```typescript
import { useWebSocket } from '@/hooks/use-websocket';

function ChatComponent() {
  const ws = useWebSocket();

  useEffect(() => {
    const unsubscribe = ws.onMessage((event) => {
      console.log('Received:', event);
    });
    return unsubscribe;
  }, [ws]);

  const sendMessage = () => {
    ws.sendMessage('Hello, agent!');
  };
}
```

### Connection State Debugging

The manager logs key events:

- `Connecting to WebSocket:` (with URL, token redacted)
- `WebSocket connected successfully`
- `WebSocket closed:` (with code, reason, wasClean)
- `Reconnecting... Attempt X/Y`
- `Token expired, attempting to refresh...`
- `Already connected to the same agent/session, ignoring duplicate connect call`

**Pro tip:** These logs help diagnose connection issues without exposing sensitive tokens.

## Key Hooks

Custom hooks provide reusable stateful logic for WebSocket communication, chat management, and session operations.

### useChat (`hooks/use-chat.ts`)

The main chat hook that orchestrates WebSocket events, store updates, and message lifecycle.

**Responsibilities:**
- Manages WebSocket connection lifecycle
- Handles incoming WebSocket events
- Updates chat store with messages
- Manages session ID synchronization
- Handles session recovery (session not found errors)

**Key features:**
- Automatic message streaming (text_delta accumulation)
- Tool call visualization (tool_use/tool_result messages)
- Pending message support (welcome page quick start)
- Session recovery with toast notifications
- Connection status tracking

**State management:**
```typescript
const {
  messages,        // All chat messages
  sessionId,       // Current session ID
  agentId,         // Selected agent ID
  status,          // Connection status
  isStreaming,     // Is agent currently streaming
  sendMessage,     // Send user message
  sendAnswer,      // Answer user question
  sendPlanApproval, // Approve/reject plan
  disconnect,      // Disconnect WebSocket
} = useChat();
```

**WebSocket event handling:**
```typescript
useEffect(() => {
  const unsubscribe = ws.onMessage((event: WebSocketEvent) => {
    switch (event.type) {
      case 'ready': /* Session established */
      case 'session_id': /* Session ID update */
      case 'text_delta': /* Streaming content */
      case 'tool_use': /* Tool execution */
      case 'tool_result': /* Tool output */
      case 'ask_user_question': /* Open modal */
      case 'plan_approval': /* Open plan modal */
      case 'error': /* Handle errors */
    }
  });
  return unsubscribe;
}, [ws]);
```

**Tool reference filtering:**
```typescript
// Filters out patterns like: [Tool: Bash (ID: call_...)] Input: {...}
const toolRefPattern = /\[Tool: [^]]+\] Input:\s*(?:\{[^}]*\}|\[.*?\]|"[^"]*")\s*/g;
const filteredText = event.text.replace(toolRefPattern, '');
```

**Session recovery:**
```typescript
case 'error':
  if (event.error?.includes('not found') && event.error?.includes('Session')) {
    // Auto-recover from session not found
    toast.info('Session expired. Starting a new conversation...');
    setSessionId(null);
    queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.SESSIONS] });
    setTimeout(() => ws.connect(agentId, null), 500);
  }
```

### useSessions (`hooks/use-sessions.ts`)

React Query hooks for session CRUD operations.

**Hooks provided:**
```typescript
// Fetch sessions list
const { data: sessions, isLoading, error } = useSessions();

// Create new session
const createSession = useCreateSession();
createSession.mutate(agentId);

// Delete session
const deleteSession = useDeleteSession();
deleteSession.mutate(sessionId);

// Close session
const closeSession = useCloseSession();
closeSession.mutate(sessionId);

// Resume session
const resumeSession = useResumeSession();
resumeSession.mutate({ id, initialMessage: 'Hello' });

// Update session name
const updateSession = useUpdateSession();
updateSession.mutate({ id, name: 'New name' });

// Batch delete sessions
const batchDelete = useBatchDeleteSessions();
batchDelete.mutate([id1, id2, id3]);
```

**Automatic cache invalidation:**
All mutations automatically invalidate the sessions query, triggering a refetch:

```typescript
onSuccess: () => {
  queryClient.invalidateQueries({ queryKey: [QUERY_KEYS.SESSIONS] });
}
```

**Error handling:**
All mutations show toast notifications on error:

```typescript
onError: (error: Error) => {
  toast.error(error.message || 'Failed to delete conversation');
}
```

### useWebSocket (`hooks/use-websocket.ts`)

React hook wrapper around WebSocketManager singleton.

**Returns:**
```typescript
{
  status,           // 'connecting' | 'connected' | 'disconnected'
  error,            // Error | null
  connect,          // (agentId, sessionId) => void
  disconnect,       // () => void
  forceReconnect,   // (agentId, sessionId) => void
  sendMessage,      // (content) => void
  sendAnswer,       // (questionId, answers) => void
  sendPlanApproval, // (planId, approved, feedback) => void
  onMessage,        // (callback) => unsubscribe
  getReadyState,    // () => WebSocket readyState
}
```

**Key behaviors:**
- Creates WebSocketManager singleton on first mount
- Subscribes to status and error callbacks
- Returns memoized callback functions (stable references)
- Automatic cleanup on unmount

**Usage example:**
```typescript
function ChatComponent() {
  const ws = useWebSocket();
  const agentId = useChatStore((s) => s.agentId);

  // Connect to agent
  useEffect(() => {
    if (agentId) ws.connect(agentId, null);
  }, [agentId, ws]);

  // Send message
  const handleSend = () => {
    ws.sendMessage('Hello!');
  };
}
```

### Hook Architecture Diagram

```
Component Layer
    ├── useChat() (orchestration)
    │   └── useWebSocket() (connection)
    │       └── WebSocketManager (singleton)
    │           └── Native WebSocket
    ├── useSessions() (data fetching)
    │   └── apiClient (REST)
    └── Store Hooks (state)
        ├── useChatStore()
        ├── useUIStore()
        ├── useQuestionStore()
        └── usePlanStore()
```

## Theming

This application uses a semantic color token system following Claude.ai's warm terracotta design language, making it easy to customize and integrate with other applications.

### Color Token Hierarchy

| Category | CSS Variables | Tailwind Classes | Purpose |
|----------|--------------|------------------|---------|
| **Brand** | `--primary`, `--primary-foreground` | `text-primary`, `bg-primary` | Primary brand color (Crail terracotta) |
| **Status** | `--status-success`, `--status-warning`, `--status-error`, `--status-info` | `text-status-*`, `bg-status-*-bg` | State indicators |
| **Code** | `--codeblock-bg`, `--codeblock-text`, `--syntax-*` | `bg-codeblock-*`, `text-codeblock-*` | Code block styling |
| **Diff** | `--diff-added-*`, `--diff-removed-*` | `bg-diff-*-bg`, `text-diff-*-fg` | Code diff highlighting |
| **Tool** | `--tool-bash`, `--tool-read`, `--tool-write`, etc. | Via `hsl(var(...))` | Tool-specific accents |

### Customizing the Theme

1. **Override CSS variables** in your own stylesheet:
```css
:root {
  --primary: 200 80% 50%; /* Change to blue */
  --status-success: 160 80% 40%; /* Custom success color */
}

.dark {
  --primary: 200 70% 60%;
  --codeblock-bg: 220 15% 12%;
}
```

2. All colors use **HSL format** (three space-separated numbers) for easy modification
3. Both light (`:root`) and dark (`.dark`) modes are supported

### Integration with Other Apps

To integrate this theme system into another application:

1. **Import the base theme** - Copy `app/globals.css` for all CSS variables
2. **Override brand colors** - Customize `--primary` and related tokens
3. **Adjust semantic tokens** - Modify status, codeblock, and diff colors as needed
4. **Use the Tailwind config** - Import color definitions from `tailwind.config.ts`

### Available Tokens Reference

**Status Colors** (each has DEFAULT, fg, bg variants):
- `status-success` - Success states (green)
- `status-warning` - Warning states (amber)
- `status-error` - Error states (red)
- `status-info` - Informational states (blue)

**Code Block Colors**:
- `codeblock-bg` - Background
- `codeblock-header` - Header background
- `codeblock-text` - Main text
- `codeblock-muted` - Secondary text
- `codeblock-border` - Border color

**Diff Colors**:
- `diff-added-bg`, `diff-added-fg` - Added lines
- `diff-removed-bg`, `diff-removed-fg` - Removed lines

See `app/globals.css` for the complete list of available tokens.