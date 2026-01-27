# Claude Agent SDK Backend

FastAPI server with user authentication, WebSocket streaming, and per-user data isolation.

## Quick Start

```bash
uv sync && source .venv/bin/activate
cp .env.example .env   # Configure ANTHROPIC_API_KEY, API_KEY, CLI_PASSWORD
python main.py serve --port 7001
```

## Authentication

### Two-Layer Auth

1. **API Key** - For all REST endpoints (via `X-API-Key` header)
2. **User Login** - SQLite-based authentication returning JWT with `user_identity` type

### User Login Flow

```
POST /api/v1/auth/login
Headers: X-API-Key: your-api-key
Body: {"username": "admin", "password": "your-password"}

Response: {
  "success": true,
  "token": "jwt-with-user_identity-type...",
  "user": {"id": "...", "username": "admin", "role": "admin"}
}
```

### WebSocket Authentication

WebSocket requires JWT with `user_identity` type (includes username for per-user storage):

```
wss://host/api/v1/ws/chat?token=<jwt_with_username>&agent_id=xxx
```

### Default Users

Created automatically in `data/users.db`:

| Username | Role | Password Source |
|----------|------|-----------------|
| admin | admin | CLI_PASSWORD env var |
| tester | user | CLI_PASSWORD env var |

## API Endpoints

### Authentication

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/auth/login` | API Key | User login |
| POST | `/api/v1/auth/logout` | API Key | User logout |
| GET | `/api/v1/auth/me` | API Key + JWT | Current user info |

### Sessions (Per-User)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/v1/sessions` | API Key + User | List user's sessions |
| GET | `/api/v1/sessions/{id}/history` | API Key + User | Get session history |
| DELETE | `/api/v1/sessions/{id}` | API Key + User | Delete session |
| POST | `/api/v1/sessions/{id}/close` | API Key + User | Close session |
| POST | `/api/v1/sessions/{id}/resume` | API Key + User | Resume session |

### WebSocket

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| WS | `/api/v1/ws/chat` | JWT (user_identity) | WebSocket chat |

**Query Parameters:**
- `token` (required) - JWT with user_identity type
- `agent_id` (optional) - Agent to use
- `session_id` (optional) - Session to resume

### Configuration

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/health` | None | Health check |
| GET | `/api/v1/config/agents` | API Key | List agents |

## WebSocket Protocol

```
# Connection
Server → {"type": "ready"}

# User message
Client → {"content": "Hello!"}

# Streaming response
Server → {"type": "session_id", "session_id": "uuid"}
Server → {"type": "text_delta", "text": "Hi!"}
Server → {"type": "tool_use", "name": "Read", ...}
Server → {"type": "tool_result", "content": "..."}
Server → {"type": "done", "turn_count": 1}

# AskUserQuestion
Server → {"type": "ask_user_question", "question_id": "...", "questions": [...]}
Client → {"type": "user_answer", "question_id": "...", "answers": {...}}
Server → {"type": "question_answered", "question_id": "..."}
```

## CLI Commands

```bash
python main.py serve              # Start server (port 7001)
python main.py chat               # Interactive chat (prompts for password)
python main.py agents             # List agents
python main.py sessions           # List sessions
```

## Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...
API_KEY=your-api-key              # For REST auth + JWT derivation

# User credentials (for CLI and tests)
CLI_USERNAME=admin
CLI_PASSWORD=your-password        # No hardcoded default

# Optional
CORS_ORIGINS=https://your-frontend.com
API_HOST=0.0.0.0
API_PORT=7001
```

## Data Structure

```
data/
├── users.db              # SQLite user database
├── admin/                # Admin's data
│   ├── sessions.json
│   └── history/
│       └── {session_id}.jsonl
└── tester/               # Tester's data
    └── ...
```

## Testing

```bash
# Set CLI_PASSWORD in .env first
pytest tests/
```

## Docker

```bash
make build && make up
```
