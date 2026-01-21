# Claude Agent SDK CLI

An interactive chat application wrapping the Claude Agent SDK with multi-agent support. Provides CLI and web interfaces with WebSocket/SSE streaming.

## Table of Contents

- [Quick Start](#quick-start)
- [Available Agents](#available-agents)
- [API Reference](#api-reference)
- [WebSocket vs HTTP SSE](#websocket-vs-http-sse)
- [Frontend Setup](#frontend-setup)
- [Custom Agents](#custom-agents)
- [Configuration](#configuration)
- [CLI Commands](#cli-commands)

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
nano .env  # Add your ANTHROPIC_API_KEY

# Start API server
python main.py serve --port 7001
```

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev  # Starts on port 7002 with WebSocket proxy
```

### 3. Verify

```bash
curl http://localhost:7001/health
# Response: {"status": "ok", "service": "agent-sdk-api"}
```

### 4. First Request

```bash
# Default agent
curl -N -X POST http://localhost:7001/api/v1/conversations \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello!"}'

# Specific agent
curl -N -X POST http://localhost:7001/api/v1/conversations \
  -H "Content-Type: application/json" \
  -d '{"content": "Review this code", "agent_id": "code-reviewer-x9y8z7w6"}'
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
curl http://localhost:7001/api/v1/config/agents
```

---

## API Reference

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
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
ws://localhost:7001/api/v1/ws/chat?agent_id=general-agent-a1b2c3d4
```

**Protocol:**
1. Server sends `{"type": "ready"}`
2. Client sends `{"content": "message"}`
3. Server streams response events
4. Repeat for multi-turn

**JavaScript Example:**

```javascript
const ws = new WebSocket('ws://localhost:7002/ws/chat?agent_id=general-agent-a1b2c3d4');

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

The Next.js frontend uses a custom Express server for WebSocket proxying.

```bash
cd frontend
npm install
npm run dev    # Custom server with WebSocket proxy (port 7002)
```

### Architecture

```
Browser → Frontend (server.js:7002) → Backend (:7001)
  /ws/chat      → /api/v1/ws/chat     (WebSocket proxy)
  /api/proxy/*  → /api/v1/*           (HTTP proxy)
  /*            → Next.js             (Pages)
```

### Single Tunnel Deployment

```bash
# Terminal 1: Backend
cd backend && python main.py serve --port 7001

# Terminal 2: Frontend
cd frontend && npm run dev

# Terminal 3: Tunnel
cloudflare tunnel --url http://localhost:7002
```

### Environment Variables

Create `frontend/.env.local`:

```bash
BACKEND_URL=http://localhost:7001
# NEXT_PUBLIC_WS_URL=wss://your-domain.com/ws/chat
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

### Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-api03-...

# Optional: Alternative providers
ZAI_API_KEY=your_key
ZAI_BASE_URL=https://api.zai-provider.com
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

### Docker (Production)

```bash
cd backend
make build && make up
make logs
make down
```

---

## Documentation

- [DOCKER.md](backend/DOCKER.md) - Docker deployment guide
- [CLAUDE.md](CLAUDE.md) - Architecture and development instructions

## License

MIT
