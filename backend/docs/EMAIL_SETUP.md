# Email Integration Setup Guide

Complete guide for configuring email integration with the Claude Agent SDK. Supports Gmail (OAuth), Yahoo Mail, Outlook, iCloud, Zoho Mail, and custom IMAP providers.

## Overview

The email integration provides two connection methods:

| Method | Providers | Auth Type | Setup |
|--------|-----------|-----------|-------|
| **OAuth 2.0** | Gmail | Google login consent screen | One-time Google Cloud setup |
| **IMAP + App Password** | Yahoo, Outlook, iCloud, Zoho, Custom | Provider-generated app password | Generate app password per provider |

All users can connect email accounts via the **Profile** page in the frontend. Additionally, the admin user has access to:
- **Auto-seeded accounts** from environment variables (connected at server startup)
- **PDF auto-decryption** for password-protected email attachments (e.g., bank statements)

## Quick Start

### For Users (Frontend)

1. Log in and navigate to **Profile** page
2. **Gmail**: Click "Connect Gmail" → authorize via Google consent screen
3. **Other providers**: Click "Connect Email (IMAP)" → enter email + app password

### For Admins (Environment Variables)

Add to backend `.env` file:
```bash
# Auto-seed email accounts (admin user only)
EMAIL_ACCOUNT_1_EMAIL=user@gmail.com
EMAIL_ACCOUNT_1_PASSWORD=abcd-efgh-ijkl-mnop

# PDF decryption passwords (admin user only)
PDF_PASSWORD_DEFAULT=your-password
```

---

## Connection Method 1: Gmail OAuth

### Prerequisites

- Google Cloud account (free tier works)
- Admin access to create OAuth 2.0 credentials

### Step 1: Google Cloud Project Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (e.g., "Claude Agent SDK")
3. Enable the **Gmail API**: APIs & Services > Library > search "Gmail API" > Enable

### Step 2: OAuth Consent Screen

1. Go to APIs & Services > OAuth consent screen
2. Choose user type:
   - **External**: Any Gmail user (requires verification for production)
   - **Internal**: Organization users only
3. Fill in:
   - App name: "Claude Agent SDK"
   - User support email: your email
   - Authorized domains: your production domain
   - Developer contact: your email
4. Add scope: `https://www.googleapis.com/auth/gmail.readonly`
5. Add test users (required for external type before verification)

### Step 3: Create OAuth Credentials

1. Go to APIs & Services > Credentials
2. Create Credentials > OAuth 2.0 Client ID
3. Application type: **Web application**
4. **Authorized JavaScript origins**:
   - `http://localhost:7002` (dev)
   - `https://your-frontend-domain.com` (production)
5. **Authorized redirect URIs** (must match exactly):
   - `http://localhost:7002/api/auth/callback/email/gmail` (dev)
   - `https://your-frontend-domain.com/api/auth/callback/email/gmail` (production)
6. Copy the **Client ID** and **Client Secret**

### Step 4: Environment Variables

```bash
# Gmail OAuth 2.0 credentials
EMAIL_GMAIL_CLIENT_ID=your-client-id.apps.googleusercontent.com
EMAIL_GMAIL_CLIENT_SECRET=your-client-secret

# Must match Google Cloud Console redirect URI exactly
EMAIL_GMAIL_REDIRECT_URI=http://localhost:7002/api/auth/callback/email/gmail

# Frontend URL for post-OAuth redirect
EMAIL_FRONTEND_URL=http://localhost:7002
```

Production:
```bash
EMAIL_GMAIL_REDIRECT_URI=https://your-frontend-domain.com/api/auth/callback/email/gmail
EMAIL_FRONTEND_URL=https://your-frontend-domain.com
```

### OAuth Flow

```
User clicks "Connect Gmail"
  → Frontend fetches /api/v1/email/gmail/auth-url (backend generates OAuth URL with CSRF state)
  → Browser redirects to Google consent screen
  → User authorizes
  → Google redirects to frontend /api/auth/callback/email/gmail (Next.js proxy route)
  → Frontend proxy forwards code+state to backend /api/v1/email/gmail/callback
  → Backend exchanges code for tokens, saves credentials
  → Frontend redirects to /profile with success indicator
```

---

## Connection Method 2: IMAP with App Password

### Why App Passwords?

Most email providers block regular passwords for third-party IMAP access. You must generate a provider-specific **app password** — a separate password created in your account security settings specifically for third-party apps.

Your regular login password **will not work** for IMAP connections.

### Provider Setup Guides

#### Yahoo Mail
1. Go to [Yahoo Account Security](https://login.yahoo.com/account/security)
2. Enable **Two-Step Verification** (required for app passwords)
3. Scroll to **"Generate and manage app passwords"**
4. Select "Other App", name it (e.g., "Claude Agent SDK")
5. Copy the generated password
6. IMAP server: `imap.mail.yahoo.com:993` (auto-configured)

#### Outlook / Hotmail / Live
1. Go to [Microsoft Account Security](https://account.microsoft.com/security)
2. Enable **Two-Step Verification**
3. Go to **"App passwords"** > Create a new app password
4. Copy the generated password
5. IMAP server: `outlook.office365.com:993` (auto-configured)

#### iCloud Mail
1. Go to [Apple ID](https://appleid.apple.com/) > Sign-In and Security
2. Enable **Two-Factor Authentication**
3. Go to **"App-Specific Passwords"** > Generate
4. Name it (e.g., "Claude Agent SDK")
5. Copy the generated password
6. IMAP server: `imap.mail.me.com:993` (auto-configured)

#### Zoho Mail
1. Go to [Zoho Account Security](https://accounts.zoho.com/home#security/security_pwd)
2. Enable **Two-Factor Authentication**
3. Go to **"Application-Specific Passwords"** > Generate
4. Copy the generated password
5. IMAP server: `imap.zoho.com:993` (auto-configured)

#### Custom IMAP Provider
1. Select "Custom IMAP" in the provider dropdown
2. Enter your IMAP server hostname and port (default: 993)
3. Use an app password if your provider requires one

### Auto-Detected Providers

The system auto-detects providers from email domain:

| Domain | Provider |
|--------|----------|
| `gmail.com`, `googlemail.com` | Gmail (OAuth recommended) |
| `yahoo.com`, `yahoo.co.uk`, `yahoo.co.jp`, `ymail.com` | Yahoo Mail |
| `outlook.com`, `hotmail.com`, `live.com`, `msn.com` | Outlook |
| `icloud.com`, `me.com`, `mac.com` | iCloud |
| `zoho.com`, `zohomail.com` | Zoho Mail |

---

## Admin-Only Features

### Auto-Seeded Email Accounts

Email accounts can be pre-configured via environment variables. These are **automatically connected at server startup for the admin user only**. Other users must connect their accounts from the frontend Profile page.

```bash
# Account 1
EMAIL_ACCOUNT_1_EMAIL=user@gmail.com
EMAIL_ACCOUNT_1_PASSWORD=abcd-efgh-ijkl-mnop
# EMAIL_ACCOUNT_1_IMAP_SERVER=imap.gmail.com    # Optional (auto-detected from domain)
# EMAIL_ACCOUNT_1_IMAP_PORT=993                  # Optional (default: 993)

# Account 2
EMAIL_ACCOUNT_2_EMAIL=user@yahoo.com
EMAIL_ACCOUNT_2_PASSWORD=wxyz-abcd-efgh-ijkl

# Add more accounts by incrementing the number...
```

**Behavior:**
- Provider is auto-detected from the email domain
- IMAP connection is tested before saving credentials
- Existing credentials are never overwritten (preserves UI-modified accounts)
- Multiple accounts per provider are supported (keys: `gmail`, `gmail-user2`, etc.)
- Only the `admin` user receives these accounts

### PDF Auto-Decryption

Password-protected PDF attachments (e.g., bank statements) are automatically decrypted when downloaded by the **admin user only**. Other users' PDF attachments are saved as-is.

```bash
# PDF passwords tried in order when decrypting attachments
PDF_PASSWORD_HSBC=your-hsbc-statement-password
PDF_PASSWORD_VIB_CASHBACK=your-vib-cashback-password
PDF_PASSWORD_VIB_BOUNDLESS=your-vib-boundless-password
PDF_PASSWORD_DEFAULT=fallback-password
```

Requires `pypdf` (included in email extras): `uv pip install -e ".[email]"`

---

## Installation

Install email dependencies:

```bash
cd backend
uv pip install -e ".[email]" --python .venv/bin/python
```

This installs:
- `google-api-python-client` — Gmail API client
- `google-auth-oauthlib` — Google OAuth 2.0
- `imap-tools` — Universal IMAP client
- `pypdf` — PDF decryption

---

## Environment Variable Reference

### Gmail OAuth

| Variable | Required | Description |
|----------|----------|-------------|
| `EMAIL_GMAIL_CLIENT_ID` | For Gmail | OAuth Client ID from Google Cloud Console |
| `EMAIL_GMAIL_CLIENT_SECRET` | For Gmail | OAuth Client Secret |
| `EMAIL_GMAIL_REDIRECT_URI` | For Gmail | Callback URL (must match Google Cloud Console exactly) |
| `EMAIL_FRONTEND_URL` | For Gmail | Frontend base URL for post-OAuth redirect |

### Auto-Seeded Accounts (Admin Only)

| Variable | Required | Description |
|----------|----------|-------------|
| `EMAIL_ACCOUNT_N_EMAIL` | Yes | Email address |
| `EMAIL_ACCOUNT_N_PASSWORD` | Yes | App password (not regular password) |
| `EMAIL_ACCOUNT_N_IMAP_SERVER` | No | Custom IMAP server (auto-detected from domain) |
| `EMAIL_ACCOUNT_N_IMAP_PORT` | No | Custom IMAP port (default: 993) |

### PDF Decryption (Admin Only)

| Variable | Required | Description |
|----------|----------|-------------|
| `PDF_PASSWORD_HSBC` | No | Password for HSBC bank statements |
| `PDF_PASSWORD_VIB_CASHBACK` | No | Password for VIB Cashback statements |
| `PDF_PASSWORD_VIB_BOUNDLESS` | No | Password for VIB Boundless statements |
| `PDF_PASSWORD_DEFAULT` | No | Fallback password for any PDF |

---

## Credential Storage

All credentials are stored per-user in isolated directories:

```
backend/data/{username}/
  email_credentials/
    gmail.json              # Gmail OAuth tokens
    yahoo.json              # Yahoo IMAP credentials
    outlook.json            # Outlook IMAP credentials
    gmail-secondaccount.json  # Additional Gmail account
  email_attachments/
    gmail/{message_id}/     # Downloaded attachments per message
```

- Credentials include tokens (OAuth) or app passwords (IMAP)
- OAuth tokens are automatically refreshed by Google's client library
- IMAP credentials store the app password for each connection
- Disconnecting an account deletes its credential file

---

## Troubleshooting

### Gmail OAuth Issues

**"Redirect URI Mismatch"**
- Verify redirect URI in Google Cloud Console matches `EMAIL_GMAIL_REDIRECT_URI` exactly
- Check: no trailing slashes, correct protocol (http vs https), correct port

**"Access Blocked: App is unverified"**
- Add test users in OAuth consent screen (for development)
- Complete Google's app verification for production

**No refresh token**
- Revoke app access at [Google Account Security](https://myaccount.google.com/security) > Third-party apps
- Re-authorize through the app (the `prompt=consent` parameter forces a new refresh token)

**"callback_forward_failed" error on Profile page**
- Check backend is running and accessible from the frontend
- Verify `BACKEND_API_URL` in frontend `.env` is correct
- Check backend logs for the actual error

### IMAP Issues

**"IMAP login failed"**
- You must use an **app password**, not your regular login password
- Generate an app password from your provider's security settings (see guides above)
- Verify 2FA is enabled (required by most providers before generating app passwords)

**Connection timeout**
- Check IMAP server and port are correct
- Verify network connectivity to the IMAP server
- Some corporate firewalls block IMAP port 993

### General Issues

**Gmail library not available**
- Install email dependencies: `uv pip install -e ".[email]" --python .venv/bin/python`
- Restart the backend server

**Email tools not appearing in agent**
- Ensure the agent has email MCP tools configured in `agents.yaml`
- Check backend startup logs for email tool registration errors

---

**Last Updated**: 2026-02-18
**Document Version**: 2.0
