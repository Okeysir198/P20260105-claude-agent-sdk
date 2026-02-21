"""
WhatsApp Cloud API integration tests — verifies real connection works.

Run: pytest tests/test_13_whatsapp.py -v
"""

import os
import time
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

    @pytest.mark.asyncio
    async def test_webhook_verify_ok(self):
        async with httpx.AsyncClient(timeout=10.0) as c:
            resp = await c.get(
                "https://example.com/api/v1/webhooks/whatsapp",
                params={"hub.mode": "subscribe", "hub.verify_token": _VERIFY, "hub.challenge": "test_ok"},
            )
        assert resp.status_code == 200
        assert resp.text == "test_ok"

    @pytest.mark.asyncio
    async def test_webhook_rejects_bad_token(self):
        async with httpx.AsyncClient(timeout=10.0) as c:
            resp = await c.get(
                "https://example.com/api/v1/webhooks/whatsapp",
                params={"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "x"},
            )
        assert resp.status_code == 403
