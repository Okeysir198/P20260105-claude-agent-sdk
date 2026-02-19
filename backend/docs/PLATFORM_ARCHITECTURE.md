# Platform Integration Architecture

How the Claude Agent SDK connects to messaging platforms (WhatsApp, Telegram, Zalo, iMessage) — using WhatsApp as the primary example.

---

## Overview

The platform integration follows a **webhook-based adapter pattern**. Each messaging platform sends events to webhook endpoints on the backend. A shared worker processes them through the Claude Agent SDK and streams responses back incrementally.

```
Platform User  →  Platform API  →  Webhook  →  Backend Worker  →  Claude Agent SDK
               ←  Platform API  ←  Adapter  ←  Backend Worker  ←  Claude Agent SDK
```

**Design principles:**

1. **Adapter pattern** — Platform-specific logic isolated in adapters; the worker is platform-agnostic
2. **Webhook-first** — All platforms push events via HTTP webhooks; the backend never polls
3. **Incremental delivery** — Agent events (text, tool use, tool results) sent as separate messages so users can follow along in real-time
4. **Per-user data isolation** — Each platform user maps to an internal username with isolated storage
5. **Background processing** — Webhooks ACK immediately (200 OK); actual processing happens asynchronously

---

## Data Flow: Incoming Message to Agent Response

### Step-by-step (WhatsApp example)

```
1. User sends "Summarize this PDF" via WhatsApp
   ↓
2. WhatsApp Cloud API posts webhook to:
   POST /api/v1/webhooks/whatsapp
   ↓
3. Webhook router:
   a. Verify HMAC-SHA256 signature (X-Hub-Signature-256 header)
   b. Parse JSON payload → NormalizedMessage
   c. Deduplicate (in-memory, 1-hour TTL)
   d. Return {"status": "ok"} immediately
   e. Queue background task
   ↓
4. Background worker (process_platform_message):
   a. Send typing indicator
   b. Resolve identity: platform_user_id → internal username
   c. Look up or create session via session bridge
   d. Download media attachments (if any)
   e. Create ClaudeSDKClient with agent options
   f. Send user message to agent
   ↓
5. Stream agent response:
   a. Text chunks → accumulate, format markdown for WhatsApp, send
   b. Tool use → flush pending text, format tool info, send
   c. Tool result → format result preview, send
   d. Files created → deliver directly (<10MB) or via download link
   ↓
6. Finalize:
   a. Save message history (JSONL)
   b. Update session turn count
   c. Persist session mapping
```

---

## Core Abstractions

### NormalizedMessage (inbound)

Platform-agnostic representation of an incoming message:

```python
@dataclass
class NormalizedMessage:
    platform: Platform          # WHATSAPP, TELEGRAM, ZALO, IMESSAGE
    platform_user_id: str       # Platform-specific user ID
    platform_chat_id: str       # Platform-specific chat/conversation ID
    text: str                   # Message text content
    media: list[MediaItem]      # Attached media (photos, documents, voice)
    metadata: dict              # Platform-specific metadata (timestamp, message_id)
```

### NormalizedResponse (outbound)

```python
@dataclass
class NormalizedResponse:
    text: str                   # Response message text
    media: list[dict]           # Media to send back (optional)
```

### PlatformAdapter (interface)

Every platform adapter implements:

| Method | Purpose |
|--------|---------|
| `parse_inbound(payload)` | Parse webhook payload → NormalizedMessage |
| `verify_signature(body, headers)` | Verify webhook authenticity |
| `send_response(chat_id, response)` | Send text message back |
| `send_typing_indicator(chat_id)` | Show "typing..." status |
| `send_file(chat_id, path, name, mime)` | Send a file directly |
| `get_media_download_kwargs()` | Platform-specific download params |

---

## Adapter Pattern: WhatsApp Example

The WhatsApp adapter (`platforms/adapters/whatsapp.py`) implements the full `PlatformAdapter` interface:

### Signature Verification

```python
# HMAC-SHA256 verification using WHATSAPP_APP_SECRET
expected = hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
actual = headers["x-hub-signature-256"].removeprefix("sha256=")
return hmac.compare_digest(expected, actual)
```

### Markdown Conversion

WhatsApp uses its own formatting syntax. The adapter converts:

| Claude Markdown | WhatsApp Format |
|----------------|-----------------|
| `**bold**` | `*bold*` |
| `## Header` | `*Header*` |
| `[text](url)` | `text (url)` |
| `~~strike~~` | `~strike~` |

### Message Splitting

WhatsApp enforces a 4096-character limit. The adapter splits long messages intelligently on paragraph → line → word boundaries using `split_message()` from the base class.

### File Sending

Two-step process via WhatsApp Cloud API:
1. Upload file to WhatsApp media endpoint → get media_id
2. Send message referencing media_id with correct type (image/video/audio/document)

---

## Identity Mapping

**File:** `platforms/identity.py`

Maps platform user IDs to internal application usernames for data isolation.

### Two strategies

1. **Explicit mapping** (env var):
   ```bash
   PLATFORM_USER_MAP_WHATSAPP_84907996550=admin
   ```
   Routes this WhatsApp number to the `admin` user's data directory.

2. **Deterministic hash** (fallback):
   ```
   whatsapp_84907996550 → whatsapp_a7f8c2d1
   ```
   SHA-256 hash of platform + user_id, truncated to 8 chars. Consistent across restarts.

### Data isolation guarantee

Each username has an isolated directory:
```
data/{username}/
├── sessions.json              # Session metadata
├── platform_sessions.json     # Platform chat → session mappings
├── history/{session_id}.jsonl  # Conversation history
└── files/{cwd_id}/            # Session files (input/output)
```

---

## Session Bridge

**File:** `platforms/session_bridge.py`

Maps platform chat IDs to internal session IDs for multi-turn conversations.

### How it works

```
WhatsApp chat 84907996550
    ↕ (session_bridge)
Internal session abc-123-def
    ↕ (session_storage)
Claude Agent SDK session
```

### Session lifecycle

1. **First message**: No mapping exists → create new session → save mapping
2. **Subsequent messages**: Look up mapping → resume session with full history
3. **Session expired** (> 24h by default): Clear mapping → create fresh session → notify user
4. **User says "new session"**: Clear mapping → confirm → next message starts fresh

### Expiry

Configured via `PLATFORM_SESSION_MAX_AGE_HOURS` (default: 24). When a session expires, the user sees:

```
━━━━━━━━━━━━━━━━━━━━
🔄 New session started

Previous conversation exceeded the time limit and has been archived.
I won't remember what we discussed before, but feel free to bring me up to speed!
━━━━━━━━━━━━━━━━━━━━
```

---

## Media Processing

**File:** `platforms/media.py`

Handles incoming media from platforms — images go to Claude as vision content, other files go to the agent's file storage.

### Processing pipeline

```
Incoming media item
  ↓
Download from platform API
  ├─ Telegram: file_id → getFile API → HTTP download
  ├─ WhatsApp: media_id → media URL → HTTP download (with auth header)
  └─ iMessage: attachment_guid → BlueBubbles API download
  ↓
Classify by MIME type
  ├─ Image (jpeg, png, gif, webp)
  │   → Base64 encode → content block for Claude vision
  │   → Claude can "see" the image and reason about it
  └─ Other (PDF, documents, audio, code files)
      → Save to FileStorage (data/{user}/files/{cwd}/input/)
      → Add text annotation: "[File received: report.pdf — saved to input/abc_report.pdf]"
      → Agent can read the file using the Read tool
```

### Size limits

- Individual file: 50MB max
- Images: auto-converted to base64 for Claude vision
- Documents: saved to disk, referenced in message

---

## Incremental Event Delivery

Unlike the web UI which streams text character-by-character, platform messages must be sent as discrete messages. The worker converts agent events into a series of platform messages:

| Agent Event | Platform Message |
|-------------|-----------------|
| Text chunks | Accumulated, then sent as one message when a tool event occurs or response ends |
| Tool use (Read) | `📖 *Reading file*\n\`src/main.py\`` |
| Tool use (Bash) | `⚡ *Running command*\n\`\`\`npm test\`\`\`` |
| Tool result (success) | `✅ *Read* — ~2.5K chars` |
| Tool result (error) | `❌ *Bash failed*\n\`\`\`Error: ...\`\`\`` |
| File created | Direct file send (<10MB) or download link |

### Rate limiting

Messages are sent with a 0.3-second delay between them to avoid platform rate limits. A typing indicator is refreshed after each send.

---

## File Delivery

**File:** `platforms/worker.py` → `_deliver_file_to_platform()`

When the agent creates files using the Write tool, they are delivered to the platform user:

| Condition | Behavior |
|-----------|----------|
| File < 10MB, platform supports files | Send directly via platform API |
| File >= 10MB | Generate signed download URL (24h expiry) |
| Direct send fails | Fall back to signed download URL |
| Platform doesn't support files (Zalo) | Always send download URL |

Download URLs use HMAC-signed tokens scoped to the specific file, username, and session. No authentication needed — the token IS the credential.

---

## Webhook Deduplication

**File:** `api/routers/webhooks.py`

Platforms sometimes deliver the same webhook multiple times (retries, network issues). The router deduplicates using:

- In-memory dict: `{platform}:{message_id}` → timestamp
- TTL: 1 hour
- Auto-evicts stale entries when dict exceeds 10,000 entries
- Thread-safe via `asyncio.Lock`

---

## Adding a New Platform

To add a new messaging platform:

1. **Create adapter** in `platforms/adapters/{platform}.py`:
   - Implement `PlatformAdapter` interface
   - Handle signature verification, message parsing, response sending

2. **Register adapter** in `platforms/adapters/__init__.py`:
   - Add to platform registry, gated on an env var

3. **Add webhook route** in `api/routers/webhooks.py`:
   - The generic handler already supports any registered adapter
   - Add platform-specific verification endpoint if needed

4. **Add identity mapping** in `platforms/identity.py`:
   - Add `PLATFORM_USER_MAP_{PLATFORM}_*` env var support

5. **Add media download** in `platforms/media.py` (optional):
   - Implement platform-specific file download function

No changes needed in `worker.py` — it operates on `NormalizedMessage` and `PlatformAdapter` abstractions.

---

## Architecture Reference

| Component | File | Purpose |
|-----------|------|---------|
| Base interface | `platforms/base.py` | NormalizedMessage, PlatformAdapter ABC |
| WhatsApp adapter | `platforms/adapters/whatsapp.py` | WhatsApp Cloud API integration |
| Telegram adapter | `platforms/adapters/telegram.py` | Telegram Bot API integration |
| Zalo adapter | `platforms/adapters/zalo.py` | Zalo OA API integration |
| iMessage adapter | `platforms/adapters/imessage.py` | BlueBubbles bridge |
| Adapter registry | `platforms/adapters/__init__.py` | Auto-register based on env vars |
| Webhook router | `api/routers/webhooks.py` | HTTP endpoints + deduplication |
| Message worker | `platforms/worker.py` | Main processing pipeline |
| Session bridge | `platforms/session_bridge.py` | Platform chat ↔ app session mapping |
| Identity mapping | `platforms/identity.py` | Platform user ↔ app username |
| Media processing | `platforms/media.py` | Download + classify media |
| Event formatter | `platforms/event_formatter.py` | Format tool events for platforms |
| Download tokens | `api/services/file_download_token.py` | Signed file download URLs |

---

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `PLATFORM_DEFAULT_AGENT_ID` | No | Default agent for all platform messages |
| `PLATFORM_SESSION_MAX_AGE_HOURS` | No | Session expiry (default: 24h) |
| `PLATFORM_USER_MAP_{PLATFORM}_{ID}` | No | Explicit user identity mapping |
| `BACKEND_PUBLIC_URL` | No | Base URL for download links |
| `WHATSAPP_PHONE_NUMBER_ID` | Per platform | WhatsApp phone number ID |
| `WHATSAPP_ACCESS_TOKEN` | Per platform | WhatsApp Cloud API token |
| `WHATSAPP_VERIFY_TOKEN` | Per platform | Webhook verification shared secret |
| `WHATSAPP_APP_SECRET` | No | HMAC signature verification |
| `TELEGRAM_BOT_TOKEN` | Per platform | Telegram bot token |
| `TELEGRAM_WEBHOOK_SECRET` | No | Webhook signature verification |
| `ZALO_OA_ACCESS_TOKEN` | Per platform | Zalo OA access token |
| `BLUEBUBBLES_PASSWORD` | Per platform | iMessage server password |
