"""Tests for media processing tools (OCR, STT, TTS).

Tests the MCP server integration with local Docker services:
- Ollama GLM-OCR on port 18013
- Whisper V3 Turbo STT on port 18050
- Kokoro TTS on port 18034
"""
import os
import pytest
from pathlib import Path

# Set test environment
os.environ.setdefault("API_KEY", "test-api-key-for-testing")


class TestMediaToolsConfig:
    """Test media tools configuration."""

    def test_config_import(self):
        """Test that config module can be imported."""
        from agent.tools.media.config import (
            OCR_SERVICE_URL,
            STT_WHISPER_URL,
            TTS_KOKORO_URL,
            TTS_VOICES,
            get_service_url,
        )
        assert OCR_SERVICE_URL == "http://localhost:18013"
        assert STT_WHISPER_URL == "http://localhost:18050"
        assert TTS_KOKORO_URL == "http://localhost:18034"
        assert "kokoro" in TTS_VOICES
        assert len(TTS_VOICES["kokoro"]) > 0

    def test_get_service_url(self):
        """Test get_service_url function."""
        from agent.tools.media.config import get_service_url

        assert get_service_url("whisper_v3_turbo") == "http://localhost:18050"
        assert get_service_url("kokoro") == "http://localhost:18034"
        assert get_service_url("nemotron_speech") == "http://localhost:18052"

        with pytest.raises(ValueError):
            get_service_url("unknown_engine")

    def test_get_voices_for_engine(self):
        """Test get_voices_for_engine function."""
        from agent.tools.media.config import get_voices_for_engine

        kokoro_voices = get_voices_for_engine("kokoro")
        assert "af_heart" in kokoro_voices

        supertonic_voices = get_voices_for_engine("supertonic_v1_1")
        assert "F1" in supertonic_voices

        chatterbox_voices = get_voices_for_engine("chatterbox_turbo")
        assert "custom" in chatterbox_voices


class TestBaseClient:
    """Test BaseServiceClient class."""

    @pytest.mark.asyncio
    async def test_client_initialization(self):
        """Test that base client initializes correctly."""
        from agent.tools.media.clients.base_client import BaseServiceClient

        client = BaseServiceClient("http://localhost:18013", api_key="test_key")
        assert client.base_url == "http://localhost:18013"
        assert client.api_key == "test_key"
        await client.close()

    @pytest.mark.asyncio
    async def test_client_without_api_key(self):
        """Test client initialization without API key."""
        from agent.tools.media.clients.base_client import BaseServiceClient

        client = BaseServiceClient("http://localhost:18013")
        assert client.base_url == "http://localhost:18013"
        assert client.api_key is None
        await client.close()


class TestOCRClient:
    """Test OCR client."""

    @pytest.mark.asyncio
    async def test_ocr_client_initialization(self):
        """Test OCR client initialization."""
        from agent.tools.media.clients.ocr_client import OCRClient

        client = OCRClient()
        assert client.base_url == "http://localhost:18013"
        await client.close()

    def test_get_content_type(self):
        """Test MIME type detection for different file formats."""
        from agent.tools.media.clients.ocr_client import OCRClient

        client = OCRClient()

        assert client._get_content_type(Path("test.pdf")) == "application/pdf"
        assert client._get_content_type(Path("test.png")) == "image/png"
        assert client._get_content_type(Path("test.jpg")) == "image/jpeg"
        assert client._get_content_type(Path("test.jpeg")) == "image/jpeg"
        assert client._get_content_type(Path("test.webp")) == "image/webp"


class TestSTTClient:
    """Test STT client."""

    @pytest.mark.asyncio
    async def test_stt_client_initialization(self):
        """Test STT client initialization for different engines."""
        from agent.tools.media.clients.stt_client import STTClient

        whisper_client = STTClient("whisper_v3_turbo")
        assert whisper_client.base_url == "http://localhost:18050"
        await whisper_client.close()

        nemotron_client = STTClient("nemotron_speech")
        assert nemotron_client.base_url == "http://localhost:18052"
        await nemotron_client.close()

    def test_get_audio_content_type(self):
        """Test MIME type detection for audio files."""
        from agent.tools.media.clients.stt_client import STTClient

        client = STTClient("whisper_v3_turbo")

        assert client._get_audio_content_type(Path("test.wav")) == "audio/wav"
        assert client._get_audio_content_type(Path("test.mp3")) == "audio/mpeg"
        assert client._get_audio_content_type(Path("test.m4a")) == "audio/mp4"
        assert client._get_audio_content_type(Path("test.flac")) == "audio/flac"


class TestTTSClient:
    """Test TTS client."""

    @pytest.mark.asyncio
    async def test_tts_client_initialization(self):
        """Test TTS client initialization for different engines."""
        from agent.tools.media.clients.tts_client import TTSClient

        kokoro_client = TTSClient("kokoro")
        assert kokoro_client.base_url == "http://localhost:18034"
        assert kokoro_client.api_key is None
        await kokoro_client.close()

        supertonic_client = TTSClient("supertonic_v1_1")
        assert supertonic_client.base_url == "http://localhost:18030"
        # Supertonic uses API key
        await supertonic_client.close()

    def test_list_voices(self):
        """Test listing voices for different engines."""
        from agent.tools.media.clients.tts_client import TTSClient

        kokoro_client = TTSClient("kokoro")
        voices = kokoro_client.list_voices()
        assert len(voices) > 0
        assert voices[0]["id"] in ["af_heart", "af_sky", "af_bella"]


class TestMCPServer:
    """Test MCP server registration and tools."""

    def test_mcp_server_import(self):
        """Test that MCP server can be imported."""
        try:
            from agent.tools.media.mcp_server import (
                media_tools_server,
                set_username,
                get_username,
                set_session_id,
                get_session_id,
            )
            assert media_tools_server is not None
            assert callable(set_username)
            assert callable(get_username)
            assert callable(set_session_id)
            assert callable(get_session_id)
        except ImportError as e:
            pytest.skip(f"Media tools MCP server not available: {e}")

    def test_context_username_functions(self):
        """Test username context management functions."""
        try:
            from agent.tools.media.mcp_server import set_username, get_username, reset_username
        except ImportError:
            pytest.skip("Media tools MCP server not available")
            return

        # Test set and get username
        token = set_username("test_user")
        assert get_username() == "test_user"

        # Test reset
        reset_username(token)

        # After reset, should raise ValueError
        with pytest.raises(ValueError, match="Username not set"):
            get_username()

    def test_environment_fallback(self):
        """Test that environment variable MEDIA_USERNAME is used as fallback."""
        try:
            from agent.tools.media.mcp_server import get_username
        except ImportError:
            pytest.skip("Media tools MCP server not available")
            return

        # Set environment variable
        os.environ["MEDIA_USERNAME"] = "env_user"

        try:
            # Should get username from environment
            assert get_username() == "env_user"
        finally:
            # Clean up
            os.environ.pop("MEDIA_USERNAME", None)

    def test_context_session_id_functions(self):
        """Test session_id context management functions."""
        try:
            from agent.tools.media.mcp_server import set_session_id, get_session_id, reset_session_id
        except ImportError:
            pytest.skip("Media tools MCP server not available")
            return

        # Test set and get session_id
        token = set_session_id("test-session-abc123")
        assert get_session_id() == "test-session-abc123"

        # Test reset
        reset_session_id(token)

        # After reset, should raise ValueError
        with pytest.raises(ValueError, match="Session ID not set"):
            get_session_id()


class TestToolRegistration:
    """Test that tools are properly registered."""

    def test_perform_ocr_tool_exists(self):
        """Test perform_ocr tool is importable."""
        try:
            from agent.tools.media.ocr_tools import perform_ocr
            assert perform_ocr is not None
            # Tool is wrapped by @tool decorator, check it has the right attributes
            assert hasattr(perform_ocr, "name")
            assert perform_ocr.name == "perform_ocr"
        except ImportError as e:
            pytest.skip(f"OCR tool not available: {e}")

    def test_stt_tools_exist(self):
        """Test STT tools are importable."""
        try:
            from agent.tools.media.stt_tools import list_stt_engines, transcribe_audio
            assert list_stt_engines is not None
            assert transcribe_audio is not None
        except ImportError as e:
            pytest.skip(f"STT tools not available: {e}")

    def test_tts_tools_exist(self):
        """Test TTS tools are importable."""
        try:
            from agent.tools.media.tts_tools import list_tts_engines, synthesize_speech
            assert list_tts_engines is not None
            assert synthesize_speech is not None
        except ImportError as e:
            pytest.skip(f"TTS tools not available: {e}")


class TestAgentOptionsIntegration:
    """Test integration with agent_options.py."""

    def test_media_tools_in_all(self):
        """Test that set_media_tools_username and set_media_tools_session_id are in __all__."""
        from agent.core.agent_options import __all__

        assert "set_media_tools_username" in __all__
        assert "set_media_tools_session_id" in __all__

    def test_set_media_tools_username_function(self):
        """Test set_media_tools_username function exists."""
        from agent.core.agent_options import set_media_tools_username

        assert callable(set_media_tools_username)

        # Should not raise error even if media tools not available
        set_media_tools_username("test_user")

    def test_set_media_tools_session_id_function(self):
        """Test set_media_tools_session_id function exists."""
        from agent.core.agent_options import set_media_tools_session_id

        assert callable(set_media_tools_session_id)

        # Should not raise error even if media tools not available
        set_media_tools_session_id("test_session_abc123")

    def test_media_tools_availability_flag(self):
        """Test MEDIA_TOOLS_AVAILABLE flag."""
        from agent.core.agent_options import MEDIA_TOOLS_AVAILABLE

        # Should be boolean
        assert isinstance(MEDIA_TOOLS_AVAILABLE, bool)


class TestFileStorageIntegration:
    """Test integration with FileStorage."""

    def test_file_storage_import(self):
        """Test FileStorage can be imported for media tools."""
        from agent.core.file_storage import FileStorage

        assert FileStorage is not None

    def test_file_storage_initialization(self):
        """Test FileStorage initialization."""
        from agent.core.file_storage import FileStorage

        storage = FileStorage(username="test_user", session_id="test_session")
        assert storage._username == "test_user"
        assert storage._session_id == "test_session"

        # Check directories exist
        assert storage.get_input_dir().exists()
        assert storage.get_output_dir().exists()

    def test_file_storage_sanitize_filename(self):
        """Test filename sanitization."""
        from agent.core.file_storage import FileStorage

        storage = FileStorage(username="test_user", session_id="test_session")

        # Test sanitization
        assert storage.sanitize_filename("test.pdf") == "test.pdf"
        # Spaces are removed in current implementation
        sanitized = storage.sanitize_filename("my document.pdf")
        assert "pdf" in sanitized
        assert "document" in sanitized
        # Path traversal should be blocked
        assert "etc" not in storage.sanitize_filename("../../etc/passwd")


class TestServiceHealthChecks:
    """Test health checks for media services.

    These tests require services to be running. They will be skipped if
    services are unavailable.
    """

    @pytest.mark.asyncio
    async def test_ocr_service_health(self):
        """Test OCR service health check."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("http://localhost:18013/health")
                assert response.status_code == 200
        except (httpx.ConnectError, httpx.ConnectTimeout):
            pytest.skip("OCR service not running")

    @pytest.mark.asyncio
    async def test_stt_service_health(self):
        """Test STT service health check."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("http://localhost:18050/health")
                assert response.status_code == 200
        except (httpx.ConnectError, httpx.ConnectTimeout):
            pytest.skip("STT service not running")

    @pytest.mark.asyncio
    async def test_tts_service_health(self):
        """Test TTS service health check."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("http://localhost:18034/health")
                assert response.status_code == 200
        except (httpx.ConnectError, httpx.ConnectTimeout):
            pytest.skip("TTS service not running")


class TestToolsWithMockServices:
    """Test tools with engine definitions from config."""

    def test_stt_engine_definitions(self):
        """Test STT engine definitions from config."""
        from agent.tools.media.config import STT_ENGINE_DEFINITIONS

        assert len(STT_ENGINE_DEFINITIONS) == 2
        assert STT_ENGINE_DEFINITIONS[0]["id"] == "whisper_v3_turbo"
        assert STT_ENGINE_DEFINITIONS[1]["id"] == "nemotron_speech"

    def test_tts_engine_definitions(self):
        """Test TTS engine definitions from config."""
        from agent.tools.media.config import TTS_ENGINE_DEFINITIONS

        assert len(TTS_ENGINE_DEFINITIONS) == 3
        engine_ids = [e["id"] for e in TTS_ENGINE_DEFINITIONS]
        assert "kokoro" in engine_ids
        assert "supertonic_v1_1" in engine_ids
        assert "chatterbox_turbo" in engine_ids


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
