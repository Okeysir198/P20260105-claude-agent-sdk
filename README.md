# Claude Agent SDK CLI

An interactive chat application that wraps the Claude Agent SDK with Skills and Subagents support. Supports multiple LLM providers and two operational modes (Direct SDK and API Server).

## Features

- **Dual Operation Modes**: Direct SDK mode or API server mode
- **Docker Support**: Production-ready Docker deployment with easy provider switching
- **Skills System**: Extensible custom skills for code analysis, documentation generation, and issue tracking
- **Subagents**: Built-in agents (researcher, reviewer, file_assistant) for specialized tasks
- **Multi-Provider Support**: Claude (Anthropic), ZAI, and MiniMax providers
- **Session Management**: Persistent conversation history with resume capability
- **Streaming Responses**: Real-time SSE streaming for both modes
- **Provider Switching**: Switch providers instantly without rebuilding

## Quick Start

### Option 1: Docker (Recommended - Production Ready)

```bash
# Configure environment
cp .env.example .env
nano .env  # Add your API key

# Build and start
make build && make up

# Or use Docker Compose directly
docker compose build
docker compose up -d claude-api

# Test the API
curl http://localhost:19830/health
```

**See [DOCKER.md](DOCKER.md) for complete Docker deployment guide, including:**
- Provider switching without rebuild
- Cloud deployment (AWS, GCP, Azure)
- Production configuration
- Troubleshooting and monitoring

### Option 2: Local Development

```bash
# Clone the repository
git clone <repository-url>
cd P20260105-claude-agent-sdk

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Add your API key

# Run interactive chat
python main.py
```

## Configuration

### Environment Variables

Set your API key for the provider you want to use:

```bash
# For Claude (Anthropic) - Recommended
ANTHROPIC_API_KEY=sk-ant-api03-...

# For Zai
ZAI_API_KEY=your_zai_key
ZAI_BASE_URL=https://api.zai-provider.com

# For MiniMax
MINIMAX_API_KEY=your_minimax_key
MINIMAX_BASE_URL=https://api.minimax-provider.com
```

### Provider Configuration

Edit `config.yaml` to switch between providers:

```yaml
provider: claude  # Options: claude, zai, minimax
```

**Docker users**: Switch providers easily without rebuilding:
```bash
./switch-provider.sh zai      # Switch to Zai
./switch-provider.sh claude   # Switch to Claude
./switch-provider.sh minimax  # Switch to MiniMax
```

## Usage

### Interactive Chat (Direct Mode - Default)

```bash
# Local development
python main.py
python main.py --mode direct

# Docker
make up-interactive
# OR
docker compose run --rm claude-interactive
```

### API Server Mode

```bash
# Local development
python main.py serve                  # Default: 0.0.0.0:19830
python main.py serve --port 8080      # Custom port

# Docker
make up
# OR
docker compose up -d claude-api

# Check logs
docker compose logs -f claude-api
```

The API will be available at `http://localhost:19830`

### List Resources

```bash
# Local
python main.py skills                 # List available skills
python main.py agents                 # List subagents
python main.py sessions               # List conversation history

# Docker
make skills
make agents
make sessions
```

### Resume Session

```bash
# Local
python main.py --session-id <id>

# Docker
docker compose run --rm claude-interactive python main.py --session-id <id>
```

## API Endpoints

When running in server mode, the following endpoints are available:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/v1/sessions` | GET | List sessions |
| `/api/v1/sessions/{id}/resume` | POST | Resume session |
| `/api/v1/conversations` | POST | Create conversation (SSE stream) |
| `/api/v1/conversations/{id}/stream` | POST | Send message (SSE stream) |
| `/api/v1/conversations/{id}/interrupt` | POST | Interrupt task |
| `/api/v1/config/skills` | GET | List skills |
| `/api/v1/config/agents` | GET | List agents |

### Example API Usage

```bash
# Create a new conversation
curl -N -X POST http://localhost:19830/api/v1/conversations \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello! Can you help me?"}'

# Send a follow-up message
curl -N -X POST http://localhost:19830/api/v1/conversations/{session_id}/stream \
  -H "Content-Type: application/json" \
  -d '{"content": "What is 2 + 2?"}'

# List sessions
curl http://localhost:19830/api/v1/sessions
```

## Custom Skills

Add custom skills in `.claude/skills/<name>/SKILL.md`. The application includes:

- **code-analyzer**: Analyze code for patterns and issues
- **doc-generator**: Generate documentation for code
- **issue-tracker**: Track and categorize code issues

Skills are automatically invoked based on context. For example:
- "Analyze this file for issues" → invokes `code-analyzer`
- "Generate documentation for this module" → invokes `doc-generator`

## Architecture

```
├── agent/                    # Core business logic
│   ├── core/
│   │   ├── options.py       # ClaudeAgentOptions builder
│   │   ├── session.py       # ConversationSession - main loop
│   │   ├── storage.py       # Session storage (data/sessions.json)
│   │   ├── config.py        # Provider configuration loader
│   │   └── agents.py        # Subagent definitions
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
├── .claude/skills/           # Custom skills
├── config.yaml              # Provider configuration
├── Dockerfile               # Docker image definition
├── docker-compose.yml       # Docker orchestration
├── Makefile                 # Convenient management commands
└── data/sessions.json       # Persisted session history
```

## Data Flows

**Direct Mode**: `cli/main.py` → `cli/clients/direct.py` → `claude_agent_sdk.ClaudeSDKClient`

**API Mode**: `cli/main.py` → `cli/clients/api.py` → `api/routers/*` → `api/services/conversation_service.py` → `ClaudeSDKClient`

## Docker Commands

```bash
# Build and start
make build && make up

# View logs
make logs

# Interactive mode
make up-interactive

# Switch providers
./switch-provider.sh zai

# Stop services
make down

# Clean up
make clean
```

## Requirements

- Python 3.10+
- Docker Engine 20.10+ (for Docker deployment)
- Docker Compose v2.0+ (for Docker deployment)

## Project Status

- ✅ **Core Features**: All features implemented and tested
- ✅ **Docker Deployment**: Production-ready with multi-provider support
- ✅ **Provider Switching**: Easy switching without rebuild (MiniMax → Zai tested)
- ✅ **API Server**: FastAPI with SSE streaming working
- ✅ **Session Management**: 20+ sessions persisted
- ✅ **Documentation**: Comprehensive Docker guide included

## Performance Notes

| Provider | Response Time | Status |
|----------|---------------|--------|
| **Claude (Anthropic)** | ~2-3s | ⭐ Recommended |
| **Zai** | ~5s | ✅ Good alternative |
| **MiniMax** | >60s | ⚠️ Not recommended for production |

## License

MIT

## Documentation

- [DOCKER.md](DOCKER.md) - Complete Docker deployment guide
- [CLAUDE.md](CLAUDE.md) - Claude Code instructions
- [API Documentation](#api-endpoints) - API reference

## Support

For Docker deployment issues:
1. Check [DOCKER.md](DOCKER.md) troubleshooting section
2. Verify logs: `docker compose logs -f claude-api`
3. Check health: `curl http://localhost:19830/health`
