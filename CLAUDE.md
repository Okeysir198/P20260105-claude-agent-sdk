# CLAUDE.md

Guidance for Claude Code when working with this repository.

## Project Overview

**Claude Agent SDK CLI** - Interactive chat application wrapping the Claude Agent SDK with multi-agent support. Provides CLI and web interfaces with SSE streaming.

## Architecture

```
backend/
├── agent/
│   ├── agents.yaml          # Top-level agents (general, reviewer, doc-writer, researcher)
│   ├── subagents.yaml       # Delegation subagents
│   └── core/
│       ├── session.py       # ConversationSession (is_connected property)
│       ├── agent_options.py # create_enhanced_options(agent_id, resume_session_id)
│       └── storage.py       # SessionStorage + HistoryStorage (data/sessions.json, data/history/)
├── api/                     # FastAPI server (port 7001)
│   ├── main.py              # App factory with global exception handlers
│   ├── routers/
│   │   ├── conversations.py # SSE streaming with agent_id support
│   │   ├── sessions.py      # Session CRUD + history
│   │   └── configuration.py # List agents
│   ├── services/
│   │   └── session_manager.py # get_or_create_conversation_session(session_id, agent_id)
│   └── models/              # Pydantic request/response models
├── cli/                     # Click CLI
├── tests/                   # test_claude_agent_sdk*.py, test_api_agent_selection.py
└── data/
    ├── sessions.json        # Session metadata
    └── history/             # Message history (JSONL per session)

frontend/                    # Next.js (port 7002)
├── app/api/                 # Proxy routes to backend
├── hooks/                   # use-sse-stream, use-claude-chat, use-sessions
└── lib/api-proxy.ts         # Shared proxyToBackend() utility
```

## Key Concepts

**Agent Selection:**
- Agents defined in `agents.yaml` with unique IDs: `{type}-{suffix}` (e.g., `code-reviewer-x9y8z7w6`)
- System prompt is APPENDED to default `claude_code` preset (not replaced)
- Select via `agent_id` parameter in `/api/v1/conversations`

**Session Flow:**
```
POST /api/v1/conversations {content, agent_id}
  → SessionManager.get_or_create_conversation_session(session_id, agent_id)
  → create_enhanced_options(agent_id=agent_id)
  → Loads agent config from agents.yaml
  → SSE streaming response
```

**Message History:**
- Stored locally in `data/history/{session_id}.jsonl`
- Roles: `user`, `assistant`, `tool_use`, `tool_result`
- Retrieved via `GET /api/v1/sessions/{id}/history`

## Commands

```bash
# Development
cd backend
uv sync && source .venv/bin/activate
cp .env.example .env  # Add ANTHROPIC_API_KEY
python main.py serve --port 7001

# CLI
python main.py agents    # List agents
python main.py sessions  # List sessions

# Tests
python tests/test_api_agent_selection.py  # API test (requires server)

# Frontend
cd frontend && npm install && npm run dev

# Docker (production)
cd backend && make build && make up
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/api/v1/conversations` | Create conversation with `agent_id` (SSE) |
| POST | `/api/v1/conversations/{id}/stream` | Follow-up message (SSE) |
| POST | `/api/v1/conversations/{id}/interrupt` | Interrupt task |
| POST | `/api/v1/sessions` | Create session |
| GET | `/api/v1/sessions` | List sessions |
| GET | `/api/v1/sessions/{id}/history` | Get message history |
| POST | `/api/v1/sessions/{id}/resume` | Resume session |
| DELETE | `/api/v1/sessions/{id}` | Delete session + history |
| GET | `/api/v1/config/agents` | List available agents |

## Adding Agents

Edit `backend/agent/agents.yaml`:

```yaml
my-agent-abc123:
  name: "My Agent"
  type: "custom"
  description: "What this agent does"
  system_prompt: |
    Role-specific instructions (appended to claude_code preset)
  tools: [Skill, Task, Read, Write, Bash, Grep, Glob]
  subagents: [researcher, reviewer]
  model: sonnet  # haiku, sonnet, opus
  read_only: false
```

## Configuration

Provider in `backend/config.yaml`:
```yaml
provider: claude  # claude, zai, minimax
```

Environment variables in `.env`:
- `ANTHROPIC_API_KEY` (for claude)
- `ZAI_API_KEY`, `ZAI_BASE_URL` (for zai)
