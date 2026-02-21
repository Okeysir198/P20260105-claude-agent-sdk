# Docker Deployment Guide

This guide explains how to deploy the Claude Agent SDK CLI using Docker, following the official Anthropic guidelines for hosting the Agent SDK.

## Prerequisites

- Docker Engine 20.10+ or Docker Desktop 4.50+
- Docker Compose v2.0+
- API key for your provider (Claude, Zai, or Proxy)

## Quick Start

### 1. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your API keys
nano .env
```

Add your provider's API key:

```bash
# For Claude (Anthropic)
ANTHROPIC_API_KEY=sk-ant-api03-...

# OR for Zai
ZAI_API_KEY=your_zai_key
ZAI_BASE_URL=https://api.zai-provider.com

# OR for Proxy (LiteLLM or similar)
PROXY_BASE_URL=http://localhost:4000
```

### 2. Build and Run

**Option A: Using Make (Recommended)**

```bash
# Build and start API server
make build && make up

# Start interactive chat session
make up-interactive

# List available commands
make help
```

**Option B: Using Docker Compose directly**

```bash
# Build the image
docker compose build

# Start API server
docker compose up -d claude-api

# View logs
docker compose logs -f claude-api
```

## Usage Examples

### API Server Mode

Start the FastAPI server:

```bash
make up
# OR
docker compose up -d claude-api
```

The API will be available at `http://localhost:7001`

### Interactive Chat Mode

```bash
# Using Make
make up-interactive

# Using Docker Compose
docker compose run --rm claude-interactive
```

### Run Specific Commands

```bash
# List available skills
make skills

# List available agents
make agents

# List conversation sessions
make sessions

# Execute arbitrary command
make exec-cmd
```

### Access Container Shell

```bash
make shell
# OR
docker compose run --rm claude-interactive /bin/bash
```

## Switching Providers

Providers are configured via environment variables in `.env`, not `config.yaml`.

### Switch Method

```bash
# 1. Edit .env to set the desired provider's API key
nano .env

# 2. Restart the container
docker compose restart claude-api

# 3. Verify in logs
docker compose logs -f claude-api
```

### Supported Providers

| Provider | Environment Variable | Notes |
|----------|---------------------|-------|
| **Claude (Anthropic)** | `ANTHROPIC_API_KEY` | Recommended |
| **Zai** | `ZAI_API_KEY` + `ZAI_BASE_URL` | Alternative provider |
| **Proxy** | `PROXY_BASE_URL` | LiteLLM or similar proxy |

Set **one** provider's API key. The backend auto-detects which provider to use based on which env var is set.

### Provider Verification

```bash
# Check which provider env vars are set
docker compose run --rm claude-interactive env | grep -E "ANTHROPIC_API_KEY|ZAI_API_KEY|PROXY_BASE_URL" | cut -d= -f1

# Test health endpoint (no auth required)
curl http://localhost:7001/health
```

### Important Notes

- **No rebuild required** — just update `.env` and restart
- **Sessions preserved** — conversation history remains in `./data`
- **API keys** — ensure the corresponding API key is set in `.env`
- **Active sessions** — existing sessions continue with their original provider

## Architecture

This Docker setup follows the **official Anthropic guidelines**:

### Container-Based Sandboxing

- Runs as **non-root user** (`appuser`) for security
- **Resource limits**: 1 CPU, 1GB RAM (per official requirements)
- Isolated filesystem with persistent volumes

### Multi-Mode Support

1. **API Server Mode** (`claude-api` service)
   - FastAPI HTTP/SSE server
   - Persistent across restarts
   - Port 7001 exposed

2. **Interactive Mode** (`claude-interactive` service)
   - Direct CLI access
   - Ephemeral containers
   - Full terminal support

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes* | Anthropic API key (for Claude) |
| `ZAI_API_KEY` | Yes* | Zai provider API key |
| `ZAI_BASE_URL` | No | Zai provider base URL |
| `API_KEY` | Yes | Shared secret for REST API auth |
| `CLI_ADMIN_PASSWORD` | Yes | Admin user password |
| `CLI_TESTER_PASSWORD` | Yes | Tester user password |
| `BACKEND_PUBLIC_URL` | No | Public URL for download links (default: your-backend-url.example.com) |
| `PLATFORM_DEFAULT_AGENT_ID` | No | Default agent for platform messages |
| `TELEGRAM_BOT_TOKEN` | No | Telegram bot token |
| `WHATSAPP_ACCESS_TOKEN` | No | WhatsApp Cloud API token |
| `ZALO_OA_ACCESS_TOKEN` | No | Zalo OA access token |
| `BLUEBUBBLES_PASSWORD` | No | iMessage server password |
| `API_PORT` | No | API server port (default: 7001) |

*At least one provider API key is required

### Volumes

- **./data:/app/data** - Session persistence
- **claude-config:/app/.claude** - Claude CLI configuration
- **./config.yaml:/app/config.yaml** - Runtime configuration

### Resource Limits

Per official Anthropic guidelines:
- **CPU**: 1 core (limit), 0.5 core (reservation)
- **Memory**: 1GB (limit), 512MB (reservation)

## Deployment Patterns

Based on the official [Anthropic hosting documentation](https://platform.claude.com/docs/en/agent-sdk/hosting):

### Pattern 1: Long-Running API Server (Default)

```bash
docker compose up -d claude-api
```

Best for: Continuous API access, multiple clients

### Pattern 2: Interactive Sessions

```bash
docker compose run --rm claude-interactive
```

Best for: Development, debugging, one-off tasks

### Pattern 3: Hybrid

```bash
# Start API server for continuous access
docker compose up -d claude-api

# Run interactive tasks with shared state
docker compose run --rm claude-interactive python main.py sessions
```

Best for: Mixed workloads

## Health Checks

The container includes a health check:

```bash
# Check container health
docker ps

# Manual health check
docker exec claude-agent-sdk-api python -c "import sys; sys.exit(0)"
```

## Logs

```bash
# Follow logs
docker compose logs -f claude-api

# View last 50 lines
docker compose logs --tail=50 claude-api

# View all services
docker compose logs
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker compose logs claude-api

# Verify environment variables
docker compose config

# Check container status
docker ps -a
```

### Permission Issues

The container runs as non-root user `appuser` (UID 1000). Ensure volume permissions:

```bash
sudo chown -R 1000:1000 ./data
```

### API Connection Refused

```bash
# Verify port is not in use
netstat -tuln | grep 7001

# Check container is running
docker ps | grep claude-agent-sdk
```

### Provider Configuration Issues

```bash
# Verify .env file is loaded
docker compose run --rm claude-interactive env | grep API

# Test configuration
docker compose run --rm claude-interactive python main.py --help
```

## Production Deployment

### Cloud Platforms

This Docker setup can be deployed to any platform supporting Docker:

- **AWS**: ECS, App Runner, Elastic Beanstalk
- **Google Cloud**: Cloud Run, GKE
- **Azure**: Container Apps, AKS
- **DigitalOcean**: App Platform
- **Heroku**: Container Registry

### Security Considerations

1. **Use Docker secrets** for API keys in production
2. **Enable HTTPS** with a reverse proxy (nginx/traefik)
3. **Restrict network access** (only outbound HTTPS)
4. **Set resource limits** appropriately
5. **Regular security updates**: `docker compose build --no-cache`

### Monitoring

```bash
# Container resource usage
docker stats claude-agent-sdk-api

# Disk usage
docker system df

# Log aggregation
docker compose logs --since 1h > logs.txt
```

## Updating

```bash
# Pull latest code
git pull

# Rebuild image
make rebuild

# Restart services
docker compose up -d claude-api
```

## Cleaning Up

```bash
# Stop and remove containers
make clean

# Remove volumes (WARNING: deletes session data)
docker compose down -v

# Remove all Docker data
docker system prune -a --volumes
```

## Official Documentation

- [Hosting the Agent SDK - Claude Docs](https://platform.claude.com/docs/en/agent-sdk/hosting)
- [Configure Claude Code - Docker Docs](https://docs.docker.com/ai/sandboxes/claude-code/)
- [Building agents with the Claude Agent SDK](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk)

## Support

For issues or questions:
1. Check the logs: `make logs`
2. Review this guide
3. Consult official Anthropic documentation
4. Check GitHub issues
