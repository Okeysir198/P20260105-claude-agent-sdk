# Claude Agent SDK CLI

An interactive chat application wrapping the Claude Agent SDK with multi-agent support. Provides CLI and web interfaces with WebSocket/SSE streaming.

## Table of Contents

- [Quick Start](#quick-start)
- [Testing](#testing)
- [Available Agents](#available-agents)
- [API Reference](#api-reference)
- [WebSocket vs HTTP SSE](#websocket-vs-http-sse)
- [Frontend Setup](#frontend-setup)
- [Custom Agents](#custom-agents)
- [Configuration](#configuration)
- [CLI Commands](#cli-commands)
- [Deployment](#deployment)

---

## Quick Start

### 1. Backend Setup

```bash
cd backend

# Install dependencies
uv sync
source .venv/bin/activate

# Configure environment
cp .env.example .env
nano .env  # Add your ANTHROPIC_API_KEY and API_KEY

# Start API server
python main.py serve --port 7001
```

### 2. Frontend Setup

```bash
cd frontend
npm install

# Configure environment
cp .env.example .env.local
nano .env.local  # Set NEXT_PUBLIC_API_URL and NEXT_PUBLIC_API_KEY

# Start Next.js dev server
npm run dev  # Starts on port 7002
```

### 3. Verify

```bash
# Health check (no auth required)
curl http://localhost:7001/health
# Response: {"status": "ok", "service": "agent-sdk-api"}

# Test with API key
curl -H "X-API-Key: your-api-key" http://localhost:7001/api/v1/sessions
```

---

## Testing

### Backend Testing

```bash
cd backend
source .venv/bin/activate

# 1. Health check (no auth required)
curl http://localhost:7001/health

# 2. Test API key authentication - should fail (401)
curl http://localhost:7001/api/v1/sessions
# Response: {"detail": "Invalid or missing API key"}

# 3. Test API key authentication - should succeed
curl -H "X-API-Key: your-api-key" http://localhost:7001/api/v1/sessions

# 4. Test with query parameter
curl "http://localhost:7001/api/v1/sessions?api_key=your-api-key"

# 5. List agents
curl -H "X-API-Key: your-api-key" http://localhost:7001/api/v1/config/agents

# 6. Test SSE conversation
curl -N -X POST http://localhost:7001/api/v1/conversations \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"content": "Hello!"}'

# 7. Test WebSocket (using websocat)
websocat "ws://localhost:7001/api/v1/ws/chat?api_key=your-api-key&agent_id=general-agent-a1b2c3d4"

# 8. Run unit tests
python -m pytest tests/
```

### Frontend Testing

```bash
cd frontend

# 1. Ensure .env.local is configured
cat .env.local
# Should show:
# NEXT_PUBLIC_API_URL=http://localhost:7001/api/v1
# NEXT_PUBLIC_API_KEY=your-api-key

# 2. Start development server
npm run dev

# 3. Open browser
# Navigate to http://localhost:7002
# - Select an agent from dropdown
# - Send a message
# - Verify WebSocket connection works
# - Check browser console for any errors

# 4. Build for production
npm run build

# 5. Run production server
npm start
```

### CORS Testing

```bash
# Test CORS preflight from browser origin
curl -X OPTIONS http://localhost:7001/api/v1/sessions \
  -H "Origin: http://localhost:7002" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: X-API-Key" \
  -v

# Should return Access-Control-Allow-* headers
```

---

## Available Agents

| agent_id | Name | Purpose | read_only |
|----------|------|---------|-----------|
| `general-agent-a1b2c3d4` | General Assistant | General-purpose coding assistant | false |
| `code-reviewer-x9y8z7w6` | Code Reviewer | Code reviews and security analysis | true |
| `doc-writer-m5n6o7p8` | Documentation Writer | Documentation generation | false |
| `research-agent-q1r2s3t4` | Code Researcher | Codebase exploration | true |

```bash
# List all agents
curl -H "X-API-Key: your-api-key" http://localhost:7001/api/v1/config/agents
```

---

## API Reference

### Authentication

All endpoints except `/health` require API key authentication via:
- **Header:** `X-API-Key: your-api-key`
- **Query parameter:** `?api_key=your-api-key`

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check (no auth) |
| **WS** | `/api/v1/ws/chat` | WebSocket for multi-turn chat |
| POST | `/api/v1/conversations` | Create conversation (SSE) |
| POST | `/api/v1/conversations/{id}/stream` | Follow-up message (SSE) |
| POST | `/api/v1/conversations/{id}/interrupt` | Interrupt task |
| POST | `/api/v1/sessions` | Create session |
| GET | `/api/v1/sessions` | List sessions |
| GET | `/api/v1/sessions/{id}/history` | Get message history |
| POST | `/api/v1/sessions/{id}/resume` | Resume session |
| DELETE | `/api/v1/sessions/{id}` | Delete session |
| GET | `/api/v1/config/agents` | List agents |

### SSE Event Types

| Event | Description | Data |
|-------|-------------|------|
| `session_id` | Session initialized | `{"session_id": "uuid"}` |
| `text_delta` | Streaming text chunk | `{"text": "..."}` |
| `tool_use` | Tool invocation | `{"tool_name": "Read", "input": {...}}` |
| `tool_result` | Tool completed | `{"tool_use_id": "...", "content": "..."}` |
| `done` | Turn completed | `{"turn_count": 1, "total_cost_usd": 0.01}` |
| `error` | Error occurred | `{"error": "message"}` |

---

## WebSocket vs HTTP SSE

| Approach | Latency | Use Case |
|----------|---------|----------|
| **WebSocket** | ~1,100ms TTFT | Real-time chat, multi-turn conversations |
| **HTTP SSE** | ~2,500ms TTFT | Simple integrations, single-turn requests |

### WebSocket Connection

```
ws://localhost:7001/api/v1/ws/chat?api_key=your-key&agent_id=general-agent-a1b2c3d4
```

**Protocol:**
1. Server sends `{"type": "ready"}`
2. Client sends `{"content": "message"}`
3. Server streams response events
4. Repeat for multi-turn

**JavaScript Example:**

```javascript
const apiKey = 'your-api-key';
const agentId = 'general-agent-a1b2c3d4';
const ws = new WebSocket(`ws://localhost:7001/api/v1/ws/chat?api_key=${apiKey}&agent_id=${agentId}`);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  switch (data.type) {
    case 'ready':
      ws.send(JSON.stringify({ content: 'Hello!' }));
      break;
    case 'text_delta':
      process.stdout.write(data.text);
      break;
    case 'done':
      console.log(`\nTurn ${data.turn_count} completed`);
      break;
  }
};
```

**React Hook:**

```tsx
import { useClaudeChat } from '@/hooks';

function ChatComponent() {
  const { messages, isStreaming, sendMessage, interrupt } = useClaudeChat({
    agentId: 'general-agent-a1b2c3d4',
  });

  return (
    <div>
      {messages.map(msg => <div key={msg.id}>{msg.content}</div>)}
      <button onClick={() => sendMessage('Hello')}>Send</button>
      <button onClick={interrupt}>Stop</button>
    </div>
  );
}
```

---

## Frontend Setup

The Next.js frontend connects directly to the backend API.

```bash
cd frontend
npm install
npm run dev    # Next.js dev server (port 7002)
```

### Architecture

```
Development:
  Browser → http://localhost:7001/api/v1/* (REST API)
  Browser → ws://localhost:7001/api/v1/ws/chat (WebSocket)

Production:
  Browser → https://your-backend-domain.com/api/v1/* (REST API)
  Browser → wss://your-backend-domain.com/api/v1/ws/chat (WebSocket)
```

### Environment Variables

Create `frontend/.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:7001/api/v1
NEXT_PUBLIC_API_KEY=your-api-key
```

For production, create `frontend/.env.production`:

```bash
NEXT_PUBLIC_API_URL=https://your-backend-domain.com/api/v1
NEXT_PUBLIC_API_KEY=your-prod-api-key
```

---

## Custom Agents

Edit `backend/agent/agents.yaml`:

```yaml
my-custom-agent-abc123:
  name: "My Custom Agent"
  type: "custom"
  description: "What this agent does"
  system_prompt: |
    Your role-specific instructions here.
  tools: [Read, Write, Bash, Grep, Glob]
  subagents: [researcher, reviewer]
  model: sonnet  # haiku, sonnet, opus
  read_only: false
```

**Agent Properties:**

| Property | Description |
|----------|-------------|
| `name` | Human-readable name |
| `type` | Category (general, reviewer, doc-writer, researcher) |
| `system_prompt` | Instructions appended to claude_code preset |
| `tools` | Allowed tools |
| `subagents` | Subagents for delegation |
| `model` | haiku, sonnet, or opus |
| `read_only` | Prevents Write/Edit if true |

---

## Configuration

### Backend Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-api03-...

# API Authentication
API_KEY=your-secure-api-key

# CORS (comma-separated origins)
CORS_ORIGINS=http://localhost:7002,https://your-frontend-domain.com

# Server
API_HOST=0.0.0.0
API_PORT=7001

# Optional: Alternative providers
ZAI_API_KEY=your_key
ZAI_BASE_URL=https://api.zai-provider.com
```

### Frontend Environment Variables

```bash
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:7001/api/v1
NEXT_PUBLIC_API_KEY=your-api-key
```

### Provider Configuration

Edit `backend/config.yaml`:

```yaml
provider: claude  # claude, zai, minimax
```

---

## CLI Commands

```bash
cd backend

# Interactive chat
python main.py                    # Default direct mode
python main.py --mode api         # API mode (requires server)

# API server
python main.py serve --port 7001
python main.py serve --reload     # Development with auto-reload

# List resources
python main.py agents
python main.py sessions

# Resume session
python main.py --session-id <id>
```

---

## Deployment

### Separate Tunnel Deployment (Cloudflare)

```bash
# Terminal 1: Backend
cd backend && python main.py serve --port 7001

# Terminal 2: Frontend
cd frontend && npm run build && npm start

# Terminal 3: Backend tunnel
cloudflare tunnel --url http://localhost:7001 --hostname api.your-domain.com

# Terminal 4: Frontend tunnel
cloudflare tunnel --url http://localhost:7002 --hostname app.your-domain.com
```

### Docker (Backend)

```bash
cd backend
make build && make up
make logs
make down
```

### Production Checklist

1. Set unique `API_KEY` values in both backend and frontend
2. Update `CORS_ORIGINS` to include your frontend domain
3. Use HTTPS/WSS in production URLs
4. Configure proper firewall rules

---

## Documentation

- [DOCKER.md](backend/DOCKER.md) - Docker deployment guide
- [CLAUDE.md](CLAUDE.md) - Architecture and development instructions

## License

MIT
