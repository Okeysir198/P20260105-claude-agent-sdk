# Docker Deployment Guide

Deploy the Claude Agent SDK backend as a Docker container. Self-contained image with Claude Code CLI, official plugins, and Playwright browser automation pre-installed.

## Prerequisites

- Docker Engine 20.10+ or Docker Desktop 4.50+
- Docker Compose v2.0+
- API key for your provider (Claude, ZAI, or Proxy)

## Quick Start

### 1. Configure Environment

```bash
cp .env.example .env.docker
nano .env.docker
```

Required variables:

```bash
API_KEY=<strong-random-key>         # REST API auth + JWT secret derivation
CLI_ADMIN_PASSWORD=<password>       # Admin user password
CLI_TESTER_PASSWORD=<password>      # Tester user password
```

Plus one API provider (see [Switching Providers](#switching-providers)).

### 2. Configure Provider

Edit `config.yaml` to set the active provider:

```yaml
provider: zai   # "claude", "zai", "minimax", or "proxy"
```

### 3. Build and Run

```bash
docker compose build
docker compose up -d trung-bot
```

The API will be available at `http://localhost:7003`.

## What's in the Image

The Dockerfile builds a self-contained image:

1. **Python 3.12** + system deps (git, curl, ffmpeg)
2. **Node.js 22** (required by Claude Code CLI and MCP servers)
3. **Claude Code CLI** via native installer (`curl -fsSL https://claude.ai/install.sh | bash`)
4. **Official Anthropic plugins** (playwright, context7, github) installed via `claude plugin marketplace add` + `claude plugin install`
5. **Playwright Chromium** for browser automation
6. **Python deps** from `pyproject.toml` via uv
7. Runs as non-root `appuser` (UID 1000)

### Adding More Plugins

To add more official plugins, append to the plugin install step in `Dockerfile`:

```dockerfile
RUN claude plugin marketplace add anthropics/claude-plugins-official && \
    claude plugin install playwright@claude-plugins-official --scope project && \
    claude plugin install context7@claude-plugins-official --scope project && \
    claude plugin install github@claude-plugins-official --scope project && \
    claude plugin install linear@claude-plugins-official --scope project
```

Available plugins: `playwright`, `context7`, `github`, `gitlab`, `atlassian`, `asana`, `linear`, `notion`, `figma`, `vercel`, `firebase`, `supabase`, `slack`, `sentry`, `commit-commands`, `pr-review-toolkit`, `agent-sdk-dev`, and more. See [official plugin docs](https://code.claude.com/docs/en/plugin-marketplaces).

### Custom Plugins

Place custom plugins in `backend/plugins/<name>/` with `.claude-plugin/plugin.json` + `.mcp.json`, then reference in `agents.yaml`:

```yaml
plugins:
  - {"path": "./plugins/<name>"}
```

## Architecture

### Container Setup

- **Non-root user** (`appuser` UID 1000) for security
- **Host networking** (`network_mode: host`) — container shares host network, no port mapping needed
- **Resource limits**: 1 CPU / 1GB RAM (per Anthropic guidelines)
- **Auto-restart**: `unless-stopped` policy

### Volumes

| Mount | Purpose |
|-------|---------|
| `./data:/app/data` | Session data, history, email credentials |
| `./config.yaml:/app/config.yaml` | Provider switching without rebuild |

No other mounts needed — Claude config, plugins, and browser are all baked into the image.

## Switching Providers

Providers are configured in `config.yaml` (mounted as a volume). No rebuild required.

### Supported Providers

| Provider | `config.yaml` value | Env vars needed |
|----------|-------------------|-----------------|
| Claude (Anthropic) | `claude` | `ANTHROPIC_API_KEY` |
| ZAI | `zai` | `ZAI_API_KEY` + `ZAI_BASE_URL` |
| MiniMax | `minimax` | `MINIMAX_API_KEY` + `MINIMAX_BASE_URL` |
| Proxy (LiteLLM) | `proxy` | `PROXY_BASE_URL` |

### Switch Steps

```bash
# 1. Edit config.yaml to change provider
nano config.yaml

# 2. Ensure the API key is in .env.docker
nano .env.docker

# 3. Restart (no rebuild needed)
docker compose restart trung-bot
```

## Environment Variables

### Required

| Variable | Description |
|----------|-------------|
| `API_KEY` | REST API auth + JWT secret derivation |
| `CLI_ADMIN_PASSWORD` | Admin user password |
| `CLI_TESTER_PASSWORD` | Tester user password |
| Provider API key | At least one (see Switching Providers) |

### Optional

| Variable | Description |
|----------|-------------|
| `CORS_ORIGINS` | Comma-separated allowed origins |
| `BACKEND_PUBLIC_URL` | Public URL for download links |
| `PLATFORM_DEFAULT_AGENT_ID` | Default agent for platform messages |
| `TELEGRAM_BOT_TOKEN` | Telegram bot integration |
| `WHATSAPP_ACCESS_TOKEN` | WhatsApp Cloud API |
| `VLLM_API_KEY` | OCR service API key |
| `EMAIL_GMAIL_CLIENT_ID` | Gmail OAuth client ID |
| `EMAIL_GMAIL_CLIENT_SECRET` | Gmail OAuth client secret |

## Operations

### Build

```bash
docker compose build              # Standard build
docker compose build --no-cache   # Clean rebuild
```

### Run

```bash
docker compose up -d trung-bot    # Start API server (port 7003)
docker compose down               # Stop
docker compose restart trung-bot  # Restart
```

### Logs

```bash
docker compose logs -f trung-bot        # Follow logs
docker compose logs --tail=50 trung-bot # Last 50 lines
```

### Health Check

```bash
curl http://localhost:7003/health
docker compose ps                       # Shows health status
```

### Shell Access

```bash
docker compose exec trung-bot bash
```

## Troubleshooting

### Container Won't Start

```bash
docker compose logs trung-bot     # Check error logs
docker compose config             # Verify compose config
```

### Permission Issues

The container runs as `appuser` (UID 1000). Fix volume permissions:

```bash
sudo chown -R 1000:1000 ./data
```

### Agent Not Responding

Check that:
1. Provider API key is set in `.env.docker`
2. `config.yaml` has the correct `provider` value
3. The API endpoint is reachable from the container

```bash
# Test provider API connectivity
docker compose exec trung-bot python3 -c "
from agent.core.config import ACTIVE_PROVIDER
print(f'Provider: {ACTIVE_PROVIDER}')
import os
print(f'AUTH_TOKEN set: {bool(os.environ.get(\"ANTHROPIC_AUTH_TOKEN\"))}')
print(f'BASE_URL: {os.environ.get(\"ANTHROPIC_BASE_URL\", \"default\")}')
"
```

### Updating

```bash
git pull
docker compose build
docker compose up -d trung-bot
```

## Security

- Runs as non-root user
- Resource-limited (1 CPU / 1GB RAM)
- Only `./data` and `./config.yaml` mounted from host
- API key authentication on all endpoints
- JWT-based user authentication
