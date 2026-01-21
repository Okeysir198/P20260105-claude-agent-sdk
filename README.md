# Claude Agent SDK CLI

An interactive chat application that wraps the Claude Agent SDK with Skills and Subagents support. Supports multiple LLM providers and two operational modes (Direct SDK and API Server).

## Table of Contents

- [Quick Start](#quick-start)
- [Available Agents](#available-agents)
- [API Reference](#api-reference)
- [SSE Event Types](#sse-event-types)
- [WebSocket vs HTTP SSE](#websocket-vs-http-sse)
- [Frontend Integration Example](#frontend-integration-example)
- [Custom Agents](#custom-agents)
- [Configuration](#configuration)
- [Architecture](#architecture)

---

## Quick Start

### 1. Development Setup (using uv)

```bash
cd backend

# Create virtual environment and install dependencies (auto-creates venv)
uv sync
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Configure environment
cp .env.example .env
nano .env  # Add your ANTHROPIC_API_KEY

# Start API server
python main.py serve --port 7001
```

### 2. Production Setup (using Docker)

```bash
cd backend
cp .env.example .env
nano .env  # Add your ANTHROPIC_API_KEY

make build && make up
```

### 3. Verify the Server is Running

```bash
curl http://localhost:7001/health
# Response: {"status": "healthy"}
```

### 4. Make Your First Request

```bash
# Create a conversation with the default agent
curl -N -X POST http://localhost:7001/api/v1/conversations \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello! What can you help me with?"}'
```

### 5. Use a Specific Agent

```bash
# Create a conversation with the code-reviewer agent
curl -N -X POST http://localhost:7001/api/v1/conversations \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Review this code for security issues",
    "agent_id": "code-reviewer-x9y8z7w6"
  }'
```

---

## Available Agents

Use the `agent_id` parameter when creating a conversation to select which agent handles your request.

| agent_id | Type | Name | Purpose | read_only |
|----------|------|------|---------|-----------|
| `general-agent-a1b2c3d4` | general | General Assistant | General-purpose coding assistant for everyday tasks | false |
| `code-reviewer-x9y8z7w6` | reviewer | Code Reviewer | Specialized agent for thorough code reviews and security analysis | true |
| `doc-writer-m5n6o7p8` | doc-writer | Documentation Writer | Specialized agent for generating and improving documentation | false |
| `research-agent-q1r2s3t4` | researcher | Code Researcher | Read-only agent for exploring and understanding codebases | true |

### Listing Available Agents

```bash
curl http://localhost:7001/api/v1/config/agents
```

Response:
```json
{
  "agents": [
    {
      "agent_id": "general-agent-a1b2c3d4",
      "name": "General Assistant",
      "type": "general",
      "description": "General-purpose coding assistant for everyday tasks",
      "model": "sonnet",
      "read_only": false,
      "is_default": true
    },
    {
      "agent_id": "code-reviewer-x9y8z7w6",
      "name": "Code Reviewer",
      "type": "reviewer",
      "description": "Specialized agent for thorough code reviews and security analysis",
      "model": "sonnet",
      "read_only": true,
      "is_default": false
    }
  ],
  "total": 4
}
```

---

## API Reference

Base URL: `http://localhost:7001`

### Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/api/v1/conversations` | Create conversation with SSE streaming |
| POST | `/api/v1/conversations/{session_id}/stream` | Send follow-up message with SSE |
| POST | `/api/v1/conversations/{session_id}/interrupt` | Interrupt current task |
| WS | `/api/v1/ws/chat` | WebSocket for persistent multi-turn chat |
| POST | `/api/v1/sessions` | Create new session |
| GET | `/api/v1/sessions` | List all sessions |
| GET | `/api/v1/sessions/{id}/history` | Get conversation history |
| POST | `/api/v1/sessions/{id}/resume` | Resume session by ID |
| POST | `/api/v1/sessions/{id}/close` | Close session |
| DELETE | `/api/v1/sessions/{id}` | Delete session |
| POST | `/api/v1/sessions/resume` | Resume with session ID in body |
| GET | `/api/v1/config/agents` | List available agents |

---

### Health Check

#### `GET /health`

```bash
curl http://localhost:7001/health
```

**Response:**
```json
{"status": "ok", "service": "agent-sdk-api"}
```

---

### Conversations

#### `POST /api/v1/conversations`

Create a new conversation and stream the response via SSE.

**Request Body:**
```json
{
  "content": "Hello, how can you help me?",
  "session_id": null,
  "agent_id": "general-agent-a1b2c3d4",
  "resume_session_id": null
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `content` | string | **Yes** | The user message (min 1 char) |
| `session_id` | string | No | Existing session ID (auto-generated if null) |
| `agent_id` | string | No | Agent ID from `agents.yaml` (see [Available Agents](#available-agents)) |
| `resume_session_id` | string | No | Session ID to resume from |

**Response:** Server-Sent Events stream (see [SSE Event Types](#sse-event-types))

**Example - Default Agent:**
```bash
curl -N -X POST http://localhost:7001/api/v1/conversations \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello, help me with coding"}'
```

**Example - Specific Agent:**
```bash
curl -N -X POST http://localhost:7001/api/v1/conversations \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Review this code for security issues",
    "agent_id": "code-reviewer-x9y8z7w6"
  }'
```

---

#### `POST /api/v1/conversations/{session_id}/stream`

Send a follow-up message to an existing conversation.

**Request Body:**
```json
{"content": "Follow-up question"}
```

**Example:**
```bash
curl -N -X POST http://localhost:7001/api/v1/conversations/550e8400-e29b-41d4-a716-446655440000/stream \
  -H "Content-Type: application/json" \
  -d '{"content": "Can you explain more?"}'
```

---

#### `POST /api/v1/conversations/{session_id}/interrupt`

Interrupt the current task execution.

**Response:**
```json
{"status": "interrupted", "session_id": "550e8400-..."}
```

---

### Sessions

#### `POST /api/v1/sessions`

Create a new session (without sending a message).

**Request Body:**
```json
{
  "agent_id": "general-agent-a1b2c3d4",
  "resume_session_id": null
}
```

**Response (201 Created):**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ready",
  "resumed": false
}
```

---

#### `GET /api/v1/sessions`

List all sessions (newest first).

**Response:**
```json
[
  {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "created_at": "2026-01-20T10:30:00Z",
    "turn_count": 5,
    "first_message": "Hello, help me with...",
    "user_id": null
  }
]
```

---

#### `GET /api/v1/sessions/{id}/history`

Get the full conversation history for a session.

**Response:**
```json
{
  "session_id": "550e8400-...",
  "messages": [
    {"role": "user", "content": "Hello", "timestamp": "2026-01-20T10:30:00Z"},
    {"role": "assistant", "content": "Hi! How can I help?", "timestamp": "2026-01-20T10:30:05Z"},
    {"role": "tool_use", "content": "{...}", "tool_name": "Read", "tool_use_id": "toolu_123"},
    {"role": "tool_result", "content": "file contents", "tool_use_id": "toolu_123", "is_error": false}
  ],
  "turn_count": 2,
  "first_message": "Hello"
}
```

---

#### `POST /api/v1/sessions/{id}/resume`

Resume a specific session by ID.

**Request Body (optional):**
```json
{"initial_message": "Continue where we left off"}
```

**Response:**
```json
{"session_id": "550e8400-...", "status": "ready", "resumed": true}
```

---

#### `POST /api/v1/sessions/{id}/close`

Close a session (keeps it in storage for potential resumption).

**Response:**
```json
{"status": "closed"}
```

---

#### `DELETE /api/v1/sessions/{id}`

Permanently delete a session and its history.

**Response:**
```json
{"status": "deleted"}
```

---

#### `POST /api/v1/sessions/resume`

Resume a session by providing `resume_session_id` in the body.

**Request Body:**
```json
{"resume_session_id": "550e8400-e29b-41d4-a716-446655440000"}
```

**Response:**
```json
{"session_id": "550e8400-...", "status": "ready", "resumed": true}
```

---

### Configuration

#### `GET /api/v1/config/agents`

List all available agents that can be selected via `agent_id`.

**Response:**
```json
{
  "agents": [
    {
      "agent_id": "general-agent-a1b2c3d4",
      "name": "General Assistant",
      "type": "general",
      "description": "General-purpose coding assistant",
      "model": "sonnet",
      "read_only": false,
      "is_default": true
    },
    {
      "agent_id": "code-reviewer-x9y8z7w6",
      "name": "Code Reviewer",
      "type": "reviewer",
      "description": "Specialized for code reviews and security analysis",
      "model": "sonnet",
      "read_only": true,
      "is_default": false
    }
  ]
}
```

---

## SSE Event Types

When using streaming endpoints, the server sends Server-Sent Events (SSE) with the following event types:

| Event Type | Description | Data Format |
|------------|-------------|-------------|
| `session_id` | Real session ID from SDK (sent once at start) | `{"session_id": "uuid-xxx"}` |
| `text_delta` | Streaming text chunk | `{"text": "partial response..."}` |
| `tool_use` | Tool invocation started | `{"tool_name": "Read", "input": {"file_path": "..."}}` |
| `tool_result` | Tool execution completed | `{"tool_use_id": "...", "content": "...", "is_error": false}` |
| `done` | Conversation turn completed | `{"session_id": "...", "turn_count": 1, "total_cost_usd": 0.0}` |
| `error` | Error occurred | `{"error": "Error message"}` |

### SSE Message Format

Each SSE message follows this format:
```
event: <event_type>
data: <json_data>

```

Example stream:
```
event: session_id
data: {"session_id": "abc-123-def"}

event: text_delta
data: {"text": "Hello! "}

event: text_delta
data: {"text": "I can help you with coding tasks."}

event: done
data: {"session_id": "abc-123-def", "turn_count": 1, "total_cost_usd": 0.001}
```

---

## WebSocket vs HTTP SSE

This section explains the two communication approaches for multi-turn conversations and when to use each.

### The Problem: Async Context Isolation

The Claude Agent SDK uses AnyIO internally for async operations. AnyIO's cancel scopes have a fundamental constraint: **they must be entered and exited in the same task**. This creates challenges for HTTP-based APIs:

```
HTTP Request 1 (Turn 1)     HTTP Request 2 (Turn 2)
      │                            │
      ▼                            ▼
   Task A                       Task B
      │                            │
      ▼                            ▼
 SDK connect()              SDK query()
      │                            │
      ▼                            ✗ ERROR
 receive_response()         "Attempted to exit cancel scope
      │                      in a different task than it
      ▼                      was entered in"
   (works)
```

Each HTTP request runs in a **separate async task**, so the SDK client created in one request cannot be reused in another.

### Solution Comparison

| Approach | How It Works | Latency | Use Case |
|----------|--------------|---------|----------|
| **HTTP SSE** | Create fresh SDK client per request, use `resume_session_id` | ~2,500ms follow-up TTFT | Simple integrations, REST-first architectures |
| **WebSocket** | Keep SDK client alive in single async context | ~1,100ms follow-up TTFT | Performance-critical, real-time applications |

### Performance Benchmark

Measured with 3 turns: "Say just the number 1", "Say just the number 2", "Say just the number 3"

```
| Turn | HTTP SSE (reconnect) | WebSocket (persistent) | Savings |
|------|---------------------|------------------------|---------|
| 1    | 2394ms              | 1139ms                 | 1255ms  |
| 2    | 2560ms              | 1088ms                 | 1472ms  |
| 3    | 2601ms              | 1044ms                 | 1557ms  |

Average follow-up TTFT:
  HTTP SSE:   2580ms
  WebSocket:  1066ms
  Savings:    1514ms (59% faster)
```

**Direct SDK** (no API overhead): ~800ms TTFT, meaning WebSocket adds only ~10% overhead vs HTTP SSE's ~222% overhead.

### WebSocket Endpoint

#### `WS /api/v1/ws/chat`

Establishes a persistent WebSocket connection for multi-turn conversations.

**Connection URL:**
```
ws://localhost:7001/api/v1/ws/chat?agent_id=general-agent-a1b2c3d4
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_id` | string | No | Agent ID to use (defaults to general assistant) |

**Protocol:**

1. **Client connects** → Server accepts
2. **Server sends** `{"type": "ready"}` → Client can send messages
3. **Client sends** `{"content": "user message"}`
4. **Server streams** response events
5. **Repeat** from step 3 for multi-turn

**Server Event Types:**

| Type | Description | Data |
|------|-------------|------|
| `ready` | Connection established | `{}` |
| `session_id` | SDK session ID assigned | `{"session_id": "uuid"}` |
| `text_delta` | Streaming text chunk | `{"text": "partial..."}` |
| `tool_use` | Tool invocation | `{"id": "...", "name": "Read", "input": {...}}` |
| `done` | Turn completed | `{"turn_count": 1, "total_cost_usd": 0.01}` |
| `error` | Error occurred | `{"error": "message"}` |

**Example - JavaScript:**

```javascript
const ws = new WebSocket('ws://localhost:7001/api/v1/ws/chat?agent_id=general-agent-a1b2c3d4');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  switch (data.type) {
    case 'ready':
      console.log('Connected, ready to chat');
      ws.send(JSON.stringify({ content: 'Hello!' }));
      break;
    case 'text_delta':
      process.stdout.write(data.text);
      break;
    case 'done':
      console.log(`\nTurn ${data.turn_count} completed`);
      // Send follow-up (same connection!)
      ws.send(JSON.stringify({ content: 'Tell me more' }));
      break;
    case 'error':
      console.error('Error:', data.error);
      break;
  }
};

ws.onclose = () => console.log('Disconnected');
```

**Example - Python:**

```python
import asyncio
import json
import websockets

async def chat():
    uri = "ws://localhost:7001/api/v1/ws/chat?agent_id=general-agent-a1b2c3d4"

    async with websockets.connect(uri) as ws:
        # Wait for ready signal
        ready = await ws.recv()
        print(f"Connected: {ready}")

        # Send first message
        await ws.send(json.dumps({"content": "Hello!"}))

        # Receive response
        while True:
            msg = await ws.recv()
            data = json.loads(msg)

            if data["type"] == "text_delta":
                print(data["text"], end="", flush=True)
            elif data["type"] == "done":
                print(f"\n[Turn {data['turn_count']} done]")
                break

        # Send follow-up (same connection, same async context)
        await ws.send(json.dumps({"content": "Tell me more"}))

        # Receive follow-up response...

asyncio.run(chat())
```

### When to Use Each Approach

**Use HTTP SSE when:**
- Building simple REST-first integrations
- Single-turn or infrequent conversations
- Infrastructure doesn't support WebSocket
- Simpler deployment requirements

**Use WebSocket when:**
- Multi-turn conversations are common
- Latency is critical (saves ~1.5s per follow-up)
- Building real-time chat interfaces
- Need persistent connection for long sessions

### Architecture Deep Dive

**HTTP SSE Flow (with reconnection):**
```
Turn 1                              Turn 2
  │                                   │
  ▼                                   ▼
POST /conversations              POST /conversations/{id}/stream
  │                                   │
  ▼                                   ▼
Create ConversationSession       Create ConversationSession
  │                              (with resume_session_id)
  ▼                                   │
connect() → query() →            connect() → query() →
receive_response()               receive_response()
  │                                   │
  ▼                                   ▼
disconnect()                     disconnect()

Total: ~1,400ms reconnection overhead per turn
```

**WebSocket Flow (persistent connection):**
```
Connect                    Turn 1              Turn 2
  │                          │                   │
  ▼                          ▼                   ▼
ws://...?agent_id=...    {"content":...}    {"content":...}
  │                          │                   │
  ▼                          ▼                   ▼
Create SDK client        query() →          query() →
  │                    receive_response() receive_response()
  ▼                          │                   │
connect()                    ▼                   ▼
  │                      (same client)       (same client)
  ▼
{"type": "ready"}

Total: ~300ms overhead per turn (vs ~1,400ms)
```

The WebSocket endpoint maintains the SDK client in a single async context for the entire connection lifetime, avoiding the cancel scope task mismatch issue.

---

## Frontend Integration Example

### JavaScript/TypeScript

```javascript
// api.js - Claude Agent SDK API Client

const API_BASE = 'http://localhost:7001';

/**
 * List all available agents
 */
async function listAgents() {
  const response = await fetch(`${API_BASE}/api/v1/config/agents`);
  const data = await response.json();
  return data.agents;
}

/**
 * Create a new conversation with a specific agent
 * @param {string} message - User message
 * @param {string} agentId - Agent ID (optional, uses default if not specified)
 * @param {function} onEvent - Callback for each SSE event
 */
async function createConversation(message, agentId, onEvent) {
  const response = await fetch(`${API_BASE}/api/v1/conversations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      content: message,
      agent_id: agentId
    })
  });

  return handleSSEStream(response, onEvent);
}

/**
 * Send a follow-up message to an existing conversation
 * @param {string} sessionId - Session ID from previous response
 * @param {string} message - User message
 * @param {function} onEvent - Callback for each SSE event
 */
async function sendMessage(sessionId, message, onEvent) {
  const response = await fetch(
    `${API_BASE}/api/v1/conversations/${sessionId}/stream`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: message })
    }
  );

  return handleSSEStream(response, onEvent);
}

/**
 * Handle SSE stream and parse events
 */
async function handleSSEStream(response, onEvent) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let sessionId = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    let currentEvent = null;

    for (const line of lines) {
      if (line.startsWith('event:')) {
        currentEvent = line.slice(6).trim();
      } else if (line.startsWith('data:') && currentEvent) {
        const data = JSON.parse(line.slice(5).trim());

        // Capture session ID for return value
        if (currentEvent === 'session_id') {
          sessionId = data.session_id;
        }

        // Call the event handler
        onEvent({ event: currentEvent, data });
        currentEvent = null;
      }
    }
  }

  return sessionId;
}

// ============================================
// Usage Example
// ============================================

async function main() {
  // 1. List available agents
  const agents = await listAgents();
  console.log('Available agents:', agents.map(a => a.agent_id));

  // 2. Create conversation with code reviewer agent
  let fullResponse = '';

  const sessionId = await createConversation(
    'Review this function for security issues:\n\nfunction login(user, pass) {\n  return db.query(`SELECT * FROM users WHERE user="${user}" AND pass="${pass}"`);\n}',
    'code-reviewer-x9y8z7w6',
    (event) => {
      switch (event.event) {
        case 'session_id':
          console.log('Session started:', event.data.session_id);
          break;

        case 'text_delta':
          process.stdout.write(event.data.text);
          fullResponse += event.data.text;
          break;

        case 'tool_use':
          console.log('\n[Tool]', event.data.tool_name);
          break;

        case 'tool_result':
          console.log('[Tool Result]', event.data.content.slice(0, 100));
          break;

        case 'done':
          console.log('\n\nCompleted:', event.data.turn_count, 'turns');
          break;

        case 'error':
          console.error('Error:', event.data.error);
          break;
      }
    }
  );

  // 3. Send follow-up message
  console.log('\n--- Sending follow-up ---\n');

  await sendMessage(
    sessionId,
    'How should I fix the SQL injection vulnerability?',
    (event) => {
      if (event.event === 'text_delta') {
        process.stdout.write(event.data.text);
      }
    }
  );
}

main().catch(console.error);
```

### React Hook Example

```tsx
// useClaudeAgent.ts
import { useState, useCallback } from 'react';

interface SSEEvent {
  event: string;
  data: Record<string, any>;
}

export function useClaudeAgent(apiBase = 'http://localhost:7001') {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [response, setResponse] = useState('');

  const sendMessage = useCallback(async (
    message: string,
    agentId?: string
  ) => {
    setIsStreaming(true);
    setResponse('');

    const endpoint = sessionId
      ? `${apiBase}/api/v1/conversations/${sessionId}/stream`
      : `${apiBase}/api/v1/conversations`;

    const body = sessionId
      ? { content: message }
      : { content: message, agent_id: agentId };

    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });

      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        let currentEvent: string | null = null;

        for (const line of lines) {
          if (line.startsWith('event:')) {
            currentEvent = line.slice(6).trim();
          } else if (line.startsWith('data:') && currentEvent) {
            const data = JSON.parse(line.slice(5).trim());

            if (currentEvent === 'session_id') {
              setSessionId(data.session_id);
            } else if (currentEvent === 'text_delta') {
              setResponse(prev => prev + data.text);
            }

            currentEvent = null;
          }
        }
      }
    } finally {
      setIsStreaming(false);
    }
  }, [sessionId, apiBase]);

  const reset = useCallback(() => {
    setSessionId(null);
    setResponse('');
  }, []);

  return { sessionId, isStreaming, response, sendMessage, reset };
}
```

---

## Custom Agents

Agent definitions are stored in `backend/agent/agents.yaml`. Each agent has a unique ID and specific capabilities.

### Adding a New Agent

1. Open `backend/agent/agents.yaml`

2. Add your agent definition:

```yaml
agents:
  # ... existing agents ...

  my-custom-agent-abc123:
    name: "My Custom Agent"
    type: "custom"
    description: "Description of what this agent specializes in"
    system_prompt: |
      You are a specialized assistant for [purpose].
      Your key responsibilities:
      - Task 1
      - Task 2
      - Task 3
    tools:
      - Skill    # Enable skills
      - Task     # Enable subagent delegation
      - Read     # Read files
      - Write    # Write files (omit for read-only)
      - Bash     # Execute commands
      - Grep     # Search content
      - Glob     # Find files
    subagents:
      - researcher      # Code exploration
      - reviewer        # Code review
      - file_assistant  # File navigation
    skills:
      - code-analyzer
      - doc-generator
    model: sonnet       # Options: haiku, sonnet, opus
    read_only: false    # Set true to prevent file modifications
```

3. Set as default (optional):

```yaml
default_agent: my-custom-agent-abc123
```

4. Restart the API server for changes to take effect

### Agent ID Format

Agent IDs follow the pattern: `{type}-agent-{unique_suffix}`

Examples:
- `general-agent-a1b2c3d4`
- `code-reviewer-x9y8z7w6`
- `research-agent-q1r2s3t4`

### Agent Properties

| Property | Type | Description |
|----------|------|-------------|
| `name` | string | Human-readable agent name |
| `type` | string | Agent category (general, reviewer, doc-writer, researcher) |
| `description` | string | Brief description of agent purpose |
| `system_prompt` | string | Instructions that define agent behavior |
| `tools` | array | List of allowed tools |
| `subagents` | array | List of subagents this agent can delegate to |
| `skills` | array | List of skills this agent can use |
| `model` | string | Model to use (haiku, sonnet, opus) |
| `read_only` | boolean | If true, prevents Write/Edit operations |

---

## Configuration

### Environment Variables

```bash
# Required: Set your API key
ANTHROPIC_API_KEY=sk-ant-api03-...

# Optional: Alternative providers
ZAI_API_KEY=your_zai_key
ZAI_BASE_URL=https://api.zai-provider.com

MINIMAX_API_KEY=your_minimax_key
MINIMAX_BASE_URL=https://api.minimax-provider.com

# Optional: API server port
API_PORT=7001
```

### Provider Configuration

Edit `backend/config.yaml` to switch between providers:

```yaml
provider: claude  # Options: claude, zai, minimax
```

Docker users can switch providers without rebuilding:
```bash
cd backend
# Edit config.yaml and change the provider line, then restart
sed -i 's/provider: .*/provider: zai/' config.yaml && docker compose restart claude-api
```

---

## Architecture

```
├── backend/
│   ├── agent/                    # Core business logic
│   │   ├── agents.yaml          # Top-level agent definitions
│   │   ├── subagents.yaml       # Delegation subagent definitions
│   │   ├── core/
│   │   │   ├── session.py       # ConversationSession (is_connected property)
│   │   │   ├── agent_options.py # ClaudeAgentOptions builder
│   │   │   ├── storage.py       # Session persistence (data/sessions.json)
│   │   │   └── config.py        # Provider configuration
│   │   ├── discovery/           # Skills and MCP server discovery
│   │   └── display/             # Rich console output utilities
│   │
│   ├── api/                      # FastAPI HTTP/SSE server
│   │   ├── main.py              # App factory with global exception handlers
│   │   ├── dependencies.py      # SessionManagerDep for DI
│   │   ├── models/              # Pydantic request/response models
│   │   ├── core/errors.py       # APIError, SessionNotFoundError
│   │   ├── routers/
│   │   │   ├── sessions.py      # Session CRUD (uses SessionManagerDep)
│   │   │   ├── conversations.py # SSE streaming (async session access)
│   │   │   └── configuration.py # Skills and agents listing
│   │   └── services/
│   │       ├── session_manager.py # Session lifecycle (async methods)
│   │       └── message_utils.py   # SSE message conversion
│   │
│   ├── cli/                      # Click-based CLI
│   │   ├── main.py              # CLI entry point
│   │   └── commands/            # chat, serve, skills, agents, sessions
│   │
│   ├── config.yaml              # Provider configuration
│   ├── data/sessions.json       # Persisted session history
│   └── main.py                  # Application entry point
│
└── frontend/                     # Next.js 16 chat UI
    ├── app/api/                  # API routes (using proxyToBackend utility)
    ├── components/chat/          # Chat components (ExpandablePanel, tool messages)
    ├── lib/
    │   ├── api-proxy.ts         # Shared backend proxy utility
    │   └── animations.ts        # Framer Motion animation variants
    ├── hooks/                    # use-sse-stream, use-claude-chat, use-sessions
    └── types/                    # TypeScript definitions
```

### Session Management Architecture

The API server uses a **SessionManager** pattern with async methods:

- **In-memory cache** (`SessionManager._sessions`) for fast access
- **Async locking** ensures thread-safe concurrent access
- **Persistent storage** backs session metadata to `data/sessions.json`
- **Global exception handlers** convert `SessionNotFoundError`/`APIError` to JSON responses
- **Dependency injection** via `SessionManagerDep` type alias

### Data Flows

**API Mode Flow:**
```
Frontend → POST /api/v1/conversations/{session_id}/stream
        → api/routers/conversations.py
        → SessionManager.get_or_create_conversation_session() (async)
        → ConversationSession.connect() (if not session.is_connected)
        → ClaudeSDKClient → SSE Stream Response
```

**Direct Mode Flow:**
```
CLI → ConversationSession → ClaudeSDKClient
```

---

## Chat Session Principles

This section documents the core principles for handling chat sessions via SSE streaming.

### 1. SSE Streaming Architecture

Server-Sent Events (SSE) provide real-time, unidirectional streaming from server to client.

```
┌─────────┐    POST /conversations/{id}/stream    ┌─────────┐
│  Client │ ─────────────────────────────────────→│  Server │
│         │                                        │         │
│         │←─── event: session_id ────────────────│         │
│         │←─── event: text_delta ────────────────│         │
│         │←─── event: text_delta ────────────────│         │
│         │←─── event: tool_use ──────────────────│         │
│         │←─── event: tool_result ───────────────│         │
│         │←─── event: text_delta ────────────────│         │
│         │←─── event: done ──────────────────────│         │
└─────────┘                                        └─────────┘
```

**Implementation:**
```python
# backend/api/routers/conversations.py
@router.post("/{session_id}/stream")
async def stream_conversation(session_id: str, request: SendMessageRequest, manager: SessionManagerDep):
    return EventSourceResponse(
        _stream_conversation_events(session_id, request.content, manager),
        media_type="text/event-stream"
    )
```

**Event Types:**
| Event | Description | Data Format |
|-------|-------------|-------------|
| `session_id` | Session initialized | `{"session_id": "uuid"}` |
| `text_delta` | Streaming text chunk | `{"text": "partial..."}` |
| `tool_use` | Tool invocation | `{"tool_name": "Read", "input": {...}}` |
| `tool_result` | Tool completed | `{"tool_use_id": "...", "content": "..."}` |
| `done` | Turn completed | `{"turn_count": 1, "total_cost_usd": 0.01}` |
| `error` | Error occurred | `{"error": "message", "type": "ErrorType"}` |

### 2. Connection Persistence

SDK client connections persist across multiple turns within a session.

```
Turn 1: User sends "Hello"
    ↓
SessionManager.get_or_create_conversation_session(session_id)
    ↓
Session NOT in cache → Create ConversationSession → Connect SDK client
    ↓
_sessions[session_id] = session  (cached)
    ↓
Stream response...

Turn 2: User sends "Follow up question"
    ↓
SessionManager.get_or_create_conversation_session(session_id)
    ↓
Session FOUND in cache → Return existing session (already connected)
    ↓
Stream response... (reuses same WebSocket connection)
```

**Key Components:**

```python
# backend/api/services/session_manager.py
class SessionManager:
    def __init__(self):
        self._sessions: dict[str, ConversationSession] = {}  # In-memory cache
        self._lock = asyncio.Lock()  # Thread-safe access

    async def get_or_create_conversation_session(self, session_id: str) -> ConversationSession:
        async with self._lock:
            if session_id not in self._sessions:
                # Create new session with resume capability
                options = create_enhanced_options(resume_session_id=session_id)
                session = ConversationSession(options)
                self._sessions[session_id] = session
            return self._sessions[session_id]
```

```python
# backend/agent/core/session.py
class ConversationSession:
    def __init__(self, options):
        self.client = ClaudeSDKClient(options)  # One client per session
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def connect(self):
        if not self._connected:
            await self.client.connect()
            self._connected = True
```

**Connection Lifecycle:**
```
create_session() ──→ ConversationSession created ──→ connect() ──→ WebSocket open
                                                          ↓
                                                    Multi-turn chat
                                                          ↓
close_session() ──→ disconnect() ──→ WebSocket closed ──→ Session removed from cache
```

### 3. Concurrent Session Support

Multiple independent sessions can run simultaneously.

```
SessionManager._sessions = {
    "session-aaa": ConversationSession(ClaudeSDKClient_1),  ← User A
    "session-bbb": ConversationSession(ClaudeSDKClient_2),  ← User B
    "session-ccc": ConversationSession(ClaudeSDKClient_3),  ← User C
}
```

**Concurrency Model:**

| Scenario | Behavior |
|----------|----------|
| Different sessions | ✅ Fully parallel - independent clients |
| Same session, sequential | ✅ Supported - reuses connection |
| Same session, concurrent | ⚠️ Not recommended - SDK may queue or error |

**Thread Safety:**
```python
async def get_or_create_conversation_session(self, session_id: str):
    async with self._lock:  # Prevents race conditions
        if session_id not in self._sessions:
            # Create session...
        return self._sessions[session_id]
```

**Best Practices:**
1. Use unique `session_id` per user/conversation
2. Avoid sending multiple messages to same session concurrently
3. Implement client-side message queuing if needed

### 4. Chat History Persistence

Both session metadata and full conversation history are persisted locally.

**Storage Architecture:**
```
┌────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│  SessionManager    │────→│  SessionStorage     │     │  HistoryStorage     │
│  (in-memory cache) │     │  (metadata)         │     │  (messages)         │
└────────────────────┘     └─────────────────────┘     └─────────────────────┘
         ↓                           ↓                           ↓
   Fast access for           data/sessions.json         data/history/{id}.jsonl
   active sessions            Session metadata           Full message history
```

**What's Persisted:**

1. **Session Metadata** (`data/sessions.json`):
```json
[
  {
    "session_id": "abc-123-def",
    "created_at": "2024-01-15T10:30:00Z",
    "turn_count": 5,
    "first_message": "Hello, help me with...",
    "user_id": null
  }
]
```

2. **Message History** (`data/history/{session_id}.jsonl`):
```jsonl
{"role": "user", "content": "Hello, help me with...", "timestamp": "2024-01-15T10:30:00Z"}
{"role": "assistant", "content": "I'd be happy to help...", "timestamp": "2024-01-15T10:30:05Z"}
{"role": "tool_use", "content": "{\"file_path\": \"src/main.py\"}", "tool_name": "Read", "tool_use_id": "tool_123", "timestamp": "..."}
{"role": "tool_result", "content": "file contents...", "tool_use_id": "tool_123", "is_error": false, "timestamp": "..."}
{"role": "user", "content": "Show me an example", "timestamp": "2024-01-15T10:31:00Z"}
{"role": "assistant", "content": "Here's an example...", "timestamp": "2024-01-15T10:31:10Z"}
```

**Message Types:**
| Role | Description |
|------|-------------|
| `user` | User messages |
| `assistant` | Claude's responses (accumulated from text_delta events) |
| `tool_use` | Tool invocation with tool_name and input |
| `tool_result` | Tool execution result |

**Retrieve History API:**
```bash
curl http://localhost:7001/api/v1/sessions/{session_id}/history
```

Response:
```json
{
  "session_id": "abc-123-def",
  "messages": [
    {"role": "user", "content": "Hello...", "timestamp": "..."},
    {"role": "assistant", "content": "I'd be happy...", "timestamp": "..."}
  ],
  "turn_count": 5,
  "first_message": "Hello, help me with..."
}
```

**Session Resume Flow:**
```
1. User requests resume with session_id
    ↓
2. create_enhanced_options(resume_session_id=session_id)
    ↓
3. ClaudeAgentOptions includes resume_session_id
    ↓
4. SDK restores conversation context from Claude's servers
    ↓
5. Local history available via GET /sessions/{id}/history
    ↓
6. User continues conversation with full history
```

**Note:** The Claude SDK also maintains conversation history on Anthropic's servers for the `resume_session_id` feature. Local storage provides additional persistence for your own tracking and display purposes.

### 5. Follow-up Messages

Follow-up messages within a session reuse the existing connection and maintain conversation context.

**How It Works:**

```
┌─────────────────────────────────────────────────────────────────────┐
│  Initial Message                                                     │
│  POST /api/v1/conversations/session-123/stream                      │
│  {"content": "What is Python?"}                                     │
└─────────────────────────────────────────────────────────────────────┘
        │
        ▼
   ┌─────────────────────────────────────┐
   │ SessionManager._sessions = {}       │  ← Empty cache
   │ Create new ConversationSession      │
   │ Connect to Claude SDK               │
   │ _sessions["session-123"] = session  │  ← Cached
   └─────────────────────────────────────┘
        │
        ▼
   Response: "Python is a programming language..."

┌─────────────────────────────────────────────────────────────────────┐
│  Follow-up Message (same session_id)                                │
│  POST /api/v1/conversations/session-123/stream                      │
│  {"content": "Show me an example"}                                  │
└─────────────────────────────────────────────────────────────────────┘
        │
        ▼
   ┌─────────────────────────────────────┐
   │ SessionManager._sessions has key    │  ← Cache hit!
   │ Return existing session             │
   │ Already connected, skip connect()   │
   │ SDK maintains conversation context  │
   └─────────────────────────────────────┘
        │
        ▼
   Response: "Here's a Python example..." (knows context from turn 1)
```

**Key Points:**
1. **Same session_id** - Client must use the same session_id for follow-ups
2. **Connection reused** - No reconnection overhead on subsequent messages
3. **Context preserved** - Claude SDK maintains full conversation history
4. **Turn count incremented** - Each message increases `turn_count`

**Frontend Implementation:**
```javascript
// Store session_id from first response
let sessionId = null;

// First message - creates new session
async function startConversation(message) {
  const response = await fetch('/api/v1/sessions', {
    method: 'POST',
    body: JSON.stringify({ content: message })
  });
  const data = await response.json();
  sessionId = data.session_id;  // Save for follow-ups
  return streamResponse(sessionId, message);
}

// Follow-up messages - reuse session
async function sendFollowUp(message) {
  if (!sessionId) throw new Error('No active session');
  return streamResponse(sessionId, message);  // Same session_id
}

async function streamResponse(sid, message) {
  const response = await fetch(`/api/v1/conversations/${sid}/stream`, {
    method: 'POST',
    body: JSON.stringify({ content: message })
  });
  // Handle SSE stream...
}
```

### 6. Session Resume

Resume allows continuing a conversation after server restart or session timeout.

**Resume vs Follow-up:**

| Aspect | Follow-up | Resume |
|--------|-----------|--------|
| Session in memory | ✅ Yes | ❌ No (expired/restarted) |
| Connection state | Connected | Disconnected |
| Use case | Continuous chat | Return after break |
| API call | Same endpoint | Create with `resume_session_id` |

**Resume Flow:**

```
┌─────────────────────────────────────────────────────────────────────┐
│  Original Session (yesterday)                                        │
│  session_id: "abc-123-def"                                          │
│  Messages: "What is Python?" → "Show example" → "Explain classes"   │
│  Server restarts overnight... session lost from memory               │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  Resume Request (today)                                              │
│  POST /api/v1/sessions                                              │
│  {"resume_session_id": "abc-123-def"}                               │
└─────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────────┐
│  SessionManager.create_session(resume_session_id="abc-123-def")     │
│      │                                                               │
│      ▼                                                               │
│  create_enhanced_options(resume_session_id="abc-123-def")           │
│      │                                                               │
│      ▼                                                               │
│  ClaudeAgentOptions(resume_session_id="abc-123-def")                │
│      │                                                               │
│      ▼                                                               │
│  Claude SDK restores conversation from Anthropic's servers          │
└─────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Continue Conversation                                               │
│  POST /api/v1/conversations/{new_session_id}/stream                 │
│  {"content": "Now explain decorators"}                              │
│                                                                      │
│  Claude remembers: Python intro → example → classes → decorators    │
└─────────────────────────────────────────────────────────────────────┘
```

**API Usage:**

```bash
# List available sessions to find session_id
curl http://localhost:7001/api/v1/sessions

# Resume a specific session
curl -X POST http://localhost:7001/api/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{"resume_session_id": "abc-123-def"}'

# Response includes new session_id for this connection
{"session_id": "xyz-789-ghi", "status": "ready", "resumed": true}

# Continue conversation with new session_id
curl -N -X POST http://localhost:7001/api/v1/conversations/xyz-789-ghi/stream \
  -H "Content-Type: application/json" \
  -d '{"content": "Continue where we left off"}'
```

**CLI Usage:**

```bash
# List previous sessions
python main.py sessions

# Resume specific session
python main.py --session-id abc-123-def
```

**Implementation:**

```python
# backend/agent/core/agent_options.py
def create_enhanced_options(
    agent_id: str | None = None,
    resume_session_id: str | None = None
) -> ClaudeAgentOptions:
    options = ClaudeAgentOptions(
        # ... other options ...
        resume_session_id=resume_session_id,  # Key parameter
    )
    return options
```

```python
# backend/api/services/session_manager.py
async def create_session(
    self,
    agent_id: str | None = None,
    resume_session_id: str | None = None  # Pass to SDK
) -> str:
    options = create_enhanced_options(
        agent_id=agent_id,
        resume_session_id=resume_session_id
    )
    session = ConversationSession(options)
    await session.connect()  # SDK loads history if resuming
    # ...
```

**Important Notes:**
1. **Resume requires valid session_id** - Must exist in Claude's servers
2. **New session_id returned** - The resumed session gets a new local ID
3. **Full history restored** - Claude remembers all previous messages
4. **Session expiry** - Sessions may expire after extended inactivity (SDK-dependent)

### 7. Complete Request Lifecycle

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Client Request                               │
│  POST /api/v1/conversations/{session_id}/stream                     │
│  Body: {"content": "What is 2+2?"}                                  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  1. FastAPI Router (conversations.py)                               │
│     - Receives request                                               │
│     - Injects SessionManagerDep                                      │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  2. SessionManager.get_or_create_conversation_session()             │
│     - Check _sessions cache                                          │
│     - Create or return existing ConversationSession                  │
│     - Thread-safe with asyncio.Lock                                  │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  3. ConversationSession                                              │
│     - Check is_connected                                             │
│     - Call connect() if needed (opens WebSocket)                     │
│     - Send query via client.query(content)                           │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  4. ClaudeSDKClient                                                  │
│     - Maintains WebSocket to Claude API                              │
│     - Streams response messages                                      │
│     - Handles tool execution                                         │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  5. SSE Response Stream                                              │
│     - Convert SDK messages to SSE events                             │
│     - Yield events as async generator                                │
│     - Client receives real-time updates                              │
└─────────────────────────────────────────────────────────────────────┘
```

---

## CLI Commands

```bash
cd backend

# Interactive chat
python main.py                        # Default mode
python main.py --mode direct          # Explicit direct mode
python main.py --mode api             # API mode (requires server)

# Start API server
python main.py serve                  # Default: 0.0.0.0:7001
python main.py serve --port 8080      # Custom port
python main.py serve --reload         # Auto-reload for development

# List resources
python main.py agents                 # List agents
python main.py sessions               # List conversation history

# Resume session
python main.py --session-id <id>      # Resume existing session
```

---

## Docker Commands (Production)

Docker is recommended for production deployments. For development, use `uv` (see [Quick Start](#quick-start)).

```bash
cd backend

# Build and start
make build && make up

# View logs
make logs

# Interactive mode
make up-interactive

# Switch providers (edit config.yaml then restart)
sed -i 's/provider: .*/provider: zai/' config.yaml && docker compose restart claude-api

# Stop services
make down

# Clean up
make clean
```

See [DOCKER.md](backend/DOCKER.md) for complete production deployment guide.

---

## Documentation

- [DOCKER.md](DOCKER.md) - Complete Docker deployment guide
- [CLAUDE.md](CLAUDE.md) - Claude Code instructions

---

## License

MIT
