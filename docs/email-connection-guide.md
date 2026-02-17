# Email Connection Guide

Connect your Gmail or Yahoo Mail account to let the Claude agent read, search, and download email attachments on your behalf.

---

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Admin Setup (Backend)](#admin-setup-backend)
- [User Guide: Connect Gmail](#user-guide-connect-gmail)
- [User Guide: Connect Yahoo Mail](#user-guide-connect-yahoo-mail)
- [Available Email Tools](#available-email-tools)
- [Disconnecting an Account](#disconnecting-an-account)
- [Security & Privacy](#security--privacy)
- [Troubleshooting](#troubleshooting)

---

## Overview

The Claude Agent SDK supports reading emails from two providers:

| Provider | Auth Method | Capabilities |
|----------|------------|-------------|
| **Gmail** | OAuth 2.0 (Google sign-in) | List, search, read, download attachments |
| **Yahoo Mail** | App-specific password (IMAP) | List, read, download attachments |

The agent has **read-only** access. It cannot send, delete, or modify your emails.

---

## Prerequisites

- A running Claude Agent SDK backend and frontend
- Backend installed with email dependencies: `pip install .[email]`
- A Google Cloud project with OAuth credentials (for Gmail)
- A Yahoo account with two-factor authentication enabled (for Yahoo)

---

## Admin Setup (Backend)

### 1. Install Email Dependencies

```bash
cd backend
pip install .[email]
# Installs: google-api-python-client, google-auth-oauthlib, imap-tools
```

### 2. Create Google OAuth Credentials (for Gmail)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select an existing one)
3. Navigate to **APIs & Services > Credentials**
4. Click **Create Credentials > OAuth client ID**
5. Select **Web application**
6. Add an authorized redirect URI:
   - Development: `http://localhost:7001/api/v1/email/gmail/callback`
   - Production: `https://<your-backend-domain>/api/v1/email/gmail/callback`
7. Copy the **Client ID** and **Client Secret**

### 3. Configure Environment Variables

Add these to your backend `.env` file:

```bash
# Gmail OAuth (required for Gmail support)
EMAIL_GMAIL_CLIENT_ID=your-client-id.apps.googleusercontent.com
EMAIL_GMAIL_CLIENT_SECRET=your-client-secret
EMAIL_GMAIL_REDIRECT_URI=http://localhost:7001/api/v1/email/gmail/callback

# Frontend URL (redirect after OAuth)
EMAIL_FRONTEND_URL=http://localhost:7002
```

For production:

```bash
EMAIL_GMAIL_REDIRECT_URI=https://your-backend.example.com/api/v1/email/gmail/callback
EMAIL_FRONTEND_URL=https://your-frontend.example.com
```

### 4. Restart the Backend

```bash
python main.py serve --port 7001
```

You should see in the logs:

```
INFO: Registered email_tools MCP server for agent
```

If email dependencies are missing, you will see:

```
WARNING: Email tools MCP server not available - google-api-python-client may not be installed
```

---

## User Guide: Connect Gmail

### Step 1: Open Profile Page

Navigate to the **Profile** page in the frontend (click your username in the sidebar, then "Profile").

### Step 2: Click "Connect Gmail"

Click the **Connect Gmail** button. You will be redirected to Google's sign-in page.

### Step 3: Grant Permission

Sign in with your Google account and grant the "View your Gmail messages" permission. This is read-only access — the agent cannot send or delete emails.

### Step 4: Confirm Connection

After granting permission, you will be redirected back to the Profile page. You should see your Gmail address displayed with a green "Connected" status.

### Step 5: Use Email Tools in Chat

Start a chat and ask the agent to work with your emails:

```
List my recent emails
```

```
Search for emails from john@example.com about the project proposal
```

```
Read email <message_id>
```

```
Download attachments from email <message_id>
```

---

## User Guide: Connect Yahoo Mail

### Step 1: Enable Two-Factor Authentication

1. Go to [Yahoo Account Security](https://login.yahoo.com/account/security)
2. Turn on **Two-step verification** if not already enabled
3. Follow the prompts to set up 2FA

### Step 2: Generate an App Password

1. On the same Yahoo Account Security page, find **Generate app password** (or "Other app passwords")
2. Select **Other App** and enter a name like "Claude Agent"
3. Click **Generate**
4. Copy the 16-character app password (e.g., `abcd efgh ijkl mnop`)

> **Important:** This app password is shown only once. Save it temporarily until you complete the next step.

### Step 3: Open Profile Page

Navigate to the **Profile** page in the frontend.

### Step 4: Click "Connect Yahoo Mail"

Click the **Connect Yahoo Mail** button. A form will appear.

### Step 5: Enter Credentials

- **Email**: Your full Yahoo email address (e.g., `user@yahoo.com`)
- **App Password**: The 16-character app password from Step 2

Click **Connect**.

### Step 6: Confirm Connection

You should see your Yahoo email address displayed with a green "Connected" status.

### Step 7: Use Email Tools in Chat

```
List my Yahoo Mail inbox
```

```
Read Yahoo email <message_id>
```

```
Download attachments from Yahoo email <message_id>
```

---

## Available Email Tools

### Gmail Tools

| Tool | Description | Parameters |
|------|-------------|-----------|
| `list_gmail` | List emails from a label | `max_results` (1-100), `query` (Gmail search), `label` (INBOX, UNREAD, STARRED, SENT, DRAFT, SPAM, TRASH) |
| `search_gmail` | Search across all emails | `query` (Gmail search syntax), `max_results` (1-100) |
| `read_gmail` | Read full email content | `message_id` |
| `download_gmail_attachments` | Download email attachments | `message_id`, `attachment_ids` (optional, downloads all if omitted) |

**Gmail Search Syntax Examples:**

| Query | Description |
|-------|-------------|
| `from:john@example.com` | Emails from a specific sender |
| `subject:invoice` | Emails with "invoice" in subject |
| `is:unread` | Unread emails |
| `has:attachment` | Emails with attachments |
| `before:2025/01/01` | Emails before a date |
| `after:2025/06/01 from:boss@company.com` | Combined filters |

### Yahoo Mail Tools

| Tool | Description | Parameters |
|------|-------------|-----------|
| `list_yahoo` | List emails from a folder | `max_results` (1-100), `folder` (INBOX, Sent, Drafts, etc.) |
| `read_yahoo` | Read full email content | `message_id`, `folder` |
| `download_yahoo_attachments` | Download email attachments | `message_id`, `filenames` (optional), `folder` |

---

## Disconnecting an Account

1. Go to the **Profile** page
2. Find the connected account
3. Click the **Disconnect** button
4. Confirm the disconnection

Your stored credentials are immediately deleted. The agent will no longer have access to that email account.

---

## Security & Privacy

### Data Isolation

- Each user's email credentials are stored in an isolated directory: `data/{username}/email_credentials/`
- One user cannot access another user's email data
- Downloaded attachments are stored per-user: `data/{username}/email_attachments/`

### Credential Storage

| Provider | What is Stored | Encryption |
|----------|---------------|------------|
| Gmail | OAuth refresh token + access token | File-system protected (not encrypted at rest) |
| Yahoo | Email address + app password | File-system protected (not encrypted at rest) |

### Access Scope

- **Gmail**: Read-only access (`gmail.readonly` scope). The agent cannot send, delete, or modify emails.
- **Yahoo**: IMAP read access only. The agent connects via IMAP with the app password.

### Token Management

- Gmail OAuth tokens are automatically refreshed when they expire
- Yahoo app passwords do not expire unless revoked manually
- OAuth state tokens use CSRF protection with a 10-minute TTL

---

## Troubleshooting

### "Email tools not available" in agent response

The email optional dependencies are not installed. Run:

```bash
cd backend
pip install .[email]
```

Then restart the backend.

### Gmail OAuth fails with "redirect_uri_mismatch"

The redirect URI in your Google Cloud Console doesn't match the one in your `.env` file. Make sure they are identical, including protocol (http vs https) and trailing slashes.

### Yahoo connection fails

1. Make sure two-factor authentication is enabled on your Yahoo account
2. Generate a **new** app password (the old one may have been revoked)
3. Make sure you are using the app password, not your Yahoo account password
4. Check that your Yahoo email address is correct

### Agent says "No email credentials found"

The user hasn't connected their email account yet. Go to the Profile page and connect the desired provider.

### Downloaded attachments are missing

Attachments are stored in `data/{username}/email_attachments/{provider}/{message_id}/`. Check that the directory exists and the agent's working directory has access to it.
