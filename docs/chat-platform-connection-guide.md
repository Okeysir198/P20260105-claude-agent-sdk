# Chat Platform Connection Guide

Connect the Claude Agent SDK to messaging platforms so users can interact with Claude agents directly from Telegram, WhatsApp, or Zalo.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Platform Comparison](#platform-comparison)
- [Telegram Setup](#telegram-setup)
- [WhatsApp Setup](#whatsapp-setup)
- [Zalo Setup](#zalo-setup)
- [Configuration Reference](#configuration-reference)
- [How It Works](#how-it-works)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

---

## Overview

The platform integration layer allows users to chat with Claude agents via popular messaging apps. Messages are received via webhooks, processed through the same agent pipeline as the web frontend, and responses are sent back to the user's chat.

Each platform user gets their own isolated data directory, session history, and conversation context — the same per-user isolation as web users.

---

## Architecture

```
User sends message in Telegram/WhatsApp/Zalo
                    |
                    v
Platform server sends webhook POST
                    |
                    v
POST /api/v1/webhooks/{platform}
    |
    |-- 1. Verify signature
    |-- 2. Parse into NormalizedMessage
    |-- 3. Return 200 OK immediately
    |-- 4. Background task processes message:
    |       |
    |       |-- Map platform user to internal username
    |       |-- Get or create session
    |       |-- Send to Claude agent (SDK)
    |       |-- Accumulate response
    |       |-- Send response back to platform
    |
    v
User receives response in their chat
```

---

## Platform Comparison

| Feature | Telegram | WhatsApp | Zalo |
|---------|----------|----------|------|
| **Cost** | Free | Free tier, then per-message | Free tier |
| **Setup Time** | Hours | 2-4 weeks (business verification) | 1-2 weeks |
| **Bot Creation** | Instant via @BotFather | Meta Business account required | Zalo OA required |
| **Message Limit** | 4096 chars (auto-split) | 4096 chars | Varies |
| **Markdown** | MarkdownV2 supported | Plain text only | Plain text only |
| **Region** | Global | Global | Vietnam only |
| **Auth** | Secret token header | HMAC-SHA256 | OA-level verification |
| **Recommended** | Start here | Phase 2 | Phase 3 (if needed) |

---

## Telegram Setup

### Prerequisites

- A Telegram account
- Your backend accessible via HTTPS (required for webhooks)

### Step 1: Create a Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Follow the prompts to set a name and username
4. Copy the **bot token** (e.g., `7123456789:AAHx...`)

### Step 2: Configure Environment Variables

Add to your backend `.env` file:

```bash
# Telegram bot token from @BotFather
TELEGRAM_BOT_TOKEN=7123456789:AAHxYourBotTokenHere

# Random 32-character string for webhook signature verification
TELEGRAM_WEBHOOK_SECRET=your-random-32-char-secret-string

# (Optional) Default agent to use for platform messages
PLATFORM_DEFAULT_AGENT_ID=your-agent-id
```

Generate a secure webhook secret:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Step 3: Restart the Backend

```bash
python main.py serve --port 7001
```

You should see in the logs:

```
INFO: Telegram adapter registered
```

### Step 4: Register the Webhook

Use the built-in CLI command:

```bash
python main.py setup-telegram --webhook-url https://your-backend.example.com/api/v1/webhooks/telegram
```

Expected output:

```
Bot: @your_bot_name (id: 7123456789)
Webhook set successfully: https://your-backend.example.com/api/v1/webhooks/telegram
```

Alternatively, register via curl:

```bash
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
  -d "url=https://your-backend.example.com/api/v1/webhooks/telegram" \
  -d "secret_token=<YOUR_WEBHOOK_SECRET>"
```

### Step 5: Test the Bot

1. Open Telegram and search for your bot by username
2. Send `/start` or any message
3. You should receive a response from the Claude agent

### Telegram Features

- **Auto-split**: Long responses are automatically split at paragraph/sentence boundaries to respect the 4096-character limit
- **Markdown**: Responses are formatted in Telegram's MarkdownV2 (with automatic fallback to plain text if formatting fails)
- **Typing indicator**: A "typing..." indicator is shown while the agent processes your message
- **Multi-turn conversations**: Each chat maintains its own session history across messages

---

## WhatsApp Setup

### Prerequisites

- A [Meta Business account](https://business.facebook.com/)
- A WhatsApp Business API phone number
- Your backend accessible via HTTPS

> **Note:** WhatsApp Business API setup requires Meta business verification, which can take 2-4 weeks.

### Step 1: Set Up WhatsApp Business API

1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Create a new app (type: **Business**)
3. Add the **WhatsApp** product to your app
4. In **WhatsApp > Getting Started**, note your:
   - **Phone Number ID**
   - **WhatsApp Business Account ID**
5. Generate a **permanent access token** (or use a temporary one for testing)

### Step 2: Configure Environment Variables

Add to your backend `.env` file:

```bash
# From Meta Developer Dashboard
WHATSAPP_PHONE_NUMBER_ID=123456789012345
WHATSAPP_ACCESS_TOKEN=EAAx...your-access-token

# Random string for webhook verification handshake
WHATSAPP_VERIFY_TOKEN=your-random-verify-token

# App secret from Meta Developer Dashboard (for signature verification)
WHATSAPP_APP_SECRET=your-app-secret-hex
```

### Step 3: Restart the Backend

```bash
python main.py serve --port 7001
```

You should see:

```
INFO: WhatsApp adapter registered
```

### Step 4: Register the Webhook in Meta Dashboard

1. Go to your app in [Meta for Developers](https://developers.facebook.com/)
2. Navigate to **WhatsApp > Configuration**
3. Under **Webhook**, click **Edit**
4. Enter:
   - **Callback URL**: `https://your-backend.example.com/api/v1/webhooks/whatsapp`
   - **Verify Token**: The value you set in `WHATSAPP_VERIFY_TOKEN`
5. Click **Verify and Save**
6. Subscribe to the **messages** webhook field

### Step 5: Test

1. Send a message from your personal WhatsApp to the business phone number
2. You should receive a response from the Claude agent

### WhatsApp Limitations

- **24-hour window**: You can only send free-form messages within 24 hours of the user's last message. After 24 hours, only template messages are allowed.
- **No typing indicator**: WhatsApp Cloud API doesn't support typing indicators.
- **Message truncation**: Messages over 4096 characters are truncated (not split like Telegram).
- **Business verification required**: Meta requires business verification before you can send messages to users.

---

## Zalo Setup

### Prerequisites

- A Zalo Official Account (OA)
- A Vietnamese phone number or business entity
- Your backend accessible via HTTPS

> **Note:** Zalo is primarily available in Vietnam.

### Step 1: Create a Zalo Official Account

1. Go to [Zalo OA Admin](https://oa.zalo.me/)
2. Create a new Official Account
3. Go to **Settings > Developer** to get your credentials

### Step 2: Configure Environment Variables

Add to your backend `.env` file:

```bash
# From Zalo OA Developer settings
ZALO_OA_ACCESS_TOKEN=your-oa-access-token
ZALO_APP_SECRET=your-app-secret
```

### Step 3: Restart the Backend

```bash
python main.py serve --port 7001
```

You should see:

```
INFO: Zalo adapter registered
```

### Step 4: Register the Webhook in Zalo OA

1. Go to your Zalo OA Developer settings
2. Set the webhook URL to: `https://your-backend.example.com/api/v1/webhooks/zalo`
3. Subscribe to `user_send_text` events

### Step 5: Test

1. Search for your OA in the Zalo app
2. Send a text message
3. You should receive a response from the Claude agent

### Zalo Limitations

- **Vietnam only**: Zalo is primarily used in Vietnam
- **Token expiration**: Zalo OA access tokens expire and need periodic refresh (manual for now)
- **Text only**: Currently supports text messages only (no images or files)
- **No typing indicator**: Zalo OA API doesn't support typing indicators

---

## Configuration Reference

### Environment Variables

| Variable | Platform | Required | Description |
|----------|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Telegram | Yes | Bot token from @BotFather |
| `TELEGRAM_WEBHOOK_SECRET` | Telegram | Recommended | Random string for webhook signature verification |
| `WHATSAPP_PHONE_NUMBER_ID` | WhatsApp | Yes | Phone number ID from Meta Dashboard |
| `WHATSAPP_ACCESS_TOKEN` | WhatsApp | Yes | Permanent access token from Meta |
| `WHATSAPP_VERIFY_TOKEN` | WhatsApp | Yes | Random string for webhook handshake |
| `WHATSAPP_APP_SECRET` | WhatsApp | Recommended | App secret for HMAC signature verification |
| `ZALO_OA_ACCESS_TOKEN` | Zalo | Yes | OA access token |
| `ZALO_APP_SECRET` | Zalo | No | App secret for verification |
| `PLATFORM_DEFAULT_AGENT_ID` | All | No | Default agent ID for platform messages (uses system default if not set) |

### Optional Dependencies

```bash
# Telegram markdown formatting (optional, falls back to plain text)
pip install telegramify-markdown

# Or install all platform extras
pip install .[platforms]
```

---

## How It Works

### User Identity Mapping

Each platform user is mapped to an internal username using a deterministic hash:

```
Telegram user 12345  -->  telegram_5994471a
WhatsApp +1234567890 -->  whatsapp_a1b2c3d4
Zalo user 98765      -->  zalo_e5f6g7h8
```

This username is used as the data directory: `data/telegram_5994471a/sessions.json`, etc.

### Session Persistence

- Each platform chat maintains its own session
- Session mappings are stored in `data/{username}/platform_sessions.json`
- Multi-turn conversations maintain full context
- Session history is stored in the same JSONL format as web sessions

### Message Deduplication

Webhooks may be retried by the platform if your server doesn't respond fast enough. The system uses in-memory deduplication (keyed by `platform:message_id`) to prevent processing the same message twice. Entries expire after 1 hour.

### Background Processing

Webhook handlers return `200 OK` immediately and process messages in FastAPI background tasks. This prevents timeout errors from platforms that require fast ACK (e.g., Zalo's 2-second requirement).

---

## Testing

### Verify Adapter Registration

```bash
# Check which adapters are registered
python -c "
from platforms.adapters import get_all_adapters
for name, adapter in get_all_adapters().items():
    print(f'{name}: {type(adapter).__name__}')
"
```

### Test Telegram Webhook Locally

Use [ngrok](https://ngrok.com/) to expose your local server:

```bash
# Terminal 1: Start backend
python main.py serve --port 7001

# Terminal 2: Expose via ngrok
ngrok http 7001

# Terminal 3: Register webhook with ngrok URL
python main.py setup-telegram --webhook-url https://abc123.ngrok.io/api/v1/webhooks/telegram
```

### Verify Webhook Health

```bash
# Telegram: Check webhook info
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"

# WhatsApp: Verify endpoint responds
curl https://your-backend.example.com/api/v1/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=YOUR_TOKEN&hub.challenge=test
```

### Check Session Data

After sending a message, verify data was created:

```bash
# List platform user directories
ls backend/data/ | grep -E "telegram_|whatsapp_|zalo_"

# Check session mapping
cat backend/data/telegram_5994471a/platform_sessions.json

# Check message history
cat backend/data/telegram_5994471a/history/<session_id>.jsonl
```

---

## Troubleshooting

### "Platform 'telegram' not configured" (404)

The `TELEGRAM_BOT_TOKEN` environment variable is not set. Add it to your `.env` file and restart the backend.

### Telegram bot doesn't respond

1. Check webhook is registered: `curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"`
2. Check `pending_update_count` in the response — if it's growing, your backend isn't processing webhooks
3. Check backend logs for errors
4. Make sure your backend URL is accessible via HTTPS from the internet

### WhatsApp webhook verification fails

1. Make sure the `WHATSAPP_VERIFY_TOKEN` in your `.env` matches what you entered in the Meta Dashboard
2. The GET endpoint must return the challenge value as plain text

### Messages are processed twice

This usually means webhook retries are happening faster than your deduplication. Check that:
1. Your backend ACKs within 2-5 seconds (background tasks handle the slow processing)
2. The message has a `message_id` in its metadata

### Agent uses wrong agent or no agent

Set the `PLATFORM_DEFAULT_AGENT_ID` environment variable to the agent ID you want platform messages to use. You can find available agent IDs with:

```bash
python main.py agents
```

### Long responses are cut off (WhatsApp/Zalo)

WhatsApp and Zalo truncate messages at ~4096 characters. For Telegram, messages are automatically split into multiple messages. Consider configuring agents with shorter response prompts for platform use.

### Zalo token expired

Zalo OA access tokens expire periodically. You need to manually refresh the token and update the `ZALO_OA_ACCESS_TOKEN` environment variable, then restart the backend.
