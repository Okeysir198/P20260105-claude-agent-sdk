# Email Integration Testing Guide

This guide provides comprehensive testing procedures for both Gmail OAuth and IMAP email integration in the Claude Agent SDK.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Gmail OAuth Testing](#gmail-oauth-testing)
4. [IMAP Connection Testing](#imap-connection-testing)
5. [Testing Email Tools](#testing-email-tools)
6. [Common Issues and Troubleshooting](#common-issues-and-troubleshooting)
7. [Success Criteria Checklist](#success-criteria-checklist)
8. [Expected Behaviors and Log Outputs](#expected-behaviors-and-log-outputs)

---

## Overview

The email integration supports two authentication methods:

- **Gmail OAuth**: OAuth 2.0 flow for secure, token-based authentication
- **Universal IMAP**: App password authentication for Yahoo, Outlook, iCloud, Zoho, and custom IMAP servers

Both methods enable AI agents to:
- List and read emails
- Search emails by subject, sender, date
- Download attachments (with automatic PDF decryption for bank statements)

---

## Prerequisites

### Backend Setup

1. **Backend server running**:
   ```bash
   cd backend
   source .venv/bin/activate
   python main.py serve --port 7001
   ```

2. **Email dependencies installed**:
   ```bash
   pip install -e ".[email]"
   ```

3. **Environment variables configured** (for Gmail OAuth):
   ```bash
   # Required for Gmail OAuth
   EMAIL_GMAIL_CLIENT_ID=your-gmail-oauth-client-id
   EMAIL_GMAIL_CLIENT_SECRET=your-gmail-oauth-client-secret
   EMAIL_GMAIL_REDIRECT_URI=http://localhost:7001/api/v1/email/gmail/callback
   EMAIL_FRONTEND_URL=http://localhost:7002
   ```

### Frontend Setup

1. **Frontend accessible**:
   ```bash
   cd frontend
   npm run dev
   # Access at http://localhost:7002
   ```

2. **User logged in**:
   - Navigate to `http://localhost:7002/login`
   - Login with test credentials (e.g., admin account)

---

## Gmail OAuth Testing

### 1. Environment Verification

Before testing, verify your Gmail OAuth setup:

**Check environment variables**:
```bash
cd backend
source .venv/bin/activate
python -c "from core.settings import get_settings; s = get_settings(); print(f'Client ID: {s.email.gmail_client_id[:20]}...' if s.email.gmail_client_id else 'MISSING'); print(f'Client Secret: {s.email.gmail_client_secret[:20]}...' if s.email.gmail_client_secret else 'MISSING'); print(f'Redirect URI: {s.email.gmail_redirect_uri}')"
```

Expected output:
```
Client ID: 123456789-abcdefg...
Client Secret: GOCSPX-abc123...
Redirect URI: http://localhost:7001/api/v1/email/gmail/callback
```

**Verify Google Cloud Console setup**:
- Gmail API is enabled
- OAuth 2.0 client credentials created
- Authorized redirect URI matches exactly: `http://localhost:7001/api/v1/email/gmail/callback`

### 2. Step-by-Step OAuth Flow Test

Follow these steps to test the complete OAuth flow:

#### Step 1: Navigate to Profile Page

1. Login to the application at `http://localhost:7002/login`
2. Navigate to the Profile page at `http://localhost:7002/profile`

**Expected**: Profile page loads with "Email Integration" header

#### Step 2: Initiate Gmail OAuth

1. Click the "Connect Gmail" button
2. Observe the browser console and network tab

**Expected behavior**:
- Frontend calls `GET /api/proxy/email/gmail/auth-url`
- Backend generates OAuth URL with CSRF-protected state token
- Browser redirects to Google OAuth consent screen

**Backend logs**:
```
INFO:     127.0.0.1:xxxx - "GET /api/v1/email/gmail/auth-url HTTP/1.1" 200 OK
```

**Network response**:
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=...&redirect_uri=...&response_type=code&scope=https://www.googleapis.com/auth/gmail.readonly&state=...&access_type=offline&prompt=consent",
  "provider": "gmail"
}
```

#### Step 3: Authorize on Google

1. On the Google OAuth screen, select your Google account
2. Review permissions (Read-only access to Gmail)
3. Click "Allow"

**Expected**: Browser redirects back to backend callback URL

#### Step 4: OAuth Callback Processing

After authorization, Google redirects to: `http://localhost:7001/api/v1/email/gmail/callback?code=...&state=...`

**Backend processing**:
1. Validates OAuth state token (CSRF protection)
2. Exchanges authorization code for access token
3. Fetches user email address
4. Stores OAuth credentials in `data/{username}/email_credentials/gmail.json`
5. Redirects to frontend: `http://localhost:7002/profile?email=gmail&status=connected`

**Backend logs**:
```
INFO:     127.0.0.1:xxxx - "GET /api/v1/email/gmail/callback?code=...&state=... HTTP/1.1" 302 Temporary Redirect
INFO:     Successfully connected Gmail for user admin (user@gmail.com)
```

**Credential file created**:
```json
{
  "provider": "gmail",
  "auth_type": "oauth",
  "email_address": "user@gmail.com",
  "access_token": "ya29.a0AfH6SMBx...",
  "refresh_token": "1//0gabc123...",
  "token_type": "Bearer",
  "expires_at": "2026-02-18T12:34:56.789123",
  "imap_server": "imap.gmail.com",
  "imap_port": 993,
  "smtp_server": "smtp.gmail.com",
  "smtp_port": 587
}
```

#### Step 5: Verify Connection

1. Frontend detects `?email=gmail&status=connected` query params
2. Automatically refreshes email status
3. Profile page updates to show connected account

**Expected UI**:
- "Connected Accounts" section shows:
  - Gmail badge with green checkmark
  - Email address: `user@gmail.com`
  - Disconnect button

**API call**:
```
GET /api/proxy/email/status
```

**Response**:
```json
{
  "gmail_connected": true,
  "yahoo_connected": false,
  "gmail_email": "user@gmail.com",
  "yahoo_email": null,
  "accounts": [
    {
      "provider": "gmail",
      "provider_name": "Gmail",
      "email": "user@gmail.com",
      "auth_type": "oauth"
    }
  ]
}
```

### 3. Verification Checks

After OAuth flow completes, perform these verification checks:

**Check credential file exists**:
```bash
ls -la backend/data/{username}/email_credentials/gmail.json
cat backend/data/{username}/email_credentials/gmail.json | jq '.email_address, .auth_type'
```

**Check API endpoint**:
```bash
curl -H "Authorization: Bearer <your-jwt>" \
     http://localhost:7001/api/v1/email/accounts
```

**Check backend logs for OAuth state validation**:
```
INFO: Created OAuth state token for user admin
INFO: Validated OAuth state for user admin
INFO: Saved gmail credentials for user admin
```

### 4. Testing Email Tools with Connected Account

Once Gmail is connected, test the email tools through the chat interface:

**Test 1: List recent emails**

In the chat interface, send:
```
List my recent Gmail emails
```

**Expected behavior**:
- Agent uses `list_gmail` tool
- Returns list of recent emails (default 10)
- Displays subject, sender, date

**Agent response example**:
```
Here are your recent Gmail emails:

1. Subject: Welcome to Your New Account
   From: noreply@example.com
   Date: Feb 18, 2026, 10:30 AM

2. Subject: Your Weekly Summary
   From: newsletter@example.com
   Date: Feb 17, 2026, 8:00 AM
```

**Backend logs**:
```
INFO:     Executing MCP tool: email_tools.list_gmail
INFO:     Listed 10 emails from Gmail
```

**Test 2: Read a specific email**

```
Read the Gmail email with ID 1234567890abcdef
```

**Expected behavior**:
- Agent uses `read_gmail` tool
- Returns full email body, headers
- Parses attachments if present

**Test 3: Search emails**

```
Search my Gmail for emails about "project update"
```

**Expected behavior**:
- Agent uses `search_gmail` tool
- Returns matching emails with search operators
- Displays relevance-ranked results

**Test 4: Download attachments**

```
Download attachments from Gmail email 1234567890abcdef
```

**Expected behavior**:
- Agent uses `download_gmail_attachments` tool
- Downloads attachments to `data/{username}/email_attachments/gmail/{message_id}/`
- Returns file paths and metadata

**Attachment storage verification**:
```bash
ls -la backend/data/{username}/email_attachments/gmail/1234567890abcdef/
# Output: document.pdf, image.png, etc.
```

---

## IMAP Connection Testing

### 1. Supported IMAP Providers

The following email providers are supported via IMAP app password:

| Provider | Email Domains | IMAP Server | Port |
|----------|---------------|-------------|------|
| Gmail (fallback) | gmail.com, googlemail.com | imap.gmail.com | 993 |
| Yahoo Mail | yahoo.com, yahoo.co.uk, ymail.com | imap.mail.yahoo.com | 993 |
| Outlook | outlook.com, hotmail.com, live.com, msn.com | outlook.office365.com | 993 |
| iCloud | icloud.com, me.com, mac.com | imap.mail.me.com | 993 |
| Zoho Mail | zoho.com, zohomail.com | imap.zoho.com | 993 |
| Custom | Any domain | Configurable | 993 |

### 2. App Password Generation Guide

Before connecting an IMAP account, you must generate an app-specific password:

#### Gmail App Password

1. Go to https://myaccount.google.com/apppasswords
2. Sign in if prompted
3. Select "Mail" from the app dropdown
4. Select "Other (Custom name)" and enter "Claude Agent SDK"
5. Click "Generate"
6. Copy the 16-character password (e.g., `abcd efgh ijkl mnop`)

**Note**: 2-Step Verification must be enabled on your Google Account to generate app passwords.

#### Yahoo App Password

1. Go to https://login.yahoo.com/account/security
2. Sign in if prompted
3. Scroll to "App passwords" section
4. Click "Generate app password"
5. Select "Mail" from app dropdown
6. Enter "Claude Agent SDK" as app name
7. Click "Generate"
8. Copy the app password

#### Outlook App Password

1. Go to https://account.microsoft.com/security
2. Sign in if prompted
3. Select "Advanced security options"
4. Under "App passwords", click "Create a new app password"
5. Copy the generated password

#### iCloud App Password

1. Go to https://appleid.apple.com/account/manage
2. Sign in with your Apple ID
3. Under "Security", find "App-Specific Passwords"
4. Click "Generate Password"
5. Enter a label (e.g., "Claude Agent SDK")
6. Click "Create"
7. Copy the password

#### Zoho App Password

1. Go to https://accounts.zoho.com/home#security
2. Sign in if prompted
3. Under "App Passwords", click "App Passwords"
4. Click "Generate New Password"
5. Select "Mail" and enter a password name
6. Click "Generate"
7. Copy the password

### 3. Step-by-Step IMAP Setup

#### Step 1: Navigate to Profile Page

1. Login to the application at `http://localhost:7002/login`
2. Navigate to the Profile page at `http://localhost:7002/profile`

#### Step 2: Open IMAP Connection Dialog

1. Click the "Connect IMAP Account" button
2. A modal dialog appears with connection form

#### Step 3: Enter IMAP Credentials

Fill in the form:

**For auto-detected providers (Gmail, Yahoo, Outlook, iCloud, Zoho)**:
```
Email: user@provider.com
App Password: your-16-char-app-password
```

**For custom IMAP providers**:
```
Email: user@custom-domain.com
App Password: your-app-password
IMAP Server: imap.custom-domain.com
IMAP Port: 993
```

#### Step 4: Submit Connection Request

Click "Connect" button.

**Frontend API call**:
```javascript
POST /api/proxy/email/imap/connect
{
  "email": "user@yahoo.com",
  "app_password": "abcdefg1234567",
  "provider": "yahoo",  // auto-detected
  "imap_server": null,   // auto-filled
  "imap_port": null      // auto-filled
}
```

#### Step 5: Backend Processing

Backend performs the following:

1. **Auto-detects provider** from email domain
2. **Resolves IMAP server config** from provider settings
3. **Tests IMAP connection** by logging in and out
4. **Saves credentials** to per-user storage

**Backend logs**:
```
INFO:     Testing IMAP connection for user@yahoo.com (imap.mail.yahoo.com:993)...
INFO:     IMAP connection test successful for user@yahoo.com
INFO:     Saved yahoo credentials for user admin
INFO:     Successfully connected Yahoo Mail IMAP for user admin (user@yahoo.com)
```

**Credential file created**: `data/{username}/email_credentials/yahoo.json`

#### Step 6: Verify Connection

Profile page updates to show connected account.

**API response**:
```json
{
  "message": "Yahoo Mail connected successfully via IMAP",
  "provider": "yahoo",
  "provider_name": "Yahoo Mail"
}
```

### 4. Connection Verification

**Check credential file**:
```bash
cat backend/data/{username}/email_credentials/yahoo.json | jq
```

**Expected output**:
```json
{
  "provider": "yahoo",
  "auth_type": "app_password",
  "email_address": "user@yahoo.com",
  "app_password": "encrypted-or-plain-password",
  "imap_server": "imap.mail.yahoo.com",
  "imap_port": 993,
  "smtp_server": "smtp.mail.yahoo.com",
  "smtp_port": 587
}
```

**List all accounts**:
```bash
curl -H "Authorization: Bearer <your-jwt>" \
     http://localhost:7001/api/v1/email/accounts
```

**Expected response**:
```json
{
  "accounts": [
    {
      "provider": "gmail",
      "provider_name": "Gmail",
      "email": "user@gmail.com",
      "auth_type": "oauth"
    },
    {
      "provider": "yahoo",
      "provider_name": "Yahoo Mail",
      "email": "user@yahoo.com",
      "auth_type": "app_password"
    }
  ]
}
```

### 5. Testing IMAP Email Tools

Once IMAP account is connected, test the tools:

**Test 1: List IMAP emails**

```
List my Yahoo emails
```

**Agent behavior**:
- Uses `list_email_accounts` to discover provider key
- Uses `list_imap_emails` with provider="yahoo"
- Returns list of emails from INBOX

**Backend logs**:
```
INFO:     Executing MCP tool: email_tools.list_email_accounts
INFO:     Found 2 connected accounts
INFO:     Executing MCP tool: email_tools.list_imap_emails
INFO:     Listed 15 emails from Yahoo INBOX
```

**Test 2: Read IMAP email**

```
Read the Yahoo email with message ID 12345
```

**Expected**: Returns full email content with headers

**Test 3: Search IMAP emails**

```
Search my Yahoo emails for "invoice" since 2025-01-01
```

**Agent behavior**:
- Uses `search_imap_emails` tool
- Supports search prefixes: `subject:`, `from:`, `since:`
- Returns matching emails

**Test 4: Download IMAP attachments**

```
Download attachments from Yahoo email 12345
```

**Expected**: Downloads to `data/{username}/email_attachments/yahoo/12345/`

### 6. Testing Multiple Accounts

The system supports multiple accounts per provider:

**Add second Gmail account via IMAP**:
1. Generate app password for second Gmail account
2. Connect via IMAP dialog
3. System saves as `gmail-anotheruser.json` (auto-generated key)

**Verification**:
```bash
ls -la backend/data/{username}/email_credentials/
# Output:
# gmail.json
# gmail-anotheruser.json
# yahoo.json
```

**Tool usage with provider key**:
```
List emails from my anotheruser@gmail.com account
```

Agent automatically detects correct provider key via `list_email_accounts`.

---

## Testing Email Tools

### 1. Available MCP Tools

#### Gmail Tools (OAuth only)

| Tool | Parameters | Description |
|------|------------|-------------|
| `list_gmail` | `max_results` (default 10), `query` (Gmail search query) | List emails with optional filters |
| `read_gmail` | `message_id` (required) | Read full email content |
| `search_gmail` | `query` (required), `max_results` (default 10) | Search using Gmail operators |
| `download_gmail_attachments` | `message_id` (required) | Download all attachments |

#### IMAP Tools (All providers)

| Tool | Parameters | Description |
|------|------------|-------------|
| `list_email_accounts` | None | List all connected accounts (Gmail + IMAP) |
| `list_imap_emails` | `provider` (required), `folder` (default INBOX), `max_results` (default 10) | List emails from IMAP account |
| `read_imap_email` | `provider` (required), `message_id` (required) | Read full email |
| `search_imap_emails` | `provider` (required), `query` (required), `max_results` (default 10) | Search with prefix operators |
| `download_imap_attachments` | `provider` (required), `message_id` (required) | Download attachments |
| `list_imap_folders` | `provider` (required) | List available folders |

### 2. Test Scenarios

#### Scenario 1: Multi-Provider Search

**User query**:
```
Search all my email accounts for messages from "boss@company.com"
```

**Expected agent behavior**:
1. Calls `list_email_accounts` to get all providers
2. Calls `search_gmail` for Gmail account
3. Calls `search_imap_emails` for each IMAP provider
4. Aggregates results from all accounts
5. Displays unified list with provider labels

#### Scenario 2: Attachment Download with Decryption

**User query**:
```
Download and read the PDF attachment from the bank statement email
```

**Expected agent behavior**:
1. Searches for bank statement email
2. Downloads attachments
3. If PDF is password-protected, attempts auto-decryption
4. Returns decrypted content

**PDF decryption configuration** (optional):
```bash
# In backend/.env
PDF_PASSWORD_CHASE="chase-password"
PDF_PASSWORD_BOA="boa-password"
```

#### Scenario 3: Folder Navigation

**User query**:
```
List my folders in Yahoo Mail and show emails from "Archive" folder
```

**Expected agent behavior**:
1. Calls `list_imap_folders` with provider="yahoo"
2. Receives list: INBOX, Archive, Sent, Trash, etc.
3. Calls `list_imap_emails` with provider="yahoo", folder="Archive"

---

## Common Issues and Troubleshooting

### Gmail OAuth Issues

#### Issue: "Gmail client ID not configured"

**Cause**: Missing `EMAIL_GMAIL_CLIENT_ID` environment variable

**Solution**:
```bash
# Add to backend/.env
EMAIL_GMAIL_CLIENT_ID=your-gmail-oauth-client-id
EMAIL_GMAIL_CLIENT_SECRET=your-gmail-oauth-client-secret
# Restart backend
```

**Verification**:
```bash
python -c "from core.settings import get_settings; print(get_settings().email.gmail_client_id)"
```

#### Issue: "Invalid or expired OAuth state"

**Cause**: OAuth state token expired (10-minute TTL) or CSRF attack

**Solution**: Try connection again. State tokens expire in 10 minutes.

**Backend log**:
```
WARNING: Invalid or expired OAuth state received
```

#### Issue: "redirect_uri_mismatch" error

**Cause**: Redirect URI in Google Cloud Console doesn't match backend setting

**Solution**:
1. Go to Google Cloud Console → Credentials
2. Edit OAuth 2.0 client
3. Add authorized redirect URI: `http://localhost:7001/api/v1/email/gmail/callback`
4. For production, use actual domain: `https://your-domain.com/api/v1/email/gmail/callback`

#### Issue: No refresh token received

**Cause**: User previously authorized the app, Google returns short-lived access token only

**Backend log**:
```
WARNING: No refresh token in Gmail response for user admin
```

**Solution**: User must revoke app access and re-authorize:
1. Go to https://myaccount.google.com/permissions
2. Revoke access to your OAuth app
3. Connect again via profile page

### IMAP Connection Issues

#### Issue: "IMAP login failed"

**Cause**: Incorrect app password or regular password used instead of app password

**Backend log**:
```
WARNING: IMAP login failed for user@yahoo.com on imap.mail.yahoo.com
INFO:     127.0.0.1:xxxx - "POST /api/v1/email/imap/connect HTTP/1.1" 400 Bad Request
```

**Solution**:
1. Generate new app password from provider's security settings
2. Ensure no spaces in password (Gmail app passwords have spaces but should be removed or kept as-is)
3. Verify email address is correct

#### Issue: "Could not connect to IMAP server"

**Cause**: IMAP server hostname/port incorrect or network issue

**Solution**:
1. Verify provider auto-detection: check email domain matches supported providers
2. For custom providers, manually specify IMAP server and port
3. Check network connectivity: `telnet imap.gmail.com 993`

#### Issue: "Unknown provider" error

**Cause**: Email domain not in `DOMAIN_TO_PROVIDER` mapping and no custom IMAP server specified

**Solution**: For custom domains, provide IMAP server in connection form:
```
IMAP Server: imap.custom-domain.com
IMAP Port: 993
```

### Email Tool Issues

#### Issue: "Provider not found" error

**Cause**: Incorrect provider key used in tool call

**Solution**: Use `list_email_accounts` to discover correct provider keys:
```
Provider keys: "gmail", "yahoo", "gmail-anotheruser"
```

#### Issue: "Folder not found" error

**Cause**: IMAP folder name case-sensitive or doesn't exist

**Solution**: Use `list_imap_folders` to get exact folder names:
```
Available folders: INBOX, Archive, Sent, Trash
```

#### Issue: Attachments not downloading

**Cause**: No write permissions to attachment directory

**Backend log**:
```
ERROR: Failed to save attachment: [Errno 13] Permission denied
```

**Solution**:
```bash
chmod -R 755 backend/data/{username}/email_attachments/
```

### Env-Var Auto-Seed Issues

#### Issue: Email accounts not seeding at startup

**Cause**: Missing or incorrect `EMAIL_ACCOUNT_N_*` environment variables

**Backend log**:
```
WARNING: EMAIL_ACCOUNT_1: no PASSWORD set, skipping user@gmail.com
```

**Solution**:
```bash
# Verify all required variables are set
EMAIL_ACCOUNT_1_EMAIL=user@gmail.com
EMAIL_ACCOUNT_1_PASSWORD=app-password
EMAIL_ACCOUNT_1_USERNAME=admin  # Optional, defaults to "admin"
```

#### Issue: IMAP connection test fails at startup

**Backend log**:
```
ERROR: EMAIL_ACCOUNT_1: IMAP connection test failed for user@gmail.com, skipping
```

**Solution**:
1. Verify app password is correct
2. Check IMAP access is enabled for account
3. For custom providers, set `EMAIL_ACCOUNT_1_IMAP_SERVER`

#### Issue: Account overwrites existing UI-modified credentials

**Expected behavior**: System skips seeding if credential file already exists

**Backend log**:
```
INFO: Email account user@gmail.com already configured (key: gmail), skipping
```

**If you want to force re-seed**: Delete existing credential file and restart:
```bash
rm backend/data/{username}/email_credentials/gmail.json
# Restart backend
```

---

## Success Criteria Checklist

Use this checklist to verify email integration is working correctly.

### Gmail OAuth

- [ ] Gmail OAuth button visible on profile page
- [ ] Clicking button redirects to Google OAuth consent screen
- [ ] Google OAuth shows correct app name and permissions
- [ ] After authorization, redirect to `/profile?email=gmail&status=connected`
- [ ] Profile page shows Gmail as connected with email address
- [ ] Credential file created at `data/{username}/email_credentials/gmail.json`
- [ ] Credential file contains access_token and refresh_token
- [ ] `GET /api/v1/email/status` returns `gmail_connected: true`
- [ ] `list_gmail` tool returns recent emails
- [ ] `read_gmail` tool returns full email content
- [ ] `search_gmail` tool returns matching emails
- [ ] `download_gmail_attachments` tool downloads files to correct directory
- [ ] Disconnect button removes credentials and updates UI

### IMAP Connection

- [ ] IMAP connection button visible on profile page
- [ ] Connection modal shows email, app password, server, port fields
- [ ] Provider auto-detection works for yahoo.com, outlook.com, etc.
- [ ] Custom IMAP server fields appear when needed
- [ ] Connection test succeeds before saving credentials
- [ ] Profile page shows IMAP account as connected
- [ ] Credential file created with correct provider key
- [ ] Credential file contains app_password and IMAP config
- [ ] `GET /api/v1/email/accounts` returns IMAP account
- [ ] `list_imap_emails` tool returns emails from INBOX
- [ ] `read_imap_email` tool returns full email
- [ ] `search_imap_emails` tool supports prefix operators
- [ ] `download_imap_attachments` tool downloads files
- [ ] Multiple accounts of same provider get unique keys
- [ ] Disconnect button removes credentials

### Multi-Provider

- [ ] Can connect both Gmail (OAuth) and Yahoo (IMAP) simultaneously
- [ ] Both accounts appear in profile page
- [ ] Email tools work for both providers
- [ ] Search across all providers works
- [ ] Attachments download to provider-specific directories

### Error Handling

- [ ] Invalid app password shows clear error message
- [ ] IMAP connection failure doesn't crash backend
- [ ] OAuth state expiration shows user-friendly error
- [ ] Missing provider key shows guidance to use `list_email_accounts`

---

## Expected Behaviors and Log Outputs

### Successful Gmail OAuth Flow

**Backend logs sequence**:
```
INFO:     127.0.0.1:54321 - "GET /api/v1/email/gmail/auth-url HTTP/1.1" 200 OK
INFO:     Created OAuth state token for user admin
INFO:     127.0.0.1:54322 - "GET /api/v1/email/gmail/callback?code=...&state=... HTTP/1.1" 302 Temporary Redirect
INFO:     Validated OAuth state for user admin
INFO:     Successfully connected Gmail for user admin (user@gmail.com)
INFO:     Saved gmail credentials for user admin
INFO:     127.0.0.1:54323 - "GET /api/v1/email/accounts HTTP/1.1" 200 OK
```

**File system changes**:
```
backend/data/admin/email_credentials/gmail.json  # Created
```

### Successful IMAP Connection

**Backend logs sequence**:
```
INFO:     Testing IMAP connection for user@yahoo.com (imap.mail.yahoo.com:993)...
INFO:     IMAP connection test successful for user@yahoo.com
INFO:     Saved yahoo credentials for user admin
INFO:     Successfully connected Yahoo Mail IMAP for user admin (user@yahoo.com)
INFO:     127.0.0.1:54324 - "POST /api/v1/email/imap/connect HTTP/1.1" 200 OK
```

**File system changes**:
```
backend/data/admin/email_credentials/yahoo.json  # Created
```

### Email Tool Execution

**Tool: list_gmail**
```
INFO:     Executing MCP tool: email_tools.list_gmail
INFO:     Gmail API request: userId=me, maxResults=10
INFO:     Listed 10 emails from Gmail
```

**Tool: list_imap_emails**
```
INFO:     Executing MCP tool: email_tools.list_imap_emails
INFO:     IMAP connection to imap.mail.yahoo.com:993
INFO:     Selected INBOX folder
INFO:     Listed 15 emails from Yahoo INBOX
INFO:     IMAP connection closed
```

**Tool: download_gmail_attachments**
```
INFO:     Executing MCP tool: email_tools.download_gmail_attachments
INFO:     Downloading 2 attachments from Gmail message 1234567890abcdef
INFO:     Saved attachment: invoice.pdf to backend/data/admin/email_attachments/gmail/1234567890abcdef/invoice.pdf
INFO:     Saved attachment: receipt.png to backend/data/admin/email_attachments/gmail/1234567890abcdef/receipt.png
```

### Error Scenarios

**Invalid app password**:
```
WARNING: IMAP login failed for user@yahoo.com on imap.mail.yahoo.com
INFO:     127.0.0.1:54325 - "POST /api/v1/email/imap/connect HTTP/1.1" 400 Bad Request
```

**OAuth state expired**:
```
WARNING: Invalid or expired OAuth state received
INFO:     127.0.0.1:54326 - "GET /api/v1/email/gmail/callback?code=...&state=... HTTP/1.1" 400 Bad Request
```

**Provider not found**:
```
ERROR: MCP tool execution failed: Provider 'unknown' not found. Use list_email_accounts to see available providers.
```

---

## Additional Testing Resources

### API Testing with cURL

**Get OAuth URL**:
```bash
curl -H "Authorization: Bearer <your-jwt>" \
     http://localhost:7001/api/v1/email/gmail/auth-url
```

**List accounts**:
```bash
curl -H "Authorization: Bearer <your-jwt>" \
     http://localhost:7001/api/v1/email/accounts
```

**Get providers**:
```bash
curl http://localhost:7001/api/v1/email/providers
```

**Connect IMAP**:
```bash
curl -X POST \
     -H "Authorization: Bearer <your-jwt>" \
     -H "Content-Type: application/json" \
     -d '{"email":"user@yahoo.com","app_password":"password123"}' \
     http://localhost:7001/api/v1/email/imap/connect
```

### Manual Credential Inspection

**View Gmail credentials**:
```bash
cat backend/data/admin/email_credentials/gmail.json | jq '.email_address, .auth_type, .expires_at'
```

**View IMAP credentials**:
```bash
cat backend/data/admin/email_credentials/yahoo.json | jq '.email_address, .imap_server, .imap_port'
```

**Check attachment storage**:
```bash
find backend/data/admin/email_attachments/ -type f
# Output:
# backend/data/admin/email_attachments/gmail/1234567890abcdef/document.pdf
# backend/data/admin/email_attachments/yahoo/0987654321fedcba/image.png
```

---

## Production Considerations

### Security

1. **OAuth secrets**: Store in secure vault (not .env files in production)
2. **Credential files**: Set restrictive permissions (chmod 600)
3. **HTTPS only**: OAuth redirect URIs must use HTTPS in production
4. **Token storage**: Consider encryption for long-term credential storage

### Scaling

1. **OAuth state store**: Currently in-memory, use Redis for multi-instance deployments
2. **Attachment storage**: Consider cloud storage (S3) instead of local filesystem
3. **Rate limiting**: Implement per-user rate limits for email API calls

### Monitoring

Key metrics to monitor:
- OAuth success/failure rates
- IMAP connection errors
- Email tool execution times
- Attachment storage usage

---

## Conclusion

This testing guide covers all aspects of email integration testing for the Claude Agent SDK. Follow the step-by-step procedures for Gmail OAuth and IMAP connections, verify with the success criteria checklist, and troubleshoot issues using the common issues section.

For additional support or questions, refer to:
- `backend/agent/tools/email/README.md` - Email integration architecture
- `backend/api/routers/email_auth.py` - OAuth and IMAP API implementation
- `backend/agent/tools/email/credential_store.py` - Credential storage logic
