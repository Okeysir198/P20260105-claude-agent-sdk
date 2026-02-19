# Email Integration Architecture

How the Claude Agent SDK connects to email providers (Gmail, Yahoo, Outlook, iCloud, Zoho, and custom IMAP servers) — giving agents the ability to read, search, send, and manage email.

---

## Overview

Email tools are integrated as an **MCP (Model Context Protocol) server** that runs inside the Claude Agent SDK process. The agent calls email tools the same way it calls Read, Write, or Bash — they appear as regular tool calls in the conversation.

```
User asks: "Check my unread emails"
  ↓
Claude Agent decides to call list_gmail tool
  ↓
MCP Server → Gmail API (OAuth) or IMAP Server (app password)
  ↓
Results returned to agent as tool_result
  ↓
Agent summarizes and responds to user
```

**Design principles:**

1. **MCP-native** — Email tools are registered as an MCP server, not custom SDK extensions
2. **Per-user credentials** — Each user's email credentials stored in isolated directories
3. **Multi-provider** — Gmail (OAuth), Yahoo, Outlook, iCloud, Zoho, and any custom IMAP server
4. **Two auth paths** — Gmail uses full OAuth 2.0; all other providers use app-specific passwords via IMAP
5. **Context-variable isolation** — Thread-safe username context ensures each request uses the correct credentials

---

## How Email Tools Reach the Agent

### Registration flow

```
1. Agent config (agents.yaml) includes email tools:
   tools:
     - mcp__email_tools__list_gmail
     - mcp__email_tools__read_gmail
     - ...

2. agent_options.py detects email tool references:
   → Adds email_tools MCP server to SDK options

3. SDK starts up:
   → Loads MCP server
   → Email tools available alongside Read, Write, Bash, etc.

4. Before each request:
   → Worker sets username context via set_email_tools_username()
   → All email tool calls use that user's credentials
```

### Username context (thread safety)

Email tools need to know which user's credentials to use. This is solved with Python's `contextvars`:

```python
# In mcp_server.py
_current_username: ContextVar[str | None] = ContextVar("email_username", default=None)

# Set before agent invocation (in worker.py or websocket.py)
set_email_tools_username("admin")

# Inside any email tool
username = get_username()  # Returns "admin"
credentials = load_credentials(username, "gmail")
```

This is thread-safe — concurrent requests for different users each see their own username.

---

## Two Authentication Paths

### Path 1: Gmail OAuth 2.0 (full access)

```
User clicks "Connect Gmail" in frontend
  ↓
Frontend redirects to Google OAuth consent screen
  ↓
User grants permissions (read-only or full access)
  ↓
Google redirects to /api/auth/callback/email/gmail with auth code
  ↓
Backend exchanges code for access_token + refresh_token
  ↓
Credentials stored in data/{username}/email_credentials/gmail.json
  ↓
Agent can now call Gmail API tools
```

**OAuth scopes:**

| Access Level | Scopes | Capabilities |
|-------------|--------|-------------|
| Read-only | `gmail.readonly` | List, search, read emails and attachments |
| Full access | `gmail.modify`, `gmail.send`, `gmail.compose` | Read + send, reply, draft, archive, star |

**Token refresh:** Access tokens expire after ~1 hour. The Gmail client auto-refreshes using the stored refresh_token and updates the credential file.

### Path 2: IMAP App Passwords (any provider)

```
User clicks "Connect Email" in frontend
  ↓
User enters: email address + app-specific password
  ↓
Backend auto-detects provider from domain:
  gmail.com → Gmail IMAP
  yahoo.com → Yahoo IMAP
  outlook.com → Outlook IMAP
  icloud.com → iCloud IMAP
  zoho.com → Zoho IMAP
  other → User provides IMAP server details
  ↓
Backend tests IMAP connection
  ↓
Credentials stored in data/{username}/email_credentials/{provider}.json
  ↓
Agent can now call IMAP tools
```

**IMAP server auto-detection:**

| Domain | IMAP Server | Port |
|--------|------------|------|
| gmail.com | imap.gmail.com | 993 |
| yahoo.com | imap.mail.yahoo.com | 993 |
| outlook.com / hotmail.com | outlook.office365.com | 993 |
| icloud.com | imap.mail.me.com | 993 |
| zoho.com | imap.zoho.com | 993 |
| Custom | User-provided | User-provided |

---

## Tool Catalog

### Discovery tools (call first)

| Tool | Purpose |
|------|---------|
| `list_email_accounts` | List all connected accounts with provider keys |
| `list_imap_folders` | List folders (Inbox, Sent, Drafts, etc.) |

### Gmail OAuth tools

| Tool | Access Level | Purpose |
|------|-------------|---------|
| `list_gmail` | Read | List emails (by label, query, count) |
| `search_gmail` | Read | Search with Gmail query syntax |
| `read_gmail` | Read | Read full email content |
| `download_gmail_attachments` | Read | Download file attachments |
| `send_gmail` | Full | Send new email |
| `reply_gmail` | Full | Reply to existing email |
| `create_gmail_draft` | Full | Create draft email |
| `modify_gmail_message` | Full | Mark read/unread, star, archive |

### IMAP tools (all providers)

| Tool | Purpose |
|------|---------|
| `list_imap_emails` | List emails in a folder |
| `search_imap_emails` | Search emails by query |
| `read_imap_email` | Read full email content |
| `download_imap_attachments` | Download file attachments |

### Agent workflow

The tools are designed to be called in sequence:

```
Step 1: list_email_accounts
        → Discover connected accounts and their provider keys
        → e.g., {"gmail": "user@gmail.com", "yahoo": "user@yahoo.com"}

Step 2: list_imap_folders (for IMAP providers)
        → Discover available folders
        → e.g., INBOX, Sent, Drafts, [Gmail]/Starred

Step 3: list_gmail or list_imap_emails
        → Get email summaries with message IDs
        → e.g., [{id: "msg123", subject: "Meeting notes", from: "alice@..."}]

Step 4: read_gmail or read_imap_email
        → Read full content of a specific email
        → Returns subject, from, to, date, body (text + HTML)

Step 5: download_gmail_attachments or download_imap_attachments
        → Download specific attachments to file storage
        → Saved to data/{username}/email_attachments/{provider}/{message_id}/
```

---

## Credential Storage

### Directory structure

```
data/{username}/email_credentials/
├── gmail.json                 # First Gmail account (OAuth)
├── gmail-work.json            # Second Gmail account (key includes local part)
├── yahoo.json                 # Yahoo (IMAP app password)
├── outlook.json               # Outlook (IMAP app password)
├── icloud.json                # iCloud (IMAP app password)
└── custom-myserver.json       # Custom IMAP server
```

### Credential key naming

- First account of a provider: `{provider}` (e.g., `gmail`)
- Additional accounts: `{provider}-{email_localpart}` (e.g., `gmail-work`)

### OAuth credential format (Gmail)

```json
{
  "provider": "gmail",
  "auth_type": "oauth",
  "email_address": "user@gmail.com",
  "access_token": "ya29.a0...",
  "refresh_token": "1//06...",
  "expires_at": "2026-02-19T12:00:00",
  "access_level": "full_access"
}
```

### App password credential format (IMAP)

```json
{
  "provider": "yahoo",
  "auth_type": "app_password",
  "email_address": "user@yahoo.com",
  "app_password": "abcd efgh ijkl mnop",
  "imap_server": "imap.mail.yahoo.com",
  "imap_port": 993,
  "smtp_server": "smtp.mail.yahoo.com",
  "smtp_port": 587
}
```

---

## Attachment Storage

Downloaded email attachments are stored per-user, per-provider, per-message:

```
data/{username}/email_attachments/
└── gmail/
    └── msg_abc123/
        ├── report.pdf
        └── photo.jpg
```

The agent receives the file path in the tool result and can then use the Read tool to access file contents.

### PDF auto-decryption (admin only)

If a PDF attachment is password-protected:
1. The system checks `PDF_PASSWORD_*` env vars
2. If a matching password is found, the PDF is decrypted automatically
3. The decrypted version replaces the original in storage

---

## Environment Variable Auto-Seeding

For the admin user, email accounts can be pre-configured via environment variables (no UI interaction needed):

```bash
# Account 1
EMAIL_ACCOUNT_1_EMAIL=user@gmail.com
EMAIL_ACCOUNT_1_PASSWORD=app-specific-password
# EMAIL_ACCOUNT_1_IMAP_SERVER=...    # Optional (auto-detected from domain)
# EMAIL_ACCOUNT_1_IMAP_PORT=993      # Optional (default: 993)

# Account 2
EMAIL_ACCOUNT_2_EMAIL=user@yahoo.com
EMAIL_ACCOUNT_2_PASSWORD=another-app-password
```

**Behavior:**
- Only runs for the admin user at startup
- Tests IMAP connection before saving
- Skips if credentials already exist (non-destructive)
- Supports unlimited accounts (EMAIL_ACCOUNT_N_*)

---

## Connection from Different Entry Points

Email tools work identically regardless of how the user connects:

| Entry Point | How username is set | Email tool behavior |
|-------------|--------------------|--------------------|
| **Web UI** (WebSocket) | JWT token → username claim | `set_email_tools_username()` in websocket.py |
| **WhatsApp/Telegram** | Platform identity mapping | `set_email_tools_username()` in worker.py |
| **CLI** | Login prompt → username | `set_email_tools_username()` in CLI client |
| **SSE API** | JWT token → username claim | `set_email_tools_username()` in conversations.py |

The email tools themselves are unaware of the entry point — they only see the username context variable.

---

## Security

### Credential isolation

- Each user's credentials stored in `data/{username}/email_credentials/`
- No user can access another user's email credentials
- Username derived from JWT token (web) or platform identity mapping (platforms)

### Token handling

- OAuth tokens refreshed automatically before expiry
- App passwords stored in plaintext (same security model as `.env` files)
- Credentials never included in agent responses to users (redacted by sensitive data filter)
- Credentials never logged

### OAuth state protection

- CSRF state tokens generated per OAuth flow
- In-memory store with 10-minute TTL
- State validated on callback to prevent injection

### Sensitive data redaction

The `sensitive_data_filter` automatically redacts email credentials from:
- WebSocket messages sent to frontend
- Log output
- Tool results displayed to users

Patterns redacted: OAuth tokens, app passwords, IMAP connection strings, Bearer tokens.

---

## Architecture Reference

| Component | File | Purpose |
|-----------|------|---------|
| MCP server | `agent/tools/email/mcp_server.py` | Tool registration + username context |
| Gmail client | `agent/tools/email/gmail_tools.py` | Gmail API operations (OAuth) |
| IMAP client | `agent/tools/email/imap_client.py` | Universal IMAP operations |
| Credential store | `agent/tools/email/credential_store.py` | Per-user credential management |
| Attachment store | `agent/tools/email/attachment_store.py` | Downloaded attachment storage |
| PDF decrypt | `agent/tools/email/pdf_decrypt.py` | PDF password decryption |
| SDK options | `agent/core/agent_options.py` | MCP server registration in SDK |
| OAuth router | `api/routers/email_auth.py` | Gmail OAuth + IMAP connect endpoints |
| Frontend profile | `frontend/app/(auth)/profile/page.tsx` | Email account management UI |

---

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `EMAIL_GMAIL_CLIENT_ID` | For Gmail OAuth | Google OAuth client ID |
| `EMAIL_GMAIL_CLIENT_SECRET` | For Gmail OAuth | Google OAuth client secret |
| `EMAIL_GMAIL_REDIRECT_URI` | For Gmail OAuth | OAuth callback URL |
| `EMAIL_FRONTEND_URL` | For Gmail OAuth | Frontend URL for post-OAuth redirect |
| `EMAIL_ACCOUNT_N_EMAIL` | No | Auto-seed email address (admin only) |
| `EMAIL_ACCOUNT_N_PASSWORD` | No | Auto-seed app password (admin only) |
| `EMAIL_ACCOUNT_N_IMAP_SERVER` | No | Override IMAP server (auto-detected) |
| `EMAIL_ACCOUNT_N_IMAP_PORT` | No | Override IMAP port (default: 993) |
| `PDF_PASSWORD_DEFAULT` | No | Default PDF decryption password |
