# Zalo OA Setup Guide

Connect Zalo Official Account (OA) to the Claude Agent SDK backend so the AI agent auto-replies to incoming Zalo messages.

**Prerequisites**: Zalo account, a Zalo Official Account, backend deployed at `https://claude-agent-sdk-api.leanwise.ai`.

---

## Overview

Zalo integration uses the **Zalo OA API v3**. Users message your Official Account, Zalo sends webhook events to your backend, and the agent replies via the Customer Service message API.

```
Zalo user  →  Zalo OA  →  webhook  →  Backend  →  Claude Agent
           ←  Zalo OA  ←  OA API   ←  Backend  ←  Claude Agent
```

**Important**: Zalo OA customer service messages can only be sent **within 48 hours** of the user's last message. After 48h, you can only send broadcast/notification messages (which require templates and OA approval).

---

## Step 1: Create a Zalo Official Account

1. Go to [oa.zalo.me](https://oa.zalo.me/) and log in with your Zalo account
2. Click **Create OA** (Tạo OA)
3. Fill in the required information:
   - OA name
   - Category
   - Description
   - Avatar and cover photo
4. Submit and wait for approval (usually instant for personal OAs)

---

## Step 2: Create a Zalo App

1. Go to [developers.zalo.me](https://developers.zalo.me/)
2. Log in and click **Create App** (Tạo ứng dụng)
3. Fill in app details:
   - App name
   - App category: **OA Tools** or **Communication**
4. Note your **App ID** and **App Secret** from the app dashboard

---

## Step 3: Get OA Access Token

Zalo OA tokens are obtained via OAuth. The process:

### 3a: Get Authorization Code

Open this URL in your browser (replace `<APP_ID>` with your App ID):

```
https://oauth.zaloapp.com/v4/oa/permission?app_id=<APP_ID>&redirect_uri=https://claude-agent-sdk-api.leanwise.ai/api/v1/webhooks/zalo
```

1. Log in with your Zalo account
2. Select the OA to connect
3. Grant permissions: **Send messages**, **Manage messages**
4. After authorization, you'll be redirected with a `code` parameter in the URL
5. Copy the authorization code

### 3b: Exchange Code for Tokens

```bash
curl -X POST "https://oauth.zaloapp.com/v4/oa/access_token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "secret_key: <APP_SECRET>" \
  -d "app_id=<APP_ID>&code=<AUTH_CODE>&grant_type=authorization_code"
```

Response:
```json
{
  "access_token": "...",
  "refresh_token": "...",
  "expires_in": 86400
}
```

Save both tokens. The **access token** expires in 24 hours. The **refresh token** is used to get new access tokens.

### 3c: Refresh Token (When Expired)

Access tokens expire every 24 hours. Refresh them with:

```bash
curl -X POST "https://oauth.zaloapp.com/v4/oa/access_token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "secret_key: <APP_SECRET>" \
  -d "app_id=<APP_ID>&refresh_token=<REFRESH_TOKEN>&grant_type=refresh_token"
```

**Note**: Each refresh token can only be used once. The response includes a new refresh token — save it for next time.

---

## Step 4: Configure Webhook

1. Go to [developers.zalo.me](https://developers.zalo.me/) → your app → **Webhook**
2. Set:
   - **Webhook URL**: `https://claude-agent-sdk-api.leanwise.ai/api/v1/webhooks/zalo`
   - **OA**: Select your Official Account
3. Subscribe to events:
   - `user_send_text` (required)
   - `user_send_image` (optional, not yet handled)
   - `user_send_file` (optional, not yet handled)
4. Click **Save** (Lưu)

Zalo verifies the webhook by sending a GET request. The backend responds with `{"status": "ok"}` automatically.

---

## Step 5: Configure Backend

Add to `backend/.env`:

```env
ZALO_OA_ACCESS_TOKEN=<access-token>
ZALO_APP_SECRET=<app-secret>
```

| Variable | Required | Description |
|---|---|---|
| `ZALO_OA_ACCESS_TOKEN` | Yes | OA access token from Step 3 |
| `ZALO_APP_SECRET` | No | App secret for future signature verification |

Restart the backend:

```bash
tmux send-keys -t claude_sdk_backend C-c && sleep 1 && \
tmux send-keys -t claude_sdk_backend "source .venv/bin/activate && python main.py serve --port 7001" Enter
```

Verify the adapter registered in backend logs:
```
INFO  Zalo adapter registered
```

---

## Step 6: Map Zalo Users to App Users (Optional)

By default, Zalo users get a hashed username (`zalo_<sha256[:8]>`). To map a specific Zalo user to an app user:

1. Find the Zalo user ID (visible in webhook logs when they message the OA)
2. Add to `backend/.env`:

```env
PLATFORM_USER_MAP_ZALO_<USER_ID>=<app_username>
```

Example:

```env
PLATFORM_USER_MAP_ZALO_8472619350284716=admin
```

---

## Step 7: Test

1. Open Zalo on your phone or desktop
2. Search for your Official Account name
3. Send a message to the OA
4. The AI agent processes it and replies back
5. Check backend logs: `tmux attach -t claude_sdk_backend`

---

## Token Refresh Automation

Since Zalo access tokens expire every 24 hours, you should automate token refresh. Options:

### Option A: Cron Job

Create a refresh script at `backend/scripts/refresh_zalo_token.sh`:

```bash
#!/bin/bash
# Refresh Zalo OA access token
RESPONSE=$(curl -s -X POST "https://oauth.zaloapp.com/v4/oa/access_token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "secret_key: $ZALO_APP_SECRET" \
  -d "app_id=$ZALO_APP_ID&refresh_token=$ZALO_REFRESH_TOKEN&grant_type=refresh_token")

NEW_ACCESS_TOKEN=$(echo $RESPONSE | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
NEW_REFRESH_TOKEN=$(echo $RESPONSE | python -c "import sys,json; print(json.load(sys.stdin)['refresh_token'])")

# Update .env file
sed -i "s|ZALO_OA_ACCESS_TOKEN=.*|ZALO_OA_ACCESS_TOKEN=$NEW_ACCESS_TOKEN|" backend/.env
sed -i "s|ZALO_REFRESH_TOKEN=.*|ZALO_REFRESH_TOKEN=$NEW_REFRESH_TOKEN|" backend/.env

echo "Token refreshed at $(date)"
```

Add to crontab (every 20 hours):
```bash
0 */20 * * * /path/to/refresh_zalo_token.sh >> /var/log/zalo_refresh.log 2>&1
```

### Option B: Update at Runtime

The adapter supports runtime token updates:

```python
from platforms.adapters import get_adapter
adapter = get_adapter("zalo")
adapter.update_access_token(new_token)
```

---

## Message Formatting

Zalo does not support any markdown formatting. The adapter automatically strips all markdown syntax:

| Markdown | Zalo Output |
|---|---|
| `**bold**` | bold |
| `*italic*` | italic |
| `` `code` `` | code |
| `[link](url)` | link (url) |
| `# Header` | Header |
| `> quote` | quote |
| ` ```code block``` ` | code block (markers stripped) |

---

## Media Support

| Media Type | Receive | Send | Notes |
|---|---|---|---|
| Text | Yes | Yes | Markdown stripped automatically |
| Images | No | No | Not yet implemented |
| Files | No | No | Not yet implemented |
| Stickers | No | No | Zalo stickers ignored |

Currently only text messages (`user_send_text` events) are processed.

---

## Limitations

1. **48-hour messaging window**: Can only reply within 48h of user's last message (customer service API restriction)
2. **No typing indicators**: Zalo OA API does not support typing status
3. **Token expiry**: Access tokens expire every 24 hours — must be refreshed
4. **Text only**: Media messages (images, files) not yet supported
5. **No signature verification**: Zalo webhook verification differs from HMAC — currently accepts all webhooks
6. **Rate limits**: Zalo OA API has rate limits (varies by OA tier)

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Adapter not registered | Ensure `ZALO_OA_ACCESS_TOKEN` is set in `.env` and backend restarted |
| `error: -216` (invalid token) | Token expired — refresh using Step 3c |
| `error: -230` (no permission) | Re-authorize the OA with required permissions (Step 3a) |
| No webhooks arriving | Check webhook URL in Zalo developer dashboard (Step 4) |
| Messages not sending | Check 48h window — user must have messaged within 48 hours |
| Agent replies not appearing | Check backend logs for API errors: `tmux attach -t claude_sdk_backend` |
| Duplicate messages | Deduplication is handled automatically by the webhook router |

Test webhook manually:

```bash
curl -X POST "https://claude-agent-sdk-api.leanwise.ai/api/v1/webhooks/zalo" \
  -H "Content-Type: application/json" \
  -d '{
    "event_name": "user_send_text",
    "sender": {"id": "test_user_123"},
    "recipient": {"id": "oa_id"},
    "message": {"text": "Hello", "msg_id": "test_msg_001"}
  }'
```

Expected: `{"status": "ok"}`

---

## Architecture

| Component | File |
|---|---|
| Adapter | `backend/platforms/adapters/zalo.py` |
| Adapter registry | `backend/platforms/adapters/__init__.py` |
| Webhook routes | `backend/api/routers/webhooks.py` |
| Message worker | `backend/platforms/worker.py` |
| Identity mapping | `backend/platforms/identity.py` |

---

## Useful Links

- [Zalo OA Dashboard](https://oa.zalo.me/)
- [Zalo Developer Portal](https://developers.zalo.me/)
- [Zalo OA API v3 Documentation](https://developers.zalo.me/docs/official-account/api/send-message)
- [Zalo OAuth Documentation](https://developers.zalo.me/docs/official-account/api/xac-thuc)
