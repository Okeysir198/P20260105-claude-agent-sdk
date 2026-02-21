# WhatsApp Setup Guide

Connect WhatsApp to the Claude Agent SDK backend so the AI agent auto-replies to incoming messages.

**Prerequisites**: Facebook account, WhatsApp on your phone, backend deployed at `https://your-backend-url.example.com`.

---

## Step 1: Create a Meta App

1. Go to [developers.facebook.com](https://developers.facebook.com/) → **Get Started** → log in
2. Click **Create App**
3. Set app name, email, and business portfolio
4. Under **Use cases**, select **"Connect on WhatsApp"**
5. Click **Create App**

---

## Step 2: Get Credentials

On the WhatsApp use case page ("Send test messages" screen):

| Credential | Where | Notes |
|---|---|---|
| **Phone Number ID** | Step 2, below the test number | Numeric string (e.g. `931808700024763`) |
| **WABA ID** | Step 2, above the test number | WhatsApp Business Account ID |
| **Access Token** | Step 1 → "Log in with Facebook" | Temporary (60 min). See Step 7 for permanent |
| **App Secret** | Left sidebar → App Settings > Basic → Show | Hex string |

---

## Step 3: Add Your Phone as Test Recipient

1. On the use case page, **Step 3** → **Select a recipient number** → **Add phone number**
2. Enter your number and verify with the code sent to your phone

---

## Step 4: Configure Backend

Add to `backend/.env`:

```env
WHATSAPP_PHONE_NUMBER_ID=<phone-number-id>
WHATSAPP_ACCESS_TOKEN=<access-token>
WHATSAPP_VERIFY_TOKEN=<any-random-string-you-choose>
WHATSAPP_APP_SECRET=<app-secret>
```

`WHATSAPP_VERIFY_TOKEN` is a shared secret you create — use the same value in Step 5.

Restart the backend:

```bash
tmux send-keys -t claude_sdk_backend C-c && sleep 1 && \
tmux send-keys -t claude_sdk_backend "source .venv/bin/activate && python main.py serve --port 7001" Enter
```

Verify with: `pytest tests/test_13_whatsapp.py -v`

---

## Step 5: Register Webhook

1. Go to **WhatsApp > Configuration** in the left sidebar
2. Under **Webhook**, click **Edit**
3. Set:
   - **Callback URL**: `https://your-backend-url.example.com/api/v1/webhooks/whatsapp`
   - **Verify token**: same value as `WHATSAPP_VERIFY_TOKEN` in `.env`
4. Click **Verify and Save**
5. Click **Manage** → subscribe to the **`messages`** field

---

## Step 6: Subscribe App to WABA

**Critical step** — without this, webhooks go to Meta's default handler, not your backend.

```bash
curl -X POST "https://graph.facebook.com/v20.0/<WABA_ID>/subscribed_apps" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

Expected: `{"success": true}`

---

## Step 7: Permanent Access Token

The temporary token expires in 60 minutes. Create a permanent one:

1. Go to [business.facebook.com/settings](https://business.facebook.com/settings) → **Users** → **System Users**
2. Click **Add** → name it (e.g. "Claude Bot"), role **Admin**
3. Click **Add Assets** → select your app → enable **Full Control** → Save
4. Click **Generate New Token** → select your app → check `whatsapp_business_messaging` → expiration **Never**
5. Copy the token and update `WHATSAPP_ACCESS_TOKEN` in `.env`
6. Restart backend

---

## Step 8: Switch to Live Mode

1. Go to **App Settings > Basic**
2. Add a Privacy Policy URL (e.g. `https://your-frontend-url.example.com/privacy`)
3. Toggle **App Mode** from "Development" to **"Live"**

Without Live mode, only test webhooks from the dashboard are delivered.

---

## Step 9: Test

1. Send a template message from the Meta Dashboard to your phone (use case page → Step 6 → Send Message)
2. Reply from your WhatsApp — the AI agent processes it and replies back
3. Check backend logs: `tmux attach -t claude_sdk_backend`

---

## File Delivery

When the AI agent creates files (via the Write tool), they are automatically sent to the WhatsApp conversation:

| File Size | Behavior |
|---|---|
| < 10 MB | Sent directly as a WhatsApp document |
| >= 10 MB | A secure download link is sent instead (expires in 24 hours) |

If direct file sending fails (unsupported MIME type, API error), a download link is sent as a fallback.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Webhook verification fails | Check `WHATSAPP_VERIFY_TOKEN` matches in `.env` and Meta Dashboard |
| No webhooks arriving | Subscribe to `messages` field (Step 5.5) and subscribe app to WABA (Step 6) |
| `Account not registered` | Add recipient number as test phone (Step 3) |
| Token expired | Create permanent System User token (Step 7) |
| 24h window error | User must message the bot first; free-text replies only within 24h |
| Messages truncated | WhatsApp 4096-char limit; adapter auto-truncates |
| Adapter not registered | Check `WHATSAPP_ACCESS_TOKEN` is set in `.env` |

Test webhook manually:
```bash
curl "https://your-backend-url.example.com/api/v1/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=YOUR_TOKEN&hub.challenge=test123"
# Expected: test123
```

---

## Architecture

| Component | File |
|---|---|
| Adapter | `backend/platforms/adapters/whatsapp.py` |
| Adapter registry | `backend/platforms/adapters/__init__.py` |
| Webhook routes | `backend/api/routers/webhooks.py` |
| Message worker | `backend/platforms/worker.py` |
| Tests | `backend/tests/test_13_whatsapp.py` |
