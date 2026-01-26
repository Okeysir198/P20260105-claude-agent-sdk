# Claude Agent SDK Chat

Interactive chat application with multi-agent support, built on the Claude Agent SDK. Provides a web interface and CLI with WebSocket/SSE streaming.

## Features

- **Multi-Agent Support** - Switch between specialized agents (General, Code Reviewer, Doc Writer, Researcher, Sandbox)
- **WebSocket Streaming** - Real-time, low-latency chat with persistent connections
- **Session Management** - Save, resume, and manage conversation history
- **Interactive Questions** - Agent can ask clarifying questions via modal UI (AskUserQuestion)
- **Resizable Sidebar** - Adjustable session panel with persistent width
- **Dark Mode** - Custom dark theme with system preference detection
- **API Key Authentication** - Secure header-based auth with timing-safe comparison

## Quick Start

### Backend

```bash
cd backend
uv sync && source .venv/bin/activate
cp .env.example .env   # Add ANTHROPIC_API_KEY and API_KEY
python main.py serve --port 7001
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local   # Set NEXT_PUBLIC_API_URL and NEXT_PUBLIC_API_KEY
npm run dev   # Starts on port 7002
```

### Verify

```bash
# Health check (no auth)
curl http://localhost:7001/health

# List agents (with auth)
curl -H "X-API-Key: your-api-key" http://localhost:7001/api/v1/config/agents
```

## Architecture

```
backend/                         # FastAPI server (port 7001)
├── agents.yaml                 # Top-level agent definitions
├── subagents.yaml              # Delegation subagent definitions
├── agent/
│   └── core/                   # Agent utilities
├── api/
│   ├── main.py                 # FastAPI app factory
│   ├── constants.py            # Event types, close codes
│   ├── dependencies.py         # Dependency injection
│   ├── routers/                # API routes
│   ├── services/               # Business logic
│   └── models/                 # Pydantic models
├── cli/
│   ├── main.py                 # Click CLI entry point
│   └── commands/               # chat, serve, list commands
└── data/
    ├── sessions.json           # Session metadata
    └── history/                # JSONL per session

frontend/                        # Next.js 16 (port 7002)
├── app/
│   ├── page.tsx                # Main chat page
│   ├── layout.tsx              # Root layout with providers
│   └── globals.css             # Global styles + dark mode
├── components/
│   ├── agent/                  # Agent selection UI
│   ├── chat/                   # Chat UI components
│   ├── session/                # Session management
│   ├── ui/                     # shadcn/ui components
│   └── providers/              # React Query + theme providers
├── hooks/                      # Custom hooks (useChat, useAgents, etc.)
└── lib/
    ├── api-client.ts           # HTTP client with auth
    └── constants.ts            # API URLs
```

## Configuration

### Backend (.env)

```bash
ANTHROPIC_API_KEY=sk-ant-...     # Required for Claude provider
# API authentication (generate with: openssl rand -hex 32)
API_KEY=your-secure-key
CORS_ORIGINS=http://localhost:7002,https://your-domain.com
```

### Frontend (.env.local)

```bash
NEXT_PUBLIC_API_URL=https://claude-agent-sdk-fastapi-sg4.tt-ai.org/api/v1
NEXT_PUBLIC_API_KEY=your-secure-key
```

**Important:** The frontend is configured to always connect to the production backend. Localhost connections are not supported.

## Available Agents

| Agent ID | Name | Description | Model |
|----------|------|-------------|-------|
| `general-agent-a1b2c3d4` | General Assistant | General-purpose coding assistant (default) | sonnet |
| `code-reviewer-x9y8z7w6` | Code Reviewer | Code reviews and security analysis | sonnet |
| `doc-writer-m5n6o7p8` | Documentation Writer | Documentation generation | sonnet |
| `research-agent-q1r2s3t4` | Code Researcher | Codebase exploration (read-only) | haiku |
| `sandbox-agent-s4ndb0x1` | Sandbox Agent | Restricted file permissions for testing | sonnet |

## Subagents (Delegation)

Available for task delegation via Task tool:
- **researcher** - Code exploration and analysis
- **reviewer** - Code review and quality checks
- **file_assistant** - File operations assistance

## Documentation

- [Backend README](backend/README.md) - API details, WebSocket protocol, endpoints
- [Frontend README](frontend/README.md) - UI components, hooks, tech stack
- [CLAUDE.md](CLAUDE.md) - Development guide for Claude Code

## License

MIT
