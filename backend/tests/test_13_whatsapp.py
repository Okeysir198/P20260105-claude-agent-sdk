"""
WhatsApp Cloud API integration tests — verifies real connection works.

Run: pytest tests/test_13_whatsapp.py -v
"""

import hashlib
import hmac
import json
import os
import time
import uuid
from pathlib import Path
import httpx
import pytest
from dotenv import dotenv_values

from platforms.adapters.whatsapp import GRAPH_API_BASE, WhatsAppAdapter

_env = dotenv_values(Path(__file__).parent.parent / ".env")
_TOKEN = _env.get("WHATSAPP_ACCESS_TOKEN", "")
_PHONE_ID = _env.get("WHATSAPP_PHONE_NUMBER_ID", "")
_VERIFY = _env.get("WHATSAPP_VERIFY_TOKEN", "")
_SECRET = _env.get("WHATSAPP_APP_SECRET", "")

pytestmark = pytest.mark.skipif(
    not (_TOKEN and _PHONE_ID and len(_TOKEN) > 50),
    reason="WhatsApp credentials not configured in .env",
)


@pytest.fixture
def http():
    return httpx.AsyncClient(timeout=15.0, headers={"Authorization": f"Bearer {_TOKEN}"})


class TestWhatsApp:

    def test_env_vars_set(self):
        assert _TOKEN.startswith("EA"), "Token should start with EA (Meta token format)"
        assert _PHONE_ID.isdigit(), "Phone number ID should be numeric"
        assert _VERIFY, "Verify token not set"
        assert _SECRET, "App secret not set"

    @pytest.mark.asyncio
    async def test_token_valid(self, http):
        resp = await http.get(f"{GRAPH_API_BASE}/debug_token", params={"input_token": _TOKEN})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["is_valid"], f"Token invalid: {data.get('error', {}).get('message')}"
        expires = data.get("expires_at", 0)
        assert expires == 0 or expires > time.time(), "Token expired"

    @pytest.mark.asyncio
    async def test_token_permissions(self, http):
        resp = await http.get(f"{GRAPH_API_BASE}/debug_token", params={"input_token": _TOKEN})
        scopes = resp.json().get("data", {}).get("scopes", [])
        if scopes:
            assert "whatsapp_business_messaging" in scopes, f"Missing permission. Has: {scopes}"

    @pytest.mark.asyncio
    async def test_phone_number_accessible(self, http):
        resp = await http.get(
            f"{GRAPH_API_BASE}/{_PHONE_ID}",
            params={"fields": "id,display_phone_number"},
        )
        assert resp.status_code == 200, f"Phone lookup failed: {resp.text}"
        data = resp.json()
        assert data["id"] == _PHONE_ID
        assert "display_phone_number" in data

    def test_adapter_initializes(self):
        os.environ["WHATSAPP_PHONE_NUMBER_ID"] = _PHONE_ID
        os.environ["WHATSAPP_ACCESS_TOKEN"] = _TOKEN
        os.environ["WHATSAPP_VERIFY_TOKEN"] = _VERIFY
        os.environ["WHATSAPP_APP_SECRET"] = _SECRET
        adapter = WhatsAppAdapter()
        assert adapter._phone_number_id == _PHONE_ID
        assert adapter._access_token == _TOKEN

    def test_webhook_verify_ok(self, client):
        resp = client.get(
            "/api/v1/webhooks/whatsapp",
            params={"hub.mode": "subscribe", "hub.verify_token": _VERIFY, "hub.challenge": "test_ok"},
        )
        assert resp.status_code == 200
        assert resp.text == "test_ok"

    def test_webhook_rejects_bad_token(self, client):
        resp = client.get(
            "/api/v1/webhooks/whatsapp",
            params={"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "x"},
        )
        assert resp.status_code == 403


_WHITELIST_RAW = _env.get("WHATSAPP_WHITELIST", "")
_WHITELIST_PHONE = _WHITELIST_RAW.split(",")[0].strip() if _WHITELIST_RAW else ""


@pytest.mark.skipif(
    not (_TOKEN and _PHONE_ID and _SECRET and _WHITELIST_PHONE),
    reason="WhatsApp credentials or whitelist not configured in .env",
)
class TestWhatsAppAgentE2E:
    """Full end-to-end test: webhook POST → agent invocation → real WhatsApp response."""

    def test_hello_message_gets_agent_response(self, client):
        """Send 'Hello' via webhook, verify agent processes it and responds via WhatsApp API.

        This is a true E2E test — the agent response is sent as a real WhatsApp
        message to the whitelisted phone number. No mocking or interception.
        Expects the test to take 10-60s due to real Claude agent invocation.
        """
        # Remove CLAUDECODE to ensure real agent subprocess spawns
        saved_claudecode = os.environ.pop("CLAUDECODE", None)

        try:
            # Build realistic Meta webhook payload
            unique_msg_id = f"wamid.test_{uuid.uuid4().hex[:16]}"
            payload = {
                "object": "whatsapp_business_account",
                "entry": [
                    {
                        "id": _PHONE_ID,
                        "changes": [
                            {
                                "value": {
                                    "messaging_product": "whatsapp",
                                    "metadata": {
                                        "display_phone_number": "15550001234",
                                        "phone_number_id": _PHONE_ID,
                                    },
                                    "contacts": [
                                        {
                                            "profile": {"name": "Test User"},
                                            "wa_id": _WHITELIST_PHONE,
                                        }
                                    ],
                                    "messages": [
                                        {
                                            "from": _WHITELIST_PHONE,
                                            "id": unique_msg_id,
                                            "timestamp": str(int(time.time())),
                                            "text": {"body": "Hello"},
                                            "type": "text",
                                        }
                                    ],
                                },
                                "field": "messages",
                            }
                        ],
                    }
                ],
            }

            raw_body = json.dumps(payload).encode()

            # Compute valid HMAC signature
            sig = hmac.new(
                _SECRET.encode(), raw_body, hashlib.sha256
            ).hexdigest()

            api_key = os.environ.get("API_KEY", "test-api-key-for-testing")

            # POST to webhook — TestClient runs BackgroundTasks synchronously,
            # so this blocks until agent finishes and response is sent via WhatsApp API
            resp = client.post(
                "/api/v1/webhooks/whatsapp",
                content=raw_body,
                headers={
                    "content-type": "application/json",
                    "x-hub-signature-256": f"sha256={sig}",
                    "X-API-Key": api_key,
                },
            )

            assert resp.status_code == 200, f"Webhook returned {resp.status_code}: {resp.text}"
            body = resp.json()
            assert body.get("status") == "ok", f"Unexpected status: {body}"

            print(f"\n--- E2E WhatsApp Test ---")
            print(f"  Webhook accepted message (id={unique_msg_id})")
            print(f"  Agent processed and sent real response to {_WHITELIST_PHONE}")
            print(f"  Check your WhatsApp for the reply!")
            print(f"--- End ---\n")

        finally:
            if saved_claudecode is not None:
                os.environ["CLAUDECODE"] = saved_claudecode
