# Email Integration

This module provides Gmail and Yahoo Mail integration for the Claude Agent SDK, enabling AI agents to read emails and download attachments.

## Features

- **Gmail**: OAuth 2.0 authentication, list/read/search emails, download attachments
- **Yahoo Mail**: App password authentication via IMAP, list/read emails, download attachments
- **Per-user credential storage**: Encrypted OAuth tokens stored per-user
- **Attachment storage**: Downloaded files saved to per-user directories

## Installation

Install the email dependencies:

```bash
cd backend
pip install -e ".[email]"
```

Or install manually:

```bash
pip install google-api-python-client google-auth-oauthlib imap-tools
```

## Environment Variables

### Gmail OAuth

```bash
# Required for Gmail integration
EMAIL_GMAIL_CLIENT_ID=your-gmail-oauth-client-id
EMAIL_GMAIL_CLIENT_SECRET=your-gmail-oauth-client-secret
EMAIL_GMAIL_REDIRECT_URI=http://localhost:7001/api/v1/email/gmail/callback

# Optional: Frontend URL for OAuth redirects
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

### Yahoo Mail

Yahoo Mail uses app-specific passwords for IMAP access. No OAuth setup required.

Users generate app passwords at: https://login.yahoo.com/account/security

## Usage

### Agent Configuration

Add to `backend/agents.yaml`:

```yaml
email-reader-x1y2z3:
  name: "Email Reader"
  description: "Read emails and download attachments from Gmail and Yahoo"
  tools:
    - mcp__email_tools__list_gmail
    - mcp__email_tools__read_gmail
    - mcp__email_tools__search_gmail
    - mcp__email_tools__download_gmail_attachments
    - mcp__email_tools__list_yahoo
    - mcp__email_tools__read_yahoo
    - mcp__email_tools__download_yahoo_attachments
  mcp_servers:
    email_tools:
      # Auto-registered when tools are used
```

### Frontend Integration

The profile page at `/profile` allows users to:
- View connected email accounts
- Connect Gmail via OAuth
- Connect Yahoo Mail with app password
- Disconnect accounts

### API Endpoints

#### Email Status
```
GET /api/v1/email/status
```
Returns connection status for current user.

#### Gmail Auth
```
GET /api/v1/email/gmail/auth-url
GET /api/v1/email/gmail/callback?code=...&state=...
POST /api/v1/email/gmail/disconnect
```

#### Yahoo Auth
```
POST /api/v1/email/yahoo/connect
POST /api/v1/email/yahoo/disconnect
```

## Storage

### Credentials
Path: `backend/data/{username}/email_credentials/`

- `gmail.json` - Gmail OAuth tokens
- `yahoo.json` - Yahoo app password

### Attachments
Path: `backend/data/{username}/email_attachments/{provider}/{message_id}/{filename}`

Example: `backend/data/admin/email_attachments/gmail/123456789/document.pdf`

## Tools Reference

### Gmail Tools

#### `list_gmail`
List Gmail emails with optional filters.

Input:
```json
{
  "max_results": 10,
  "query": "from:john@example.com",
  "label": "INBOX"
}
```

#### `read_gmail`
Read full email content.

Input:
```json
{
  "message_id": "123456789"
}
```

#### `search_gmail`
Search emails by query.

Input:
```json
{
  "query": "subject:invoice has:attachment",
  "max_results": 10
}
```

#### `download_gmail_attachments`
Download attachments from an email.

Input:
```json
{
  "message_id": "123456789",
  "attachment_ids": ["att1", "att2"]
}
```

### Yahoo Tools

#### `list_yahoo`
List Yahoo emails from a folder.

Input:
```json
{
  "max_results": 10,
  "folder": "INBOX"
}
```

#### `read_yahoo`
Read full Yahoo email.

Input:
```json
{
  "message_id": "12345",
  "folder": "INBOX"
}
```

#### `download_yahoo_attachments`
Download Yahoo email attachments.

Input:
```json
{
  "message_id": "12345",
  "filenames": ["document.pdf"]
}
```

## Security

- OAuth tokens stored per-user in separate directories
- Credentials never shared between users
- Access tokens expire and are refreshed automatically
- App passwords for Yahoo are never logged

## Troubleshooting

### Gmail not connecting
- Verify CLIENT_ID and CLIENT_SECRET are correct
- Check redirect URI matches exactly
- Ensure Gmail API is enabled in Google Cloud Console

### Yahoo connection fails
- Verify app password is generated correctly
- Check email address format
- Ensure IMAP is enabled for Yahoo account

### Tools not available
- Install email dependencies: `pip install -e ".[email]"`
- Check agent configuration includes `mcp__email_tools__*` tools
- Verify MCP server is registered (check logs for "Registered email_tools MCP server")
