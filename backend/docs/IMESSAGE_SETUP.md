# iMessage Setup Guide

Connect iMessage to the Claude Agent SDK backend so the AI agent auto-replies to incoming iMessages.

**Prerequisites**: A Mac running 24/7 (Mac mini recommended), an Apple ID signed into iMessage, backend deployed at `https://claude-agent-sdk-api.leanwise.ai`.

---

## Overview

iMessage integration uses **BlueBubbles** as a bridge. BlueBubbles is an open-source server that runs on macOS and exposes iMessage via a REST API + webhooks.

```
iPhone/Mac user  →  iMessage  →  Mac (BlueBubbles)  →  webhook  →  Backend  →  Claude Agent
                 ←  iMessage  ←  Mac (BlueBubbles)  ←  REST API ←  Backend  ←  Claude Agent
```

---

## Step 1: Set Up a Mac

You need a Mac that stays on 24/7. Options:

| Option | Cost | Notes |
|---|---|---|
| **Mac mini (used)** | $300-600 one-time | Most cost-effective for long-term use |
| **Mac mini (new, M4)** | $500-600 one-time | Best performance, Apple Silicon |
| **MacStadium** | ~$50-80/month | Cloud-hosted Mac mini |
| **AWS EC2 Mac** | ~$80-100/month | `mac1.metal` or `mac2.metal` instances |

The Mac must:
- Be signed into an **Apple ID** with iMessage enabled
- Have **Messages.app** open and working
- Stay awake (disable sleep in System Settings > Energy)
- Be reachable from your backend server (same network or port-forwarded)

---

## Step 2: Install BlueBubbles Server

1. Download BlueBubbles from [bluebubbles.app](https://bluebubbles.app/)
2. Open the `.dmg` and drag BlueBubbles to Applications
3. Launch BlueBubbles Server
4. Grant required permissions when prompted:
   - **Full Disk Access** (System Settings > Privacy & Security > Full Disk Access)
   - **Accessibility** (for Private API features)
5. Set a **server password** — you'll need this for the backend config
6. Note the **server URL** shown in BlueBubbles (e.g. `http://192.168.1.100:1234`)

### Enable Private API (Recommended)

The Private API enables typing indicators, read receipts, and more reliable message sending:

1. In BlueBubbles Server, go to **Settings > Private API**
2. Follow the setup instructions (requires SIP modification or helper bundle)
3. Enable **Private API** toggle

Without the Private API, the adapter falls back to AppleScript for sending messages, which is slower and less reliable.

---

## Step 3: Configure Backend

Add to `backend/.env`:

```env
BLUEBUBBLES_SERVER_URL=http://<mac-ip>:1234
BLUEBUBBLES_PASSWORD=<server-password>
BLUEBUBBLES_WEBHOOK_SECRET=<optional-random-string>
```

| Variable | Required | Description |
|---|---|---|
| `BLUEBUBBLES_SERVER_URL` | Yes | BlueBubbles server URL (e.g. `http://192.168.1.100:1234`) |
| `BLUEBUBBLES_PASSWORD` | Yes | Server password set in BlueBubbles |
| `BLUEBUBBLES_WEBHOOK_SECRET` | No | HMAC-SHA256 secret for webhook signature verification |

Restart the backend:

```bash
tmux send-keys -t claude_sdk_backend C-c && sleep 1 && \
tmux send-keys -t claude_sdk_backend "source .venv/bin/activate && python main.py serve --port 7001" Enter
```

Verify the adapter registered in backend logs:
```
INFO  iMessage adapter registered (BlueBubbles)
```

---

## Step 4: Register Webhook

Use the setup helper to register your webhook URL with BlueBubbles:

```bash
cd backend && source .venv/bin/activate
python -c "
from platforms.adapters.imessage_setup import run_setup
run_setup('https://claude-agent-sdk-api.leanwise.ai/api/v1/webhooks/imessage')
"
```

Or register manually in the BlueBubbles Server UI:

1. Open BlueBubbles Server on the Mac
2. Go to **Settings > Webhooks**
3. Click **Add Webhook**
4. Set URL: `https://claude-agent-sdk-api.leanwise.ai/api/v1/webhooks/imessage`
5. Select events: `new-message`, `updated-message`, `message-send-error`
6. Save

Or via curl:

```bash
curl -X POST "http://<mac-ip>:1234/api/v1/server/webhooks?password=<PASSWORD>" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://claude-agent-sdk-api.leanwise.ai/api/v1/webhooks/imessage",
    "events": ["new-message", "updated-message", "message-send-error", "typing-indicator"]
  }'
```

---

## Step 5: Verify Connectivity

Test that BlueBubbles is reachable from the backend:

```bash
curl "http://<mac-ip>:1234/api/v1/server/info?password=<PASSWORD>"
```

Expected: JSON with server version, macOS version, and iMessage status.

Test the webhook endpoint:

```bash
curl -X POST "https://claude-agent-sdk-api.leanwise.ai/api/v1/webhooks/imessage" \
  -H "Content-Type: application/json" \
  -d '{"type": "typing-indicator", "data": {}}'
```

Expected: `{"status": "ignored"}` (typing indicators are not user messages).

---

## Step 6: Map iMessage Users to App Users (Optional)

By default, iMessage users get a hashed username (`imessage_<sha256[:8]>`). To map a specific phone number or email to an app user:

```env
PLATFORM_USER_MAP_IMESSAGE_+1234567890=admin
PLATFORM_USER_MAP_IMESSAGE_user@icloud.com=admin
```

The key is the sender's iMessage address (phone number or Apple ID email).

---

## Step 7: Test

1. Send an iMessage to the Apple ID configured on the Mac
2. The AI agent processes it and replies back via iMessage
3. Check backend logs: `tmux attach -t claude_sdk_backend`

---

## Network Setup

If BlueBubbles and the backend are on different networks, you need the Mac reachable from the backend:

### Same Network (Simplest)
- Use the Mac's local IP: `http://192.168.1.100:1234`

### Different Networks
Options:
1. **Port forwarding**: Forward port 1234 on the Mac's router
2. **Tailscale/ZeroTier**: VPN mesh network (recommended for security)
3. **Cloudflare Tunnel**: Run `cloudflared` on the Mac to expose BlueBubbles
4. **ngrok**: `ngrok http 1234` on the Mac

For the webhook direction (BlueBubbles → Backend), the backend must be publicly reachable — which it already is via `https://claude-agent-sdk-api.leanwise.ai`.

---

## Media Support

| Media Type | Supported | Notes |
|---|---|---|
| Images (JPEG, PNG, GIF, WebP) | Yes | Sent as vision content blocks (Claude can "see" them) |
| Documents (PDF, etc.) | Yes | Saved to file storage for agent tool access |
| Videos | Yes | Saved to file storage |
| Audio | Yes | Saved to file storage |
| Contact cards | No | Ignored |
| Location sharing | No | Ignored |

Attachments are downloaded from BlueBubbles via:
```
GET /api/v1/attachment/<guid>/download?password=<PASSWORD>
```

Max file size: 50 MB.

---

## Group Chats

The adapter supports group iMessage chats:
- **Chat ID**: The group chat GUID (e.g. `iMessage;+;chat123456`)
- **Sender**: Individual handle address within the group
- **Replies**: Sent to the group chat, visible to all participants

Each group chat gets its own session, separate from individual chats.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| Adapter not registered | Ensure `BLUEBUBBLES_PASSWORD` is set in `.env` and backend restarted |
| `Connection refused` to BlueBubbles | Check Mac is on, BlueBubbles is running, firewall allows port 1234 |
| No webhooks arriving | Register webhook (Step 4), check BlueBubbles webhook settings |
| Messages not sending | Enable Private API in BlueBubbles; check Messages.app is signed in |
| `private-api` method fails | Adapter auto-falls back to `apple-script`; check BlueBubbles Private API setup |
| Attachments fail to download | Check BlueBubbles server URL is reachable from backend |
| Tapback reactions triggering replies | Adapter filters these out (`associatedMessageType != null`) |
| Outgoing messages echoed | Adapter filters `isFromMe: true` messages |
| Mac goes to sleep | Disable sleep: System Settings > Energy > Prevent automatic sleeping |
| BlueBubbles crashes | Enable "Launch at Login" in BlueBubbles settings |

Check BlueBubbles server status:
```bash
curl "http://<mac-ip>:1234/api/v1/server/info?password=<PASSWORD>" | python -m json.tool
```

List registered webhooks:
```bash
curl "http://<mac-ip>:1234/api/v1/server/webhooks?password=<PASSWORD>" | python -m json.tool
```

---

## Architecture

| Component | File |
|---|---|
| Adapter | `backend/platforms/adapters/imessage.py` |
| Setup helper | `backend/platforms/adapters/imessage_setup.py` |
| Adapter registry | `backend/platforms/adapters/__init__.py` |
| Webhook routes | `backend/api/routers/webhooks.py` |
| Message worker | `backend/platforms/worker.py` |
| Media downloads | `backend/platforms/media.py` |
| Identity mapping | `backend/platforms/identity.py` |

---

## Cost Summary

| Item | Cost | Notes |
|---|---|---|
| BlueBubbles | Free | Open-source |
| Mac mini (used, M1) | ~$300-400 one-time | Minimum viable option |
| Mac mini (new, M4) | ~$500-600 one-time | Best long-term value |
| Cloud Mac (MacStadium) | ~$50-80/month | No hardware to manage |
| Electricity (Mac mini) | ~$3-5/month | ~10-15W idle |
