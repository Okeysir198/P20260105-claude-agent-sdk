# Claude Agent SDK CLI

An interactive chat application that wraps the Claude Agent SDK with Skills and Subagents support. Supports multiple LLM providers and two operational modes (Direct SDK and API Server).

## Table of Contents

- [Quick Start](#quick-start)
- [Available Agents](#available-agents)
- [API Reference](#api-reference)
- [SSE Event Types](#sse-event-types)
- [Frontend Integration Example](#frontend-integration-example)
- [Custom Agents](#custom-agents)
- [Configuration](#configuration)
- [Architecture](#architecture)

---

## Quick Start

### 1. Start the API Server

```bash
# Using Docker (Recommended)
cp .env.example .env
nano .env  # Add your ANTHROPIC_API_KEY

docker compose build
docker compose up -d claude-api

# Or run locally
python main.py serve --port 7001
```

### 2. Verify the Server is Running

```bash
curl http://localhost:7001/health
# Response: {"status": "healthy"}
```

### 3. Make Your First Request

```bash
# Create a conversation with the default agent
curl -N -X POST http://localhost:7001/api/v1/conversations \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello! What can you help me with?"}'
```

### 4. Use a Specific Agent

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

### Health Check

```
GET /health
```

Response: `{"status": "healthy"}`

### Conversations

#### Create Conversation (SSE Stream)

```
POST /api/v1/conversations
```

Creates a new conversation and streams the response.

**Request Body:**
```json
{
  "content": "Your message here",
  "agent_id": "general-agent-a1b2c3d4",
  "resume_session_id": null
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `content` | string | Yes | The user message |
| `agent_id` | string | No | Agent ID to use (defaults to `general-agent-a1b2c3d4`) |
| `resume_session_id` | string | No | Session ID to resume |

**Response:** Server-Sent Events stream (see [SSE Event Types](#sse-event-types))

#### Send Message (SSE Stream)

```
POST /api/v1/conversations/{session_id}/stream
```

Send a follow-up message to an existing conversation.

**Request Body:**
```json
{
  "content": "Follow-up message"
}
```

**Response:** Server-Sent Events stream

#### Send Message (Non-Streaming)

```
POST /api/v1/conversations/{session_id}/message
```

Send a message and receive the complete response (not streaming).

**Response:**
```json
{
  "session_id": "uuid-xxx",
  "response": "Complete response text",
  "tool_uses": [],
  "turn_count": 1,
  "messages": []
}
```

#### Interrupt Conversation

```
POST /api/v1/conversations/{session_id}/interrupt
```

Stop the current task execution.

**Response:**
```json
{
  "session_id": "uuid-xxx",
  "message": "Conversation interrupted successfully"
}
```

### Sessions

#### List Sessions

```
GET /api/v1/sessions
```

**Response:**
```json
{
  "active_sessions": [...],
  "history_sessions": [...]
}
```

#### Resume Session

```
POST /api/v1/sessions/{session_id}/resume
```

Resume a previous conversation session.

#### Close Session

```
DELETE /api/v1/sessions/{session_id}
```

### Configuration

#### List Skills

```
GET /api/v1/config/skills
```

**Response:**
```json
{
  "skills": [
    {"name": "code-analyzer", "description": "Analyze Python code for patterns and issues"},
    {"name": "doc-generator", "description": "Generate documentation for code"}
  ],
  "total": 3
}
```

#### List Agents

```
GET /api/v1/config/agents
```

See [Available Agents](#available-agents) for response format.

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

Agent definitions are stored in `agent/agents.yaml`. Each agent has a unique ID and specific capabilities.

### Adding a New Agent

1. Open `agent/agents.yaml`

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
```

### Provider Configuration

Edit `config.yaml` to switch between providers:

```yaml
provider: claude  # Options: claude, zai, minimax
```

Docker users can switch providers without rebuilding:
```bash
./switch-provider.sh zai      # Switch to Zai
./switch-provider.sh claude   # Switch to Claude
```

---

## Architecture

```
├── agent/                    # Core business logic
│   ├── agents.yaml          # Top-level agent definitions (agent_id configs)
│   ├── subagents.yaml       # Subagent definitions (delegation agents)
│   ├── core/
│   │   ├── agents.py        # TopLevelAgent loader (agents.yaml)
│   │   ├── subagents.py     # Subagent loader (subagents.yaml)
│   │   ├── agent_options.py # ClaudeAgentOptions builder
│   │   ├── session.py       # ConversationSession - main loop
│   │   ├── storage.py       # Session storage (data/sessions.json)
│   │   ├── config.py        # Provider configuration
│   │   └── hook.py          # Permission hooks for tool access
│   ├── discovery/
│   │   ├── skills.py        # Discovers skills from .claude/skills/
│   │   └── mcp.py           # Loads MCP servers from .mcp.json
│   └── display/             # Rich console output utilities
│
├── api/                      # FastAPI HTTP/SSE server
│   ├── main.py              # FastAPI app with lifespan management
│   ├── routers/
│   │   ├── health.py        # Health check
│   │   ├── sessions.py      # Session CRUD
│   │   ├── conversations.py # Message handling with SSE
│   │   └── configuration.py # Skills and agents listing
│   └── services/
│       ├── session_manager.py     # Session lifecycle management
│       └── conversation_service.py # Claude SDK interaction
│
├── cli/                      # Click-based CLI
│   ├── main.py              # CLI entry point
│   ├── clients/
│   │   ├── direct.py        # DirectClient - wraps SDK
│   │   └── api.py           # APIClient - HTTP/SSE client
│   └── commands/            # chat, serve, list commands
│
├── .claude/skills/           # Custom skills
├── config.yaml              # Provider configuration
└── data/sessions.json       # Persisted session history
```

### Data Flows

**API Mode Flow:**
```
Frontend → POST /api/v1/conversations
        → api/routers/conversations.py
        → api/services/conversation_service.py
        → ClaudeSDKClient (with agent config)
        → SSE Stream Response
```

**Direct Mode Flow:**
```
CLI → cli/clients/direct.py → claude_agent_sdk.ClaudeSDKClient
```

---

## CLI Commands

```bash
# Interactive chat
python main.py                        # Default mode
python main.py --mode direct          # Explicit direct mode
python main.py --mode api             # API mode (requires server)

# Start API server
python main.py serve                  # Default: 0.0.0.0:7001
python main.py serve --port 8080      # Custom port
python main.py serve --reload         # Auto-reload for development

# List resources
python main.py skills                 # List available skills
python main.py agents                 # List agents
python main.py sessions               # List conversation history

# Resume session
python main.py --session-id <id>      # Resume existing session
```

---

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

---

## Documentation

- [DOCKER.md](DOCKER.md) - Complete Docker deployment guide
- [CLAUDE.md](CLAUDE.md) - Claude Code instructions

---

## License

MIT
