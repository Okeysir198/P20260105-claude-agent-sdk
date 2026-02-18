# Telegram Setup Guide

Connect Telegram to the Claude Agent SDK backend so the AI agent auto-replies to incoming messages.

**Prerequisites**: Telegram account, backend deployed at `https://claude-agent-sdk-api.leanwise.ai`.

---

## Step 1: Create a Bot via BotFather

1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Choose a **display name** (e.g. "Claude Assistant")
4. Choose a **username** ending in `bot` (e.g. `claude_assistant_bot`)
5. BotFather replies with your **bot token** — copy it

The token looks like: `7123456789:AAH...`

---

## Step 2: Configure Backend

Add to `backend/.env`:

```env
TELEGRAM_BOT_TOKEN=<bot-token-from-botfather>
TELEGRAM_WEBHOOK_SECRET=<any-random-string-you-choose>
```

`TELEGRAM_WEBHOOK_SECRET` is an optional shared secret for verifying webhook authenticity. Telegram sends it back in the `X-Telegram-Bot-Api-Secret-Token` header. Choose any random string (e.g. generate with `openssl rand -hex 32`).

Restart the backend:

```bash
tmux send-keys -t claude_sdk_backend C-c && sleep 1 && \
tmux send-keys -t claude_sdk_backend "source .venv/bin/activate && python main.py serve --port 7001" Enter
```

---

## Step 3: Register Webhook

Use the setup helper to register your webhook URL with Telegram:

```bash
cd backend && source .venv/bin/activate
python -c "
from platforms.adapters.telegram_setup import run_setup
run_setup('https://claude-agent-sdk-api.leanwise.ai/api/v1/webhooks/telegram')
"
```

Or register manually via curl:

```bash
curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://claude-agent-sdk-api.leanwise.ai/api/v1/webhooks/telegram",
    "secret_token": "<TELEGRAM_WEBHOOK_SECRET>"
  }'
```

Expected response: `{"ok": true, "result": true, "description": "Webhook was set"}`

Verify the webhook is active:

```bash
curl "https://api.telegram.org/bot<BOT_TOKEN>/getWebhookInfo"
```

---

## Step 4: Set Bot Commands (Optional)

Configure the bot's command menu via BotFather:

1. Message @BotFather
2. Send `/setcommands`
3. Select your bot
4. Send:
   ```
   start - Start chatting with the AI assistant
   ```

---

## Step 5: Set Bot Description (Optional)

1. Message @BotFather
2. Send `/setdescription` → select your bot → enter a description
3. Send `/setabouttext` → select your bot → enter the about text
4. Send `/setuserpic` → select your bot → send a profile photo

---

## Step 6: Map Telegram Users to App Users (Optional)

By default, Telegram users get a hashed username (`telegram_<sha256[:8]>`). To map a Telegram user to a specific app user for per-user data isolation:

1. Find the Telegram user ID (visible in webhook logs or via `@userinfobot`)
2. Add to `backend/.env`:

```env
PLATFORM_USER_MAP_TELEGRAM_<USER_ID>=<app_username>
```

Example:

```env
PLATFORM_USER_MAP_TELEGRAM_123456789=admin
```

---

## Step 7: Test

1. Open Telegram and search for your bot by username
2. Send `/start` or any message
3. The AI agent processes it and replies back
4. Check backend logs: `tmux attach -t claude_sdk_backend`

---

## Media Support

The bot handles:

| Media Type | Supported | Notes |
|---|---|---|
| Photos | Yes | Sent as vision content blocks (Claude can "see" them) |
| Documents | Yes | Saved to file storage for agent tool access |
| Voice messages | Yes | Downloaded as audio files |
| Stickers | Yes | Non-animated, non-video only (WebP images) |
| Videos | No | Not yet implemented |

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Yes | Bot token from @BotFather |
| `TELEGRAM_WEBHOOK_SECRET` | No | Shared secret for webhook signature verification |
| `PLATFORM_DEFAULT_AGENT_ID` | No | Default agent ID for platform messages |
| `PLATFORM_USER_MAP_TELEGRAM_<ID>` | No | Map Telegram user ID to app username |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| No messages arriving | Verify webhook is set: `curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo` |
| `401 Unauthorized` from Telegram API | Bot token is wrong or revoked — regenerate via @BotFather |
| Webhook verification fails | Check `TELEGRAM_WEBHOOK_SECRET` matches what was sent to `setWebhook` |
| Bot doesn't respond | Check backend logs: `tmux attach -t claude_sdk_backend` |
| Adapter not registered | Ensure `TELEGRAM_BOT_TOKEN` is set in `.env` and backend is restarted |
| Markdown formatting broken | Install `telegramify-markdown`: `uv pip install telegramify-markdown` |
| Message too long | Adapter auto-splits at 4096 chars (Telegram limit) |

Delete webhook (to stop receiving messages):

```bash
curl "https://api.telegram.org/bot<BOT_TOKEN>/deleteWebhook"
```

---

## Architecture

| Component | File |
|---|---|
| Adapter | `backend/platforms/adapters/telegram.py` |
| Setup helper | `backend/platforms/adapters/telegram_setup.py` |
| Adapter registry | `backend/platforms/adapters/__init__.py` |
| Webhook routes | `backend/api/routers/webhooks.py` |
| Message worker | `backend/platforms/worker.py` |
| Media downloads | `backend/platforms/media.py` |
| Identity mapping | `backend/platforms/identity.py` |
