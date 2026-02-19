# Claude Agent SDK - Frontend

Next.js 16 chat interface with user authentication, WebSocket streaming, and per-user sessions.

## Quick Start

```bash
npm install
cp .env.example .env.local   # Configure API_KEY and BACKEND_API_URL
npm run dev                   # http://localhost:7002
```

## Features

- User login with route protection
- Real-time WebSocket streaming
- Multi-agent selection
- Session sidebar with search (name + full-text content search)
- Kanban task board panel (synced from agent tool calls)
- Admin settings page (Chat Platform whitelist, user management)
- Email integration management (Gmail OAuth, universal IMAP)
- File upload and preview (images, PDFs, Excel, code)
- Plan approval and AskUserQuestion modals
- Dark/light mode

## Architecture

```
app/
├── (auth)/
│   ├── login/             # Login page (public)
│   ├── profile/           # Email integration management
│   └── admin/             # Admin settings (Chat Platform whitelist, users)
├── s/[sessionId]/         # Session detail page
├── api/
│   ├── auth/              # Login, logout, session, token, refresh, OAuth callback
│   ├── files/             # File upload proxy
│   └── proxy/             # REST API proxy (adds API key server-side)
├── page.tsx               # Main chat (protected)
└── layout.tsx             # Root layout with providers

components/
├── agent/                 # Agent selector grid + switcher
├── chat/                  # Chat UI (messages, input, tools/, connection state)
├── email/                 # Email connection buttons + status badge
├── files/                 # File upload zone, preview modal, file cards
├── kanban/                # Task board panel (board, cards, columns, activity)
├── session/               # Sidebar with session list + user profile
├── features/auth/         # Login form, logout button
├── providers/             # Auth, Query, Theme providers
└── ui/                    # Radix UI primitives

hooks/                     # React hooks (chat, sessions, agents, files, search)
lib/                       # Stores (Zustand), WebSocket manager, auth, utilities
types/                     # TypeScript type definitions
proxy.ts                   # Route protection (Next.js 16 proxy, renamed from middleware.ts)
```

## Environment Variables

```bash
# Server-only (never exposed to browser)
API_KEY=your-api-key
BACKEND_API_URL=https://claude-agent-sdk-api.leanwise.ai/api/v1

# Public (browser-accessible, baked into client bundle at build time)
NEXT_PUBLIC_WS_URL=wss://claude-agent-sdk-api.leanwise.ai/api/v1/ws/chat
NEXT_PUBLIC_APP_URL=https://claude-agent-sdk-chat.leanwise.ai
```

## Scripts

```bash
npm run dev          # Development server with Turbopack (port 7002)
npm run build        # Production build
npm run start        # Production server (port 7002)
npm run lint         # ESLint
npx tsc --noEmit     # Type check

# Cloudflare Workers deployment
npm run cf:build     # Build for Cloudflare Workers (via OpenNext)
npm run cf:preview   # Build + local preview with Wrangler
npm run cf:deploy    # Build + deploy to Cloudflare Workers
```

## Deployment

### Local (via Cloudflare Tunnel)

The dev server runs locally on port 7002, exposed via Cloudflare Tunnel:
- URL: `https://claude-agent-sdk-chat.leanwise.ai`

### Cloudflare Workers

Frontend is deployed to Cloudflare Workers using the [OpenNext adapter](https://opennext.js.org/cloudflare):
- URL: `https://claude-agent-sdk-chat.nthanhtrung198.workers.dev`
- Auto-deploy: Push to `cf-deployment` branch triggers [GitHub Actions workflow](../.github/workflows/deploy-cloudflare.yml)
- Manual: `npm run cf:deploy`

**Required GitHub Secrets** (for CI auto-deploy):

| Secret | Description |
|--------|-------------|
| `CLOUDFLARE_API_TOKEN` | Cloudflare API token ("Edit Workers" template) |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare account ID |
| `API_KEY` | Same as backend API_KEY |
| `BACKEND_API_URL` | Backend API base URL |
| `NEXT_PUBLIC_WS_URL` | WebSocket URL (baked at build time) |
| `NEXT_PUBLIC_APP_URL` | Frontend public URL (baked at build time) |

**Note:** `NEXT_PUBLIC_*` vars are baked into the client bundle at build time, not read at runtime.

### Cloudflare Build Workaround

OpenNext doesn't support Next.js 16's `proxy.ts` yet ([#962](https://github.com/opennextjs/opennextjs-cloudflare/issues/962)). The `cf:build` script automatically renames `proxy.ts` → `middleware.ts` during build and restores it after.

## Authentication Flow

1. User visits `/` → `proxy.ts` redirects to `/login`
2. Login form → `/api/auth/login` → backend validates → HttpOnly session cookie set
3. Protected routes: `proxy.ts` checks session cookie
4. WebSocket: `/api/auth/token` creates JWT → WebSocket connects with `?token={jwt}`

## API Routes

| Route | Purpose |
|-------|---------|
| `/api/auth/login` | Forward login to backend |
| `/api/auth/logout` | Clear session cookie |
| `/api/auth/session` | Get current user from cookie |
| `/api/auth/token` | Create user_identity JWT for WebSocket |
| `/api/auth/refresh` | Refresh expired tokens |
| `/api/files/upload` | File upload proxy |
| `/api/proxy/*` | Forward REST calls with API key |

## State Management

Uses **Zustand** stores in `lib/store/`:

| Store | Purpose |
|-------|---------|
| `chat-store` | Messages, session/agent ID, streaming state |
| `ui-store` | Sidebar, theme, mobile detection |
| `kanban-store` | Tasks, tool calls, subagents |
| `question-store` | AskUserQuestion modal |
| `plan-store` | Plan approval modal |
| `file-store` | File management |
| `file-preview-store` | File preview modal |

## Edge Runtime Compatibility

All server-side code uses Web Crypto API instead of Node.js `crypto` module for Cloudflare Workers compatibility:
- `lib/jwt-utils.ts` — `crypto.subtle.importKey()`, `crypto.subtle.sign()`, `crypto.subtle.digest()`
- `lib/session.ts` — Async `deriveJwtSecret()` calls
- `app/api/proxy/[...path]/route.ts` — `Uint8Array` instead of `Buffer`
