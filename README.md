# Claude Agent SDK Chat

Interactive chat application with multi-agent support and user authentication, built on the Claude Agent SDK.

## Overview

TT-Bot is a full-stack chat application that provides:

- **User Authentication** - SQLite-based login with per-user data isolation
- **Multi-Agent Support** - Switch between specialized AI agents
- **WebSocket Streaming** - Real-time chat with persistent connections
- **Session Management** - Save, resume, and manage conversation history
- **Interactive Questions** - AskUserQuestion modal for clarification
- **Dark Mode** - System preference detection with manual toggle

## Quick Start

### Backend (FastAPI)

```bash
cd backend
uv sync && source .venv/bin/activate
cp .env.example .env   # Configure API keys and CLI_PASSWORD
python main.py serve --port 7001
```

### Frontend (Next.js)

```bash
cd frontend
npm install
cp .env.example .env.local   # Configure API_KEY and BACKEND_API_URL
npm run dev   # Starts on port 7002
```

### Login

Open http://localhost:7002 and log in with the credentials below.

## Default Login Credentials

| Username | Password | Role |
|----------|----------|------|
| admin | (value of `CLI_ADMIN_PASSWORD` from backend .env) | admin |
| tester | (value of `CLI_TESTER_PASSWORD` from backend .env) | user |

## Where to Start?

This README provides a quick overview. For detailed documentation, see:

### [CLAUDE.md](./CLAUDE.md)
**Development guide for Claude Code**

- Project architecture diagram
- Authentication flow details
- Per-user data isolation structure
- Commands reference
- Agent configuration guide
- Deployment URLs

### [backend/README.md](./backend/README.md)
**API reference and backend architecture**

- Quick start guide
- Two-layer authentication system (API Key + User Login)
- Complete API endpoints reference
- WebSocket protocol specification
- CLI commands
- Environment variables reference
- Data structure
- Testing and Docker setup

### [frontend/README.md](./frontend/README.md)
**Frontend architecture and UI components**

- Quick start guide
- Authentication flow
- Architecture overview
- Environment variables (server-only vs public)
- Proxy routes reference
- Key components description
- Semantic color token system for theming
- Theme customization guide

## Production URLs

- **Backend**: https://claude-agent-sdk-fastapi-sg4.tt-ai.org
- **Frontend**: https://claude-agent-sdk-chat.tt-ai.org

## License

MIT
