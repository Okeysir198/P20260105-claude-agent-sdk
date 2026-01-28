# Claude Agent SDK Chat - Frontend

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