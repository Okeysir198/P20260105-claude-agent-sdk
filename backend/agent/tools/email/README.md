# Email Integration

This module provides email integration for the Claude Agent SDK, enabling AI agents to read emails and download attachments from Gmail and any IMAP-compatible provider (Yahoo, Outlook, iCloud, Zoho, custom).

## Features

- **Gmail**: OAuth 2.0 authentication, list/read/search emails, download attachments
- **Universal IMAP**: App password authentication for Yahoo, Outlook, iCloud, Zoho, and custom IMAP servers
- **Multi-account support**: Multiple accounts per provider (e.g., two Gmail accounts)
- **Per-user credential storage**: OAuth tokens and app passwords stored per-user
- **Attachment storage**: Downloaded files saved to per-user directories
- **PDF decryption**: Automatic password-protected PDF decryption for bank statements
- **Dual connection paths**: Env-var auto-seeding at startup + UI manual connection at runtime

## Architecture

```
agent/tools/email/
├── gmail_tools.py          # Gmail API client + MCP tool implementations
├── imap_client.py          # Universal IMAP client for any provider
├── mcp_server.py           # MCP server registration (contextvars for thread safety)
├── credential_store.py     # Per-user OAuth/app-password storage + env-var seeding
├── attachment_store.py     # Downloaded email attachment storage + PDF decryption
└── pdf_decrypt.py          # PDF password decryption utility (bank statements)
```

## Installation

Install the email dependencies:

```bash
cd backend
pip install -e ".[email]"
```

## Connection Paths

### Path 1: Env-Var Auto-Seed (startup)

Pre-configure email accounts in `backend/.env`. They are auto-connected when the backend starts. Credentials are only written if they don't already exist (won't overwrite UI-modified accounts).

```bash
# Format: EMAIL_ACCOUNT_N_EMAIL, EMAIL_ACCOUNT_N_PASSWORD
# Optional: EMAIL_ACCOUNT_N_USERNAME (defaults to "admin")
# Optional: EMAIL_ACCOUNT_N_IMAP_SERVER, EMAIL_ACCOUNT_N_IMAP_PORT

EMAIL_ACCOUNT_1_EMAIL=user@gmail.com
EMAIL_ACCOUNT_1_PASSWORD=app-specific-password

EMAIL_ACCOUNT_2_EMAIL=user@yahoo.com
EMAIL_ACCOUNT_2_PASSWORD=yahoo-app-password

EMAIL_ACCOUNT_3_EMAIL=another@gmail.com
EMAIL_ACCOUNT_3_PASSWORD=another-app-password
```

- Provider is auto-detected from the email domain
- IMAP connection is tested before saving credentials
- Multiple accounts of the same provider get unique keys (e.g., `gmail`, `gmail-another`)
- On restart, existing accounts are skipped (no overwrite)

### Path 2: UI Manual (runtime)

Users connect/disconnect accounts via the Profile page (`/profile`):

- **Gmail**: OAuth flow via `GET /api/v1/email/gmail/auth-url`
- **IMAP providers**: App password via `POST /api/v1/email/imap/connect`

Both paths write to the same credential store.

## Environment Variables

### Gmail OAuth

```bash
EMAIL_GMAIL_CLIENT_ID=your-gmail-oauth-client-id
EMAIL_GMAIL_CLIENT_SECRET=your-gmail-oauth-client-secret
EMAIL_GMAIL_REDIRECT_URI=http://localhost:7001/api/v1/email/gmail/callback
EMAIL_FRONTEND_URL=http://localhost:7002
```

### Setting up Gmail OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Gmail API
4. Create OAuth 2.0 credentials:
   - Application type: Web application
   - Authorized redirect URI: `http://localhost:7001/api/v1/email/gmail/callback`
   - For production, use your actual domain
5. Copy Client ID and Client Secret to environment variables

### IMAP Providers (Yahoo, Outlook, iCloud, Zoho)

IMAP providers use app-specific passwords. No OAuth setup required.

- **Yahoo**: Generate at https://login.yahoo.com/account/security
- **Outlook**: Generate at https://account.microsoft.com/security
- **iCloud**: Generate at https://appleid.apple.com/account/manage
- **Gmail (IMAP fallback)**: Generate at https://myaccount.google.com/apppasswords

## API Endpoints

### Accounts

```
GET  /api/v1/email/accounts          # List all connected accounts
GET  /api/v1/email/status            # Connection status (legacy compat)
GET  /api/v1/email/providers         # List available providers
```

### Gmail OAuth

```
GET  /api/v1/email/gmail/auth-url    # Get OAuth authorization URL
GET  /api/v1/email/gmail/callback    # OAuth callback (handles token exchange)
POST /api/v1/email/gmail/disconnect  # Disconnect Gmail
```

### Universal IMAP

```
POST /api/v1/email/imap/connect      # Connect IMAP account (tests connection first)
POST /api/v1/email/imap/disconnect   # Disconnect IMAP account
```

### Yahoo (backward-compatible, delegates to IMAP)

```
POST /api/v1/email/yahoo/connect     # Connect Yahoo (delegates to /imap/connect)
POST /api/v1/email/yahoo/disconnect  # Disconnect Yahoo (delegates to /imap/disconnect)
```

## MCP Tools Reference

All tools are registered in `mcp_server.py` as `email_tools` MCP server.

### Gmail Tools

| Tool | Description |
|------|-------------|
| `list_gmail` | List Gmail emails with optional query/label filters |
| `read_gmail` | Read full email content by message ID |
| `search_gmail` | Search emails using Gmail search operators |
| `download_gmail_attachments` | Download attachments by message ID |

### IMAP Tools (all providers)

| Tool | Description |
|------|-------------|
| `list_imap_emails` | List emails from an IMAP account by provider key |
| `read_imap_email` | Read full email by provider key + message ID |
| `search_imap_emails` | Search emails with `subject:`, `from:`, `since:` prefixes |
| `download_imap_attachments` | Download attachments by provider key + message ID |
| `list_imap_folders` | List available IMAP folders |
| `list_email_accounts` | List all connected email accounts (Gmail + IMAP) |

### Provider Key

The `provider` parameter in IMAP tools is the credential key, which matches the credential filename (without `.json`):
- Single account: `yahoo`, `outlook`, `gmail` (for IMAP fallback)
- Multiple accounts of same provider: `gmail-nthanhtrung198`, `gmail-another`

Use `list_email_accounts` to discover available provider keys.

## Storage

### Credentials

Path: `backend/data/{username}/email_credentials/`

- `gmail.json` - Gmail OAuth tokens (or IMAP app password)
- `yahoo.json` - Yahoo app password
- `gmail-nthanhtrung198.json` - Additional Gmail account (multi-account)
- `outlook.json` - Outlook app password

### Attachments

Path: `backend/data/{username}/email_attachments/{provider}/{message_id}/{filename}`

Example: `backend/data/admin/email_attachments/gmail/123456789/document.pdf`

## Security

- OAuth tokens and app passwords stored per-user in separate directories
- Credentials never shared between users
- Gmail access tokens expire and are refreshed automatically
- App passwords are never logged
- IMAP connection is tested before saving credentials (both env-var and UI paths)

## Troubleshooting

### Gmail OAuth not connecting

- Verify CLIENT_ID and CLIENT_SECRET are correct
- Check redirect URI matches exactly
- Ensure Gmail API is enabled in Google Cloud Console

### IMAP connection fails

- Verify app password is generated correctly (not your regular password)
- Check email address format
- Ensure IMAP access is enabled for the account
- For Gmail IMAP: enable "Less secure app access" or use app-specific password

### Env-var accounts not seeding

- Check backend startup logs for IMAP connection test results
- Verify `EMAIL_ACCOUNT_N_EMAIL` and `EMAIL_ACCOUNT_N_PASSWORD` are set
- For custom providers, `EMAIL_ACCOUNT_N_IMAP_SERVER` is required
- Accounts are skipped if credential file already exists

### Tools not available

- Install email dependencies: `pip install -e ".[email]"`
- Verify MCP server is registered (check logs for "Registered email_tools MCP server")

### PDF attachments not opening

- For password-protected PDFs, configure `PDF_PASSWORD_*` environment variables
- Check that `pypdf` is installed: `pip install pypdf`
- Verify passwords are correct for the specific bank statement type
