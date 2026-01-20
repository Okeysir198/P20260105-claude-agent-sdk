# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Claude Agent SDK CLI** - A production-ready interactive chat application that wraps the Claude Agent SDK with multi-agent support, skills system, and both CLI and web interfaces. It provides a flexible platform for building AI-powered coding assistants with support for multiple LLM providers (Claude, Zai, Minimax).

## Architecture

### Backend (Python + FastAPI)

```
backend/
├── agent/              # Core agent system
│   ├── agents.yaml     # Top-level agent definitions (general, reviewer, doc-writer, researcher)
│   ├── subagents.yaml  # Delegation subagents (researcher, reviewer, file_assistant)
│   ├── core/           # Session management, agent options, storage
│   ├── discovery/      # Skills and MCP server discovery
│   └── display/        # Console output formatting
├── api/                # FastAPI server (port 7001)
│   ├── main.py         # FastAPI app factory with global exception handlers
│   ├── routers/        # REST endpoints (sessions, conversations, config, health)
│   ├── services/       # Session manager, message utilities
│   ├── models/         # Pydantic request/response models
│   ├── core/           # Error classes (APIError, SessionNotFoundError)
│   └── dependencies.py # Dependency injection (SessionManagerDep)
├── cli/                # Click-based CLI
│   ├── main.py         # CLI entry point
│   ├── clients/        # API and Direct client modes
│   └── commands/       # chat, serve, skills, agents, sessions commands
├── tests/              # Pytest test suite
└── data/               # Runtime data (sessions.json persistence)
```

### Frontend (Next.js + React)

```
frontend/
├── app/                # Next.js 16 App Router
│   └── api/            # API route handlers (proxy to backend)
├── components/         # React components with Tailwind CSS
│   └── chat/           # Chat UI components (expandable-panel, tool messages)
├── lib/                # Utilities (api-proxy, animations, utils)
├── hooks/              # Custom React hooks (use-sse-stream, use-claude-chat)
├── types/              # TypeScript type definitions
└── package.json        # Runs on port 7002
```

### Key Concepts

**Agent Types vs Subagents:**
- **Top-level agents** (`agents.yaml`): Selected via `agent_id` when creating a session (e.g., `general-agent-a1b2c3d4`, `code-reviewer-x9y8z7w6`)
- **Subagents** (`subagents.yaml`): Used for task delegation within conversations via the Task tool

**Agent ID Format:** `{type}-{unique_suffix}` (e.g., `general-agent-a1b2c3d4`)

**Session Architecture:**
- In-memory session cache (`SessionManager._sessions`) for fast access
- Persistent storage (`SessionStorage`) backs session metadata to `data/sessions.json`
- Sessions can be resumed via `resume_session_id` parameter
- `ConversationSession` wraps the Claude Agent SDK client
- Global exception handlers in `main.py` for `SessionNotFoundError` and `APIError`
- `SessionManagerDep` type alias for dependency injection in routers

**Skills System:**
- Discovered from `.claude/skills/` directory
- Each agent specifies `skills:` list in YAML config
- Example skills: `code-analyzer`, `doc-generator`, `issue-tracker`

## Common Commands

### Backend Development

```bash
cd backend

# Install dependencies (using uv)
uv sync

# Set up environment
cp .env.example .env
# Edit .env to add ANTHROPIC_API_KEY or other provider keys

# Run API server (port 7001)
python main.py serve --port 7001

# Interactive CLI
python main.py

# List resources
python main.py skills
python main.py agents
python main.py subagents
python main.py sessions
```

### Docker (Recommended)

```bash
cd backend

# Build and start API server
make build && make up

# Start interactive CLI session
make up-interactive

# Run basic tests
make test

# View logs
make logs

# List resources (Docker)
make skills
make agents
make sessions
```

### Running Tests

```bash
cd backend

# Run all tests
pytest

# Run specific test file
pytest tests/test_session_manager.py

# Run with verbose output
pytest -v

# Run async tests
pytest tests/test_api_endpoints_comprehensive.py -v
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Development server (port 7002)
npm run dev

# Build for production
npm run build

# Start production server
npm start

# Lint code
npm run lint
```

## Configuration

### Provider Selection

Edit `backend/config.yaml` to switch between providers:
```yaml
provider: zai  # Options: claude, zai, minimax
```

Each provider requires corresponding environment variables in `.env`:
- `claude`: `ANTHROPIC_API_KEY`
- `zai`: `ZAI_API_KEY`, `ZAI_BASE_URL`
- `minimax`: `MINIMAX_API_KEY`, `MINIMAX_BASE_URL`

### Docker Environment

Set `API_PORT` in `.env` or use default (7001):
```bash
export API_PORT=7001
```

## API Endpoints

The FastAPI server provides:

- `GET /health` - Health check
- `POST /api/v1/sessions` - Create new session (201 Created)
- `GET /api/v1/sessions` - List all sessions
- `POST /api/v1/sessions/{id}/close` - Close session
- `DELETE /api/v1/sessions/{id}` - Delete session
- `POST /api/v1/conversations/{session_id}/stream` - SSE streaming response
- `POST /api/v1/conversations/{session_id}/interrupt` - Interrupt conversation
- `GET /api/v1/config/agents` - List available agents

## Adding New Agents

1. Edit `backend/agent/agents.yaml` for top-level agents
2. Edit `backend/agent/subagents.yaml` for delegation subagents
3. Follow agent ID format: `{type}-{unique_suffix}`
4. Specify `tools:`, `skills:`, `subagents:`, and `model:`

Example:
```yaml
my-new-agent-x1y2z3w4:
  name: "My New Agent"
  type: "custom"
  description: "Description of what this agent does"
  system_prompt: |
    Role-specific instructions (appended to default claude_code prompt)
  tools:
    - Skill
    - Task
    - Read
    - Write
    - Bash
  subagents:
    - researcher
    - reviewer
  skills:
    - code-analyzer
  model: sonnet  # Options: sonnet, haiku, opus
```

## Session Persistence

- Sessions stored in `backend/data/sessions.json`
- Session metadata includes: `session_id`, `created_at`, `turn_count`, `first_message`, `user_id`
- Resume sessions by passing `resume_session_id` to `create_session()`
- Use `python main.py sessions` to list all sessions

## Multi-Agent Delegation

Agents delegate to subagents using the Task tool:
```python
Task(
    subagent_type="researcher",
    prompt="Find all files related to authentication",
    description="Research authentication code"
)
```

Available subagent types:
- `researcher` - Code exploration and analysis
- `reviewer` - Code review and quality checks
- `file_assistant` - File navigation and search

## Testing Patterns

Tests use pytest with async support:
- `tests/test_session_manager.py` - Session lifecycle tests
- `tests/test_api_endpoints_comprehensive.py` - API endpoint tests
- `tests/test_conversations_sse.py` - SSE streaming tests
- `tests/test_claude_agent_sdk_multi_turn.py` - Multi-turn conversation tests

Use `pytest-asyncio` for async tests:
```python
@pytest.mark.asyncio
async def test_my_async_function():
    result = await my_async_function()
    assert result is not None
```

## Resource Limits

Docker containers enforce Anthropic's official requirements:
- CPU: 1 core (limit), 0.5 core (reservation)
- Memory: 1GiB (limit), 512MiB (reservation)

## Frontend-Backend Integration

- Frontend (port 7002) proxies API requests to backend (port 7001)
- SSE streaming endpoint: `POST /api/v1/conversations/{session_id}/stream`
- Shared proxy utility: `frontend/lib/api-proxy.ts` (`proxyToBackend()`)
- Shared UI component: `frontend/components/chat/expandable-panel.tsx`
