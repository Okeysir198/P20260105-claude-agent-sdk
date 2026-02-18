# WhatsApp Setup Guide

Step-by-step guide to connect your WhatsApp account to the Claude Agent SDK chat backend.

**Goal**: Receive WhatsApp messages on your personal number (+84907996550) and have the AI agent respond automatically.

---

## Prerequisites

- A Facebook account
- WhatsApp installed on your phone (number: +84907996550)
- Backend already deployed at `https://claude-agent-sdk-api.leanwise.ai`

---

## Step 1: Create a Meta Developer Account

1. Go to [developers.facebook.com](https://developers.facebook.com/)
2. Click **Get Started** and log in with your Facebook account
3. Accept the terms and complete registration

---

## Step 2: Create a WhatsApp Business App

1. In the Meta Developer Dashboard, click **Create App**
2. Select **Business** as the app type
3. Fill in:
   - **App name**: e.g. "Claude Agent Bot"
   - **Contact email**: your email
   - **Business portfolio**: create one if you don't have one
4. Click **Create App**
5. On the product page, find **WhatsApp** and click **Set Up**

---

## Step 3: Get Your Credentials

After adding WhatsApp to your app, go to **WhatsApp > API Setup** in the left sidebar.

### Phone Number ID

- Meta provides a **free test phone number** automatically
- Copy the **Phone Number ID** shown on the API Setup page (a numeric string like `123456789012345`)

### Temporary Access Token

- On the same page, click **Generate** under "Temporary access token"
- Copy the token (starts with `EAA...`)
- This token expires in 24 hours (see Step 9 for a permanent one)

### App Secret

- Go to **App Settings > Basic** in the left sidebar
- Click **Show** next to App Secret
- Copy the hex string

---

## Step 4: Add Your Personal Number as Test Recipient

Meta's test number can only send messages to verified phone numbers.

1. On the **WhatsApp > API Setup** page, find the **To** field
2. Click **Manage phone number list**
3. Click **Add phone number**
4. Enter `+84907996550`
5. Verify via the SMS/WhatsApp code sent to your phone

---

## Step 5: Configure Backend Environment

Edit the backend `.env` file:

```bash
nano /home/nthanhtrung/Documents/01_Personal/P20260105-claude-agent-sdk/backend/.env
```

Add these 4 variables:

```env
# WhatsApp Cloud API
WHATSAPP_PHONE_NUMBER_ID=<your-phone-number-id>
WHATSAPP_ACCESS_TOKEN=<your-access-token>
WHATSAPP_VERIFY_TOKEN=<any-random-string-you-choose>
WHATSAPP_APP_SECRET=<your-app-secret>
```

| Variable | Where to Find | Required |
|----------|--------------|----------|
| `WHATSAPP_PHONE_NUMBER_ID` | WhatsApp > API Setup | Yes |
| `WHATSAPP_ACCESS_TOKEN` | WhatsApp > API Setup > Generate token | Yes |
| `WHATSAPP_VERIFY_TOKEN` | You create this (any random string) | Yes |
| `WHATSAPP_APP_SECRET` | App Settings > Basic > App Secret | Recommended |

The `WHATSAPP_VERIFY_TOKEN` is a shared secret you define. You'll use the same value when registering the webhook in Step 7.

---

## Step 6: Restart Backend and Verify

Restart the backend server:

```bash
tmux send-keys -t claude_sdk_backend C-c && sleep 1 && \
tmux send-keys -t claude_sdk_backend "source .venv/bin/activate && python main.py serve --port 7001" Enter
```

Check the logs for:

```
WhatsApp adapter registered
```

You can also run the test script:

```bash
cd backend && source .venv/bin/activate
python test_whatsapp_connection.py
```

This validates:
- Environment variables are set
- WhatsApp adapter is registered
- Webhook endpoint is configured

---

## Step 7: Register the Webhook

1. In the Meta Developer Dashboard, go to **WhatsApp > Configuration**
2. Under **Webhook**, click **Edit**
3. Fill in:
   - **Callback URL**: `https://claude-agent-sdk-api.leanwise.ai/api/v1/webhooks/whatsapp`
   - **Verify token**: the same value you set for `WHATSAPP_VERIFY_TOKEN` in `.env`
4. Click **Verify and Save**
   - Meta sends a GET request to your callback URL with a challenge
   - The backend responds automatically if the verify token matches
5. After verification succeeds, click **Manage** under Webhook fields
6. Subscribe to the **messages** field

---

## Step 8: Send a Test Message

### Option A: From Meta Dashboard

1. On **WhatsApp > API Setup**, use the **Send Message** section
2. Select your test number (+84907996550) as recipient
3. Click **Send Message**
4. You should receive a template message on WhatsApp

### Option B: From WhatsApp

1. Open WhatsApp on your phone
2. Send any message to the **test phone number** shown in the Meta dashboard
3. The backend receives the webhook, processes it through the AI agent, and sends a reply
4. Check backend logs for message processing details

---

## Step 9: Get a Permanent Access Token

The temporary token from Step 3 expires in 24 hours. For production use, create a System User token:

1. Go to [business.facebook.com/settings](https://business.facebook.com/settings)
2. Navigate to **Users > System Users**
3. Click **Add** to create a new System User
   - Name: e.g. "Claude Bot"
   - Role: **Admin**
4. Click **Add Assets**
   - Select your WhatsApp app
   - Enable **Full Control**
5. Click **Generate New Token**
   - Select your app
   - Check the `whatsapp_business_messaging` permission
   - Token expiration: **Never**
6. Copy the generated token
7. Update `WHATSAPP_ACCESS_TOKEN` in your `.env` with this permanent token
8. Restart the backend (Step 6)

---

## Step 10: Troubleshooting

### Webhook verification fails

- Confirm `WHATSAPP_VERIFY_TOKEN` in `.env` matches what you entered in Meta Dashboard
- Confirm the backend is running and accessible at the production URL
- Test manually: `curl "https://claude-agent-sdk-api.leanwise.ai/api/v1/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=YOUR_TOKEN&hub.challenge=test123"`
- Expected response: `test123`

### Messages not arriving

- Check that you subscribed to the **messages** webhook field (Step 7.6)
- Verify the recipient number is in the test phone number list (Step 4)
- Check backend logs for incoming webhook payloads

### "Token expired" errors

- The temporary access token lasts 24 hours
- Follow Step 9 to create a permanent System User token

### "Not within 24h window" errors

- WhatsApp only allows free-form replies within 24 hours of the user's last message
- The user must message the bot first before the bot can reply
- After 24 hours of inactivity, only pre-approved template messages can be sent

### Messages truncated

- WhatsApp has a 4096-character limit per message
- The adapter truncates longer messages and appends "..."

### Adapter not registered

- Check that `WHATSAPP_ACCESS_TOKEN` is set in `.env` (the adapter auto-registers when this variable is present)
- Check backend startup logs for errors

---

## Architecture Reference

| Component | File |
|-----------|------|
| Adapter code | `backend/platforms/adapters/whatsapp.py` |
| Adapter registration | `backend/platforms/adapters/__init__.py` |
| Webhook routes | `backend/api/routers/webhooks.py` |
| Test script | `backend/test_whatsapp_connection.py` |
| Env example | `backend/.env.example` |
| Platform guide | `docs/chat-platform-connection-guide.md` |
