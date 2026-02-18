# Gmail OAuth Setup Guide

This guide provides step-by-step instructions for configuring Gmail OAuth integration with the Claude Agent SDK. OAuth authentication provides secure, passwordless access to Gmail accounts with automatic token refresh.

## Overview

The Gmail OAuth integration allows users to:
- Connect Gmail accounts securely without sharing passwords
- Grant read-only access to emails and attachments
- Automatically refresh access tokens without user intervention
- Comply with Google's security best practices

## Prerequisites

Before proceeding, ensure you have:
- A Google Cloud account with billing enabled (free tier works)
- Admin access to create OAuth 2.0 credentials
- Your application's callback URLs (see Environment Variables section below)
- Basic understanding of OAuth 2.0 flow

## Step-by-Step Google Cloud Console Setup

### 1. Create or Select a Google Cloud Project

1. Navigate to [Google Cloud Console](https://console.cloud.google.com/)
2. Click the project dropdown at the top
3. Click **"NEW PROJECT"** or select an existing project
4. Enter project details:
   - **Project name**: e.g., "Claude Agent SDK"
   - **Organization**: Select your organization (or leave blank for personal projects)
5. Click **"CREATE"**
6. Wait for the project to be created (this may take a minute)

### 2. Enable Gmail API

1. In the Google Cloud Console, navigate to **"APIs & Services"** > **"Library"**
2. Search for **"Gmail API"**
3. Click on **"Gmail API"** in the results
4. Click the **"ENABLE"** button
5. Wait for the API to be enabled (you should see a checkmark indicator)

### 3. Configure OAuth Consent Screen

1. Navigate to **"APIs & Services"** > **"OAuth consent screen"**
2. Choose the user type:
   - **External**: For any Gmail user (requires verification for production)
   - **Internal**: For users within your organization only
3. Click **"CREATE"**

#### 3a. Fill in OAuth Consent Screen Details

Complete the following fields:
- **App name**: "Claude Agent SDK" (or your application name)
- **User support email**: Your email address
- **Developer contact information**: Your email address
- **Scopes**: Leave blank for now (we'll add these in the next step)
- **Authorized domains**: Add your production domain (e.g., `tt-ai.org`)
- **Application home page**: Your frontend URL (optional)
- **Application privacy policy link**: Required for external apps (can be a simple page)
- **Application terms of service link**: Optional
- **Authorized domains**: Add your domains
- **Test users**: Add test email addresses for external type (required before verification)
- **Developer contact**: Your contact information

4. Click **"SAVE AND CONTINUE"** through each section
5. Review and click **"BACK TO DASHBOARD"**

### 4. Add Required Scopes

1. In the OAuth consent screen, click **"EDIT APP"** if needed
2. Navigate to the **"Scopes"** section
3. Click **"ADD SCOPE"**
4. Add the following scope:
   - `https://www.googleapis.com/auth/gmail.readonly` - Read and access your Gmail messages
5. Click **"ADD"** then **"SAVE AND CONTINUE"**

**Note**: The `gmail.readonly` scope is the minimum required scope. It allows reading emails and attachments but does not permit sending, deleting, or modifying messages.

### 5. Create OAuth Client ID Credentials

1. Navigate to **"APIs & Services"** > **"Credentials"**
2. Click **"CREATE CREDENTIALS"** > **"OAuth 2.0 Client ID"**
3. Select application type: **"Web application"**

#### 5a. Configure OAuth Client

Fill in the following information:

**Name**: "Claude Agent SDK Web Client" (or any descriptive name)

**Authorized JavaScript origins** (for development):
```
http://localhost:7002
```

**Authorized redirect URIs** (CRITICAL - must match exactly):
- **Development**: `http://localhost:7002/api/auth/callback/email/gmail`
- **Production**: `https://claude-agent-sdk-chat.tt-ai.org/api/auth/callback/email/gmail`
- **Additional Production**: `https://claude-agent-sdk-chat.leanwise.ai/api/auth/callback/email/gmail` (if applicable)

**Important Notes**:
- The redirect URI path must match EXACTLY (case-sensitive)
- Do not add trailing slashes
- Include both HTTP (dev) and HTTPS (production) versions
- The port number must match your frontend development server

4. Click **"CREATE"**

### 6. Copy Client ID and Client Secret

After creating the OAuth 2.0 Client ID:

1. A dialog will appear showing your credentials
2. Copy the **Client ID** (32-character string)
3. Copy the **Client Secret** (longer string, shown only once)
4. Store these securely - you'll need them for environment configuration

**If you close the dialog**, you can retrieve the credentials later:
1. Go to **"APIs & Services"** > **"Credentials"**
2. Find your OAuth 2.0 Client ID in the list
3. Click the eye icon or download the JSON file
4. The Client Secret is only shown at creation time, so keep it safe

## Environment Variable Configuration

Add the following environment variables to your backend `.env` file:

```bash
# ==============================================================================
# GMAIL OAUTH CONFIGURATION
# ==============================================================================
# Gmail OAuth 2.0 credentials (from Google Cloud Console)
EMAIL_GMAIL_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
EMAIL_GMAIL_CLIENT_SECRET=your-client-secret-here

# OAuth redirect URI (must match Google Cloud Console exactly)
# Dev: http://localhost:7002/api/auth/callback/email/gmail
# Prod: https://claude-agent-sdk-chat.tt-ai.org/api/auth/callback/email/gmail
EMAIL_GMAIL_REDIRECT_URI=http://localhost:7002/api/auth/callback/email/gmail

# Frontend URL for post-authentication redirect
EMAIL_FRONTEND_URL=http://localhost:7002
```

### Production Environment Variables

For production deployment, update the redirect URIs:

```bash
# Production Gmail OAuth configuration
EMAIL_GMAIL_CLIENT_ID=your-production-client-id.apps.googleusercontent.com
EMAIL_GMAIL_CLIENT_SECRET=your-production-client-secret
EMAIL_GMAIL_REDIRECT_URI=https://claude-agent-sdk-chat.tt-ai.org/api/auth/callback/email/gmail
EMAIL_FRONTEND_URL=https://claude-agent-sdk-chat.tt-ai.org
```

### Environment Variable Reference

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `EMAIL_GMAIL_CLIENT_ID` | Yes | OAuth 2.0 Client ID from Google Cloud Console | `123456789-abc...apps.googleusercontent.com` |
| `EMAIL_GMAIL_CLIENT_SECRET` | Yes | OAuth 2.0 Client Secret from Google Cloud Console | `GOCSPX-xxxxxxxxxxxx` |
| `EMAIL_GMAIL_REDIRECT_URI` | Yes | Callback URL for OAuth flow (must match Google Cloud Console) | `http://localhost:7002/api/auth/callback/email/gmail` |
| `EMAIL_FRONTEND_URL` | Yes | Frontend base URL for post-OAuth redirect | `http://localhost:7002` |

## Testing the Configuration

### 1. Backend Verification

Start your backend server:
```bash
cd backend
source .venv/bin/activate
python main.py serve --port 7001
```

Check the logs for email tool initialization:
- ✅ "Gmail tools loaded successfully"
- ❌ "Gmail credentials not configured" (missing env vars)

### 2. Frontend OAuth Flow Test

1. Navigate to your frontend application
2. Login to your account
3. Go to the **Profile** page
4. Click **"Connect Gmail"**
5. You should be redirected to Google's OAuth consent screen
6. Click **"Authorize"** to grant access
7. You'll be redirected back to the Profile page with a success message

### 3. Verify Token Storage

Check that credentials were saved:
```bash
# View stored credentials (replace with your username)
cat backend/data/{username}/email_credentials/gmail.json
```

Expected output:
```json
{
  "provider": "gmail",
  "auth_type": "oauth",
  "email_address": "user@gmail.com",
  "access_token": "ya29.a0AfH6SMBx...",
  "refresh_token": "1//0g...",
  "token_type": "Bearer",
  "expires_at": "2026-02-18T12:34:56"
}
```

## Troubleshooting Common Issues

### Issue 1: "Redirect URI Mismatch" Error

**Symptoms**: Google OAuth returns error: `redirect_uri_mismatch`

**Solution**:
1. Verify the redirect URI in Google Cloud Console matches EXACTLY
2. Check for:
   - Trailing slashes (should not have them)
   - HTTP vs HTTPS mismatch
   - Port number mismatch (dev: 7002, production: no port)
   - Case sensitivity in the URL path

**Correct format**:
```
http://localhost:7002/api/auth/callback/email/gmail
https://claude-agent-sdk-chat.tt-ai.org/api/auth/callback/email/gmail
```

**Incorrect formats**:
```
http://localhost:7002/api/auth/callback/email/gmail/  (trailing slash)
http://localhost:7002/api/auth/CallBack/email/gmail  (wrong case)
https://claude-agent-sdk-chat.tt-ai.org:7002/api/auth/callback/email/gmail  (port in HTTPS)
```

### Issue 2: "Unauthorized Client" Error

**Symptoms**: Error: `unauthorized_client`

**Solutions**:
1. Verify you're using the correct Client ID for your environment
2. Check that the OAuth consent screen is configured
3. Ensure the Gmail API is enabled
4. Verify your project has not been deleted or disabled

### Issue 3: No Refresh Token Returned

**Symptoms**: Access token works but expires after 1 hour with no refresh token

**Solution**:
1. The OAuth flow includes `prompt=consent` to force refresh token generation
2. If you previously authorized without this parameter, revoke access:
   - Go to [Google Account Security](https://myaccount.google.com/security)
   - Navigate to **"Third-party apps & services"**
   - Find your app and click **"Remove access"**
3. Re-authorize through your application

### Issue 4: "Access Blocked" for External OAuth

**Symptoms**: Google shows "Access blocked: App is unverified" warning

**Solution** (for development):
1. Add your test email addresses in the OAuth consent screen
2. Use test accounts during development
3. For production, complete Google's [app verification process](https://support.google.com/cloud/answer/1346367)

### Issue 5: Invalid Client Secret

**Symptoms**: Error: `invalid_client` or `unauthorized_client`

**Solution**:
1. Verify the Client Secret matches Google Cloud Console exactly
2. Check for extra whitespace in the `.env` file
3. If you lost the secret, delete the credential and create a new one in Google Cloud Console

### Issue 6. CORS Errors

**Symptoms**: Browser console shows CORS errors during OAuth flow

**Solution**:
1. Add your frontend origin to `CORS_ORIGINS` in backend `.env`:
   ```bash
   CORS_ORIGINS=http://localhost:7002,https://claude-agent-sdk-chat.tt-ai.org
   ```
2. Restart the backend server

### Issue 7. Token Expired Errors

**Symptoms**: Email tools fail with "Token expired" errors

**Solution**:
1. Check that refresh token was saved in credentials file
2. Verify the token refresh logic is working (check backend logs)
3. Manually revoke and re-authorize if needed

## Security Best Practices

### 1. Credential Storage

**DO**:
- Store Client Secret in environment variables only
- Never commit `.env` files to version control
- Use different Client IDs for dev and production
- Add `.env` to `.gitignore`
- Use secret management systems for production (e.g., AWS Secrets Manager, HashiCorp Vault)

**DON'T**:
- Hardcode credentials in source code
- Share credentials via email or chat
- Use production credentials in development
- Commit credentials to version control

### 2. OAuth Configuration

**DO**:
- Use the minimum required scopes (`gmail.readonly`)
- Implement proper CSRF protection (state parameter)
- Set appropriate token expiration times
- Monitor OAuth usage in Google Cloud Console
- Regularly rotate Client Secrets

**DON'T**:
- Request unnecessary scopes (e.g., `gmail.send` if only reading)
- Skip state parameter validation
- Store access tokens in URLs or logs
- Share OAuth URLs between environments

### 3. Redirect URI Security

**DO**:
- Use HTTPS for production redirect URIs
- Validate redirect URIs match exactly
- Include port numbers for development
- Whitelist only necessary domains

**DON'T**:
- Use HTTP for production (except localhost for dev)
- Use wildcard redirect URIs
- Allow open redirects
- Omit port numbers in development URIs

### 4. User Data Protection

**DO**:
- Store tokens encrypted at rest
- Use per-user credential isolation
- Implement proper logout/disconnect functionality
- Clear tokens when user revokes access
- Log security-relevant events (token refresh, failures)

**DON'T**:
- Store tokens in plaintext (except in memory)
- Share credentials between users
- Cache tokens indefinitely
- Ignore token expiration

### 5. Monitoring and Auditing

**DO**:
- Monitor OAuth token usage
- Set up alerts for suspicious activity
- Review connected apps regularly
- Audit credential access logs
- Track API quota usage

**DON'T**:
- Ignore error logs
- Expose detailed OAuth errors to end users
- Disable logging for OAuth flows
- Skip security testing

### 6. Production Readiness

Before deploying to production, ensure you have:
- [ ] Completed Google's app verification process (for external OAuth)
- [ ] Configured production-specific OAuth Client ID
- [ ] Set up production redirect URIs with HTTPS
- [ ] Implemented proper error handling
- [ ] Added rate limiting for OAuth endpoints
- [ ] Configured monitoring and alerting
- [ ] Tested token refresh flow thoroughly
- [ ] Set up backup/disaster recovery for credential store
- [ ] Documented OAuth flow for operations team
- [ ] Reviewed Google's [OAuth 2.0 security best practices](https://developers.google.com/identity/protocols/oauth2#securityconsiderations)

## Additional Resources

- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [Gmail API Documentation](https://developers.google.com/gmail/api)
- [Google Cloud Console](https://console.cloud.google.com/)
- [Setting up OAuth 2.0](https://developers.google.com/identity/protocols/oauth2/web-server)
- [OAuth 2.0 Scopes for Gmail API](https://developers.google.com/gmail/api/auth/scopes)
- [Google Cloud Project Best Practices](https://cloud.google.com/resource-manager/docs/creating-managing-projects)

## Support

For issues specific to this implementation:
1. Check the backend logs: `backend/logs/` (if configured)
2. Review the email auth router: `backend/api/routers/email_auth.py`
3. Verify environment variable loading in `backend/core/settings.py`
4. Check credential storage: `backend/data/{username}/email_credentials/`

For Google OAuth issues:
1. Review [Google Cloud Console Dashboard](https://console.cloud.google.com/apis/dashboard)
2. Check OAuth consent screen configuration
3. Verify API enablement status
4. Review credential configuration and restrictions

---

**Last Updated**: 2026-02-18
**Document Version**: 1.0
**Claude Agent SDK Version**: main branch
