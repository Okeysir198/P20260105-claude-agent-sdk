"""Tests for media processing tools (OCR, STT, TTS).

Tests the MCP server integration with local Docker services:
- Ollama GLM-OCR on port 18013
- Whisper V3 Turbo STT on port 18050
- Kokoro TTS on port 18034
"""
import os
import pytest
from pathlib import Path

os.environ.setdefault("API_KEY", "test-api-key-for-testing")

import httpx

from agent.tools.media.config import (
    OCR_SERVICE_URL,
    STT_WHISPER_URL,
    TTS_KOKORO_URL,
    TTS_VOICES,
    STT_ENGINE_DEFINITIONS,
    TTS_ENGINE_DEFINITIONS,
    get_service_url,
    get_voices_for_engine,
)
from agent.tools.media.clients.base_client import BaseServiceClient
from agent.tools.media.clients.ocr_client import OCRClient
from agent.tools.media.clients.stt_client import STTClient
from agent.tools.media.clients.tts_client import TTSClient
from agent.core.file_storage import FileStorage
from agent.core.agent_options import (
    __all__ as agent_options_all,
    MEDIA_TOOLS_AVAILABLE,
    set_media_tools_username,
    set_media_tools_session_id,
)

# Conditionally import MCP server (may not be available)
try:
    from agent.tools.media.mcp_server import (
        media_tools_server,
        set_username,
        get_username,
        reset_username,
        set_session_id,
        get_session_id,
        reset_session_id,
    )
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

try:
    from agent.tools.media.ocr_tools import perform_ocr
    OCR_TOOL_AVAILABLE = True
except ImportError:
    OCR_TOOL_AVAILABLE = False

try:
    from agent.tools.media.stt_tools import list_stt_engines, transcribe_audio
    STT_TOOLS_AVAILABLE = True
except ImportError:
    STT_TOOLS_AVAILABLE = False

try:
    from agent.tools.media.tts_tools import list_tts_engines, synthesize_speech
    TTS_TOOLS_AVAILABLE = True
except ImportError:
    TTS_TOOLS_AVAILABLE = False


# -- Markers for conditional skipping --
requires_mcp = pytest.mark.skipif(not MCP_AVAILABLE, reason="Media tools MCP server not available")


class TestMediaToolsConfig:
    """Test media tools configuration."""

    def test_config_values(self):
        """Test that config constants have expected default values."""
        assert OCR_SERVICE_URL == "http://localhost:18013"
        assert STT_WHISPER_URL == "http://localhost:18050"
        assert TTS_KOKORO_URL == "http://localhost:18034"
        assert "kokoro" in TTS_VOICES
        assert len(TTS_VOICES["kokoro"]) > 0

    def test_get_service_url(self):
        """Test get_service_url returns correct URLs and raises for unknown engines."""
        assert get_service_url("whisper_v3_turbo") == "http://localhost:18050"
        assert get_service_url("kokoro") == "http://localhost:18034"
        assert get_service_url("nemotron_speech") == "http://localhost:18052"

        with pytest.raises(ValueError):
            get_service_url("unknown_engine")

    def test_get_voices_for_engine(self):
        """Test get_voices_for_engine returns expected voices per engine."""
        assert "af_heart" in get_voices_for_engine("kokoro")
        assert "F1" in get_voices_for_engine("supertonic_v1_1")
        assert "custom" in get_voices_for_engine("chatterbox_turbo")


class TestBaseClient:
    """Test BaseServiceClient class."""

    @pytest.mark.asyncio
    async def test_client_initialization_with_api_key(self):
        """Test that base client initializes with URL and optional API key."""
        client = BaseServiceClient("http://localhost:18013", api_key="test_key")
        assert client.base_url == "http://localhost:18013"
        assert client.api_key == "test_key"
        await client.close()

    @pytest.mark.asyncio
    async def test_client_initialization_without_api_key(self):
        """Test client defaults API key to None."""
        client = BaseServiceClient("http://localhost:18013")
        assert client.base_url == "http://localhost:18013"
        assert client.api_key is None
        await client.close()


class TestOCRClient:
    """Test OCR client."""

    @pytest.mark.asyncio
    async def test_ocr_client_initialization(self):
        """Test OCR client defaults to correct service URL."""
        client = OCRClient()
        assert client.base_url == "http://localhost:18013"
        await client.close()

    def test_get_content_type(self):
        """Test MIME type detection for different file formats."""
        from agent.tools.media.clients.base_client import get_mime_type
        expected = {
            "test.pdf": "application/pdf",
            "test.png": "image/png",
            "test.jpg": "image/jpeg",
            "test.jpeg": "image/jpeg",
            "test.webp": "image/webp",
        }
        for filename, mime_type in expected.items():
            assert get_mime_type(filename) == mime_type


class TestSTTClient:
    """Test STT client."""

    @pytest.mark.asyncio
    async def test_stt_client_initialization(self):
        """Test STT client initialization for different engines."""
        whisper = STTClient("whisper_v3_turbo")
        assert whisper.base_url == "http://localhost:18050"
        await whisper.close()

        nemotron = STTClient("nemotron_speech")
        assert nemotron.base_url == "http://localhost:18052"
        await nemotron.close()

    def test_get_audio_content_type(self):
        """Test MIME type detection for audio files."""
        from agent.tools.media.clients.base_client import get_mime_type
        expected = {
            "test.wav": "audio/wav",
            "test.mp3": "audio/mpeg",
            "test.m4a": "audio/mp4",
            "test.flac": "audio/flac",
        }
        for filename, mime_type in expected.items():
            assert get_mime_type(filename, fallback="audio/wav") == mime_type


class TestTTSClient:
    """Test TTS client."""

    @pytest.mark.asyncio
    async def test_tts_client_initialization(self):
        """Test TTS client initialization for different engines."""
        kokoro = TTSClient("kokoro")
        assert kokoro.base_url == "http://localhost:18034"
        assert kokoro.api_key is None
        await kokoro.close()

        supertonic = TTSClient("supertonic_v1_1")
        assert supertonic.base_url == "http://localhost:18030"
        await supertonic.close()

    def test_list_voices(self):
        """Test listing voices returns non-empty list with known voice IDs."""
        client = TTSClient("kokoro")
        voices = client.list_voices()
        assert len(voices) > 0
        assert voices[0]["id"] in ["af_heart", "af_sky", "af_bella"]


class TestMCPServer:
    """Test MCP server registration and context management."""

    @requires_mcp
    def test_mcp_server_import(self):
        """Test that MCP server and context functions are available."""
        assert media_tools_server is not None
        assert callable(set_username)
        assert callable(get_username)
        assert callable(set_session_id)
        assert callable(get_session_id)

    @requires_mcp
    def test_username_context_set_get_reset(self):
        """Test username context lifecycle: set, get, reset, and error after reset."""
        token = set_username("test_user")
        assert get_username() == "test_user"

        reset_username(token)
        with pytest.raises(ValueError, match="Username not set"):
            get_username()

    @requires_mcp
    def test_username_environment_fallback(self):
        """Test that MEDIA_USERNAME env var is used as fallback."""
        os.environ["MEDIA_USERNAME"] = "env_user"
        try:
            assert get_username() == "env_user"
        finally:
            os.environ.pop("MEDIA_USERNAME", None)

    @requires_mcp
    def test_session_id_context_set_get_reset(self):
        """Test session_id context lifecycle: set, get, reset, and error after reset."""
        token = set_session_id("test-session-abc123")
        assert get_session_id() == "test-session-abc123"

        reset_session_id(token)
        with pytest.raises(ValueError, match="Session ID not set"):
            get_session_id()


class TestToolRegistration:
    """Test that tools are properly registered."""

    @pytest.mark.skipif(not OCR_TOOL_AVAILABLE, reason="OCR tool not available")
    def test_perform_ocr_tool_exists(self):
        """Test perform_ocr tool is registered with correct name."""
        assert hasattr(perform_ocr, "name")
        assert perform_ocr.name == "perform_ocr"

    @pytest.mark.skipif(not STT_TOOLS_AVAILABLE, reason="STT tools not available")
    def test_stt_tools_exist(self):
        """Test STT tools are importable."""
        assert list_stt_engines is not None
        assert transcribe_audio is not None

    @pytest.mark.skipif(not TTS_TOOLS_AVAILABLE, reason="TTS tools not available")
    def test_tts_tools_exist(self):
        """Test TTS tools are importable."""
        assert list_tts_engines is not None
        assert synthesize_speech is not None


class TestAgentOptionsIntegration:
    """Test integration with agent_options.py."""

    def test_media_tools_exports(self):
        """Test that media tools functions are exported in __all__."""
        assert "set_media_tools_username" in agent_options_all
        assert "set_media_tools_session_id" in agent_options_all

    def test_set_media_tools_username(self):
        """Test set_media_tools_username is callable and does not raise."""
        assert callable(set_media_tools_username)
        set_media_tools_username("test_user")

    def test_set_media_tools_session_id(self):
        """Test set_media_tools_session_id is callable and does not raise."""
        assert callable(set_media_tools_session_id)
        set_media_tools_session_id("test_session_abc123")

    def test_media_tools_availability_flag(self):
        """Test MEDIA_TOOLS_AVAILABLE is a boolean."""
        assert isinstance(MEDIA_TOOLS_AVAILABLE, bool)


class TestFileStorageIntegration:
    """Test integration with FileStorage."""

    def test_file_storage_initialization(self):
        """Test FileStorage creates directories on init."""
        storage = FileStorage(username="test_user", session_id="test_session")
        assert storage._username == "test_user"
        assert storage._session_id == "test_session"
        assert storage.get_input_dir().exists()
        assert storage.get_output_dir().exists()

    def test_file_storage_sanitize_filename(self):
        """Test filename sanitization preserves safe names and blocks traversal."""
        storage = FileStorage(username="test_user", session_id="test_session")

        assert storage.sanitize_filename("test.pdf") == "test.pdf"

        sanitized = storage.sanitize_filename("my document.pdf")
        assert "pdf" in sanitized
        assert "document" in sanitized

        assert "etc" not in storage.sanitize_filename("../../etc/passwd")


SERVICE_HEALTH_ENDPOINTS = [
    ("OCR", "http://localhost:18013/health"),
    ("STT", "http://localhost:18050/health"),
    ("TTS", "http://localhost:18034/health"),
]


class TestServiceHealthChecks:
    """Test health checks for media services.

    These tests require services to be running and will be skipped otherwise.
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("service_name,url", SERVICE_HEALTH_ENDPOINTS)
    async def test_service_health(self, service_name, url):
        """Test that a media service health endpoint returns 200."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                assert response.status_code == 200
        except (httpx.ConnectError, httpx.ConnectTimeout):
            pytest.skip(f"{service_name} service not running")


class TestEngineDefinitions:
    """Test engine definitions from config."""

    def test_stt_engine_definitions(self):
        """Test STT engine definitions contain expected engines."""
        assert len(STT_ENGINE_DEFINITIONS) == 2
        assert STT_ENGINE_DEFINITIONS[0]["id"] == "whisper_v3_turbo"
        assert STT_ENGINE_DEFINITIONS[1]["id"] == "nemotron_speech"

    def test_tts_engine_definitions(self):
        """Test TTS engine definitions contain expected engines."""
        assert len(TTS_ENGINE_DEFINITIONS) == 3
        engine_ids = [e["id"] for e in TTS_ENGINE_DEFINITIONS]
        assert "kokoro" in engine_ids
        assert "supertonic_v1_1" in engine_ids
        assert "chatterbox_turbo" in engine_ids


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
