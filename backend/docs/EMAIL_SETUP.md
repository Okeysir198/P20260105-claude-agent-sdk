# Email Integration Setup

Enable the agent to read emails via Gmail OAuth or IMAP app passwords.

## 1. Install Dependencies

```bash
cd backend
uv pip install -e ".[email]" --python .venv/bin/python
```

Installs: `google-api-python-client`, `google-auth-oauthlib`, `imap-tools`, `pypdf`

## 2. Choose Connection Method

| Method | Providers | How users connect |
|--------|-----------|-------------------|
| **OAuth 2.0** | Gmail | Profile page > "Connect Gmail" |
| **IMAP App Password** | Yahoo, Outlook, iCloud, Zoho, any IMAP | Profile page > "Connect Email (IMAP)" |

Admin can also auto-seed accounts via env vars (see Section 5).

## 3. Gmail OAuth Setup

### 3a. Google Cloud Console

1. Create a project at [console.cloud.google.com](https://console.cloud.google.com/)
2. Enable **Gmail API** (APIs & Services > Library)
3. Configure **OAuth consent screen**:
   - Scope: `https://www.googleapis.com/auth/gmail.readonly`
   - Add test users (required before Google verification)
4. Create **OAuth 2.0 Client ID** (type: Web application):
   - Authorized redirect URI: `http://localhost:7002/api/auth/callback/email/gmail`
   - Production: `https://your-frontend.com/api/auth/callback/email/gmail`

### 3b. Environment Variables

```bash
EMAIL_GMAIL_CLIENT_ID=your-client-id.apps.googleusercontent.com
EMAIL_GMAIL_CLIENT_SECRET=your-client-secret
EMAIL_GMAIL_REDIRECT_URI=http://localhost:7002/api/auth/callback/email/gmail
EMAIL_FRONTEND_URL=http://localhost:7002
```

### 3c. OAuth Flow

```
Profile > "Connect Gmail"
  → Backend generates OAuth URL with CSRF state
  → Google consent screen
  → Google redirects to frontend callback
  → Frontend proxies code+state to backend
  → Backend exchanges code for tokens, saves to data/{username}/email_credentials/gmail.json
  → Redirect to /profile with success
```

Tokens refresh automatically via Google's client library.

## 4. IMAP App Password Setup

Regular passwords do not work. Generate an **app password** from your provider:

| Provider | Where to generate | IMAP server (auto-detected) |
|----------|-------------------|-----------------------------|
| **Yahoo** | [Account Security](https://login.yahoo.com/account/security) > App passwords | `imap.mail.yahoo.com:993` |
| **Outlook** | [Microsoft Security](https://account.microsoft.com/security) > App passwords | `outlook.office365.com:993` |
| **iCloud** | [Apple ID](https://appleid.apple.com/) > App-Specific Passwords | `imap.mail.me.com:993` |
| **Zoho** | [Zoho Security](https://accounts.zoho.com/home#security/security_pwd) > App passwords | `imap.zoho.com:993` |
| **Custom** | Your provider's docs | Enter manually |

All providers require **2FA enabled** before app passwords can be generated.

### Auto-Detected Domains

| Domain | Provider |
|--------|----------|
| `gmail.com`, `googlemail.com` | Gmail |
| `yahoo.com`, `ymail.com`, `yahoo.co.*` | Yahoo |
| `outlook.com`, `hotmail.com`, `live.com` | Outlook |
| `icloud.com`, `me.com`, `mac.com` | iCloud |
| `zoho.com`, `zohomail.com` | Zoho |

## 5. Admin Auto-Seed (Environment Variables)

Pre-configure accounts in `.env` — connected at server startup for the **admin user only**.

```bash
EMAIL_ACCOUNT_1_EMAIL=user@gmail.com
EMAIL_ACCOUNT_1_PASSWORD=abcd-efgh-ijkl-mnop

EMAIL_ACCOUNT_2_EMAIL=user@yahoo.com
EMAIL_ACCOUNT_2_PASSWORD=wxyz-abcd-efgh-ijkl

# Optional overrides (auto-detected from domain by default)
# EMAIL_ACCOUNT_1_IMAP_SERVER=imap.gmail.com
# EMAIL_ACCOUNT_1_IMAP_PORT=993
```

Behavior:
- IMAP connection tested before saving
- Existing credentials never overwritten
- Multiple accounts per provider supported (keys: `gmail`, `gmail-user2`, ...)

### PDF Auto-Decryption (Admin Only)

```bash
PDF_PASSWORD_DEFAULT=fallback-password
PDF_PASSWORD_HSBC=your-hsbc-password
```

Requires `pypdf` (included in email extras).

## 6. Credential Storage

```
backend/data/{username}/
  email_credentials/
    gmail.json                  # OAuth tokens
    yahoo.json                  # IMAP app password
    gmail-secondaccount.json    # Additional account
  email_attachments/
    gmail/{message_id}/         # Downloaded attachments
```

Disconnecting deletes the credential file. Each user's data is isolated.

## 7. Testing

```bash
cd backend
pytest tests/test_14_email_connection.py -v
```

Runs real connections against configured accounts — no mocks. Tests credential loading, Gmail list/read, IMAP list/read/search/folders, and API status endpoints.

## 8. Troubleshooting

### Gmail

| Problem | Fix |
|---------|-----|
| Redirect URI mismatch | Ensure `EMAIL_GMAIL_REDIRECT_URI` matches Google Cloud Console exactly (protocol, port, no trailing slash) |
| Access blocked / unverified | Add test users in OAuth consent screen, or complete Google verification |
| No refresh token | Revoke access at [Google Security](https://myaccount.google.com/security) > Third-party apps, then re-authorize |
| callback_forward_failed | Check backend is running, verify `BACKEND_API_URL` in frontend `.env` |

### IMAP

| Problem | Fix |
|---------|-----|
| Login failed | Use app password, not regular password. Enable 2FA first. |
| Connection timeout | Check server/port. Corporate firewalls may block port 993. |

### General

| Problem | Fix |
|---------|-----|
| Gmail library not available | Run `uv pip install -e ".[email]"`, restart backend |
| Email tools not in agent | Check `agents.yaml` has email MCP tools, check startup logs |
