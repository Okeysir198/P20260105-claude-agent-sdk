# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Claude Agent SDK CLI - An interactive chat application that wraps the Claude Agent SDK with Skills and Subagents support. Supports two operational modes:
- **Direct mode**: Uses Python SDK directly (default)
- **API mode**: Connects via HTTP/SSE to a FastAPI server

## Commands

```bash
# Run CLI (interactive chat - default)
python main.py
python main.py --mode direct          # Explicit direct mode
python main.py --mode api             # API mode (requires running server)

# Start API server
python main.py serve                  # Default: 0.0.0.0:19830
python main.py serve --port 8080      # Custom port
python main.py serve --reload         # Auto-reload for development

# List resources
python main.py skills                 # List available skills
python main.py agents                 # List subagents
python main.py sessions               # List conversation history

# Resume session
python main.py --session-id <id>      # Resume existing session
```

## Architecture

```
├── agent/                    # Core business logic
│   ├── core/
│   │   ├── options.py       # ClaudeAgentOptions builder with skills/subagents
│   │   ├── session.py       # ConversationSession - main interactive loop
│   │   ├── storage.py       # Unified session storage (data/sessions.json)
│   │   └── agents.py        # Subagent definitions (researcher, reviewer, file_assistant)
│   ├── discovery/
│   │   ├── skills.py        # Discovers skills from .claude/skills/
│   │   └── mcp.py           # Loads MCP servers from .mcp.json
│   └── display/             # Rich console output utilities
│
├── api/                      # FastAPI HTTP/SSE server
│   ├── main.py              # FastAPI app with lifespan management
│   ├── routers/             # Endpoints: /sessions, /conversations, /config
│   └── services/
│       ├── session_manager.py     # In-memory session state + persistence
│       └── conversation_service.py # ClaudeSDKClient wrapper for streaming
│
├── cli/                      # Click-based CLI
│   ├── main.py              # CLI entry point with click commands
│   ├── clients/
│   │   ├── direct.py        # DirectClient - wraps SDK directly
│   │   └── api.py           # APIClient - HTTP/SSE client
│   └── commands/            # chat, serve, list commands
│
├── .claude/skills/           # Custom skills (code-analyzer, doc-generator, issue-tracker)
├── config.yaml              # Provider configuration (claude, zai, minimax)
└── data/sessions.json       # Persisted session history
```

## Key Data Flows

**Direct Mode**: `cli/main.py` → `cli/clients/direct.py` → `claude_agent_sdk.ClaudeSDKClient`

**API Mode**: `cli/main.py` → `cli/clients/api.py` → `api/routers/*` → `api/services/conversation_service.py` → `ClaudeSDKClient`

## Configuration

- **Provider switching**: Edit `config.yaml` to change between claude/zai/minimax providers
- **Skills**: Add new skills in `.claude/skills/<name>/SKILL.md`
- **Subagents**: Modify `agent/core/agents.py` to add/change subagent definitions
- **MCP servers**: Configure in `.mcp.json` (project-level only, excludes user/global)

## API Endpoints (when running server)

- `GET /health` - Health check
- `GET /api/v1/sessions` - List sessions
- `POST /api/v1/sessions/{id}/resume` - Resume session
- `POST /api/v1/conversations` - Create conversation (SSE stream)
- `POST /api/v1/conversations/{id}/stream` - Send message (SSE stream)
- `POST /api/v1/conversations/{id}/interrupt` - Interrupt task
- `GET /api/v1/config/skills` - List skills
- `GET /api/v1/config/agents` - List agents

## In Planning Mode

Always plan tasks to launch multiple subagents in parallel for higher code quality and efficiency during implementation.
