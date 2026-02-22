"""Standalone tests for each media tool.

Tests each tool (OCR, STT, TTS) independently by calling their handlers directly
and verifying outputs thoroughly including file contents, error formats, and edge cases.

Tools return MCP-compliant format:
  Success: {"content": [{"type": "text", "text": "<json string>"}]}
  Error:   {"content": [{"type": "text", "text": "error msg"}], "is_error": True}
"""
import json
import os
import shutil
import pytest
from pathlib import Path

os.environ.setdefault("API_KEY", "test-api-key-for-testing")

import httpx

from media_tools.file_storage import FileStorage
from media_tools.context import set_username, set_session_id
from media_tools.stt_tools import transcribe_audio, list_stt_engines
from media_tools.tts_tools import synthesize_speech, list_tts_engines
from media_tools.ocr_tools import perform_ocr


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_mcp_result(result: dict) -> dict:
    """Extract and parse JSON data from MCP tool result format."""
    assert "content" in result, f"Result missing 'content' key: {result}"
    assert isinstance(result["content"], list) and len(result["content"]) > 0
    assert result["content"][0]["type"] == "text"
    return json.loads(result["content"][0]["text"])


def assert_mcp_error(result: dict, expected_substring: str = ""):
    """Assert the result is a well-formed MCP error containing expected text."""
    assert result.get("is_error") is True
    assert "content" in result
    assert isinstance(result["content"], list)
    assert len(result["content"]) > 0
    assert result["content"][0]["type"] == "text"
    if expected_substring:
        assert expected_substring in result["content"][0]["text"], (
            f"Expected '{expected_substring}' in error: {result['content'][0]['text']}"
        )


async def check_service_health(url: str, skip_reason: str):
    """Skip the test if a service health endpoint is not reachable."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                pytest.skip(f"{skip_reason} (status {resp.status_code})")
    except Exception:
        pytest.skip(skip_reason)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def media_context():
    """Set up media tools context (username + session) and clean up after test.

    Usage:
        storage = media_context("my_session_id")
        # storage.get_input_dir(), storage.get_output_dir() ready to use

    Note: Does not call reset_session_id() because pytest-asyncio runs each
    async test in its own context, making token.reset() fail across contexts.
    Context values are naturally scoped per-test and do not leak.
    """
    # Ensure DATA_DIR is set for the plugin's FileStorage
    if "DATA_DIR" not in os.environ:
        os.environ["DATA_DIR"] = str(Path(__file__).parent.parent / "data")
    storages = []

    def _setup(session_id: str) -> FileStorage:
        username = "test_user"
        set_username(username)
        set_session_id(session_id)
        storage = FileStorage(username=username, session_id=session_id)
        storages.append(storage)
        return storage

    yield _setup

    for storage in storages:
        session_dir = storage.get_session_dir()
        if session_dir.exists():
            shutil.rmtree(session_dir)


@pytest.fixture
async def kokoro_service():
    """Skip test if Kokoro TTS service is not running."""
    await check_service_health(
        "http://localhost:18034/health",
        "Kokoro TTS service not running",
    )


@pytest.fixture
async def supertonic_service():
    """Skip test if Supertonic TTS service is not running."""
    await check_service_health(
        "http://localhost:18030/health",
        "Supertonic TTS service not running",
    )


@pytest.fixture
async def whisper_service():
    """Skip test if Whisper STT service is not running."""
    await check_service_health(
        "http://localhost:18050/health",
        "Whisper STT service not running",
    )


@pytest.fixture
async def ocr_service():
    """Skip test if OCR service is not running or VLLM_API_KEY is unset."""
    if not os.environ.get("VLLM_API_KEY"):
        pytest.skip("OCR service requires VLLM_API_KEY environment variable")
    await check_service_health(
        "http://localhost:18013/health",
        "OCR service not running",
    )


# ---------------------------------------------------------------------------
# List engines tests
# ---------------------------------------------------------------------------

class TestListEnginesTools:
    """Test list engines tools independently."""

    @pytest.mark.asyncio
    async def test_list_stt_engines_tool(self):
        """Test list_stt_engines returns correct engines with required fields."""
        result = parse_mcp_result(await list_stt_engines({}))

        engines = result["engines"]
        assert len(engines) == 2

        for engine in engines:
            for key in ("id", "name", "url", "status"):
                assert key in engine

        assert engines[0]["id"] == "whisper_v3_turbo"
        assert engines[1]["id"] == "nemotron_speech"

    @pytest.mark.asyncio
    async def test_list_tts_engines_tool(self):
        """Test list_tts_engines returns correct engines with required fields."""
        result = parse_mcp_result(await list_tts_engines({}))

        engines = result["engines"]
        assert len(engines) == 3

        for engine in engines:
            for key in ("id", "name", "url", "output_format", "voices"):
                assert key in engine

        engine_ids = [e["id"] for e in engines]
        assert "kokoro" in engine_ids
        assert "supertonic_v1_1" in engine_ids
        assert "chatterbox_turbo" in engine_ids


# ---------------------------------------------------------------------------
# TTS standalone tests
# ---------------------------------------------------------------------------

class TestTTSToolStandalone:
    """Test TTS tool independently."""

    @pytest.mark.asyncio
    async def test_tts_kokoro_synthesis(self, media_context, kokoro_service):
        """Test TTS synthesis with Kokoro engine, verify WAV output and headers."""
        storage = media_context("test_tts_kokoro")

        raw = await synthesize_speech({
            "text": "Hello world",
            "engine": "kokoro",
            "voice": "af_heart",
            "speed": 1.0,
        })
        assert not raw.get("is_error"), f"TTS returned error: {raw}"
        result = parse_mcp_result(raw)

        # Verify all expected keys and values
        for key in ("audio_path", "download_url", "format", "engine", "voice", "text", "duration_ms", "file_size_bytes"):
            assert key in result, f"Missing key: {key}"

        assert result["format"] == "wav"
        assert result["engine"] == "kokoro"
        assert result["voice"] == "af_heart"
        assert result["text"] == "Hello world"
        assert result["file_size_bytes"] > 1000
        assert result["duration_ms"] >= 0

        # Verify audio file on disk with WAV headers
        audio_filename = result["audio_path"].split("/")[-1]
        full_path = storage.get_output_dir() / audio_filename
        assert full_path.exists(), f"Audio file should exist: {full_path}"

        audio_bytes = full_path.read_bytes()
        assert audio_bytes[:4] == b"RIFF", "WAV file should start with RIFF header"
        assert audio_bytes[8:12] == b"WAVE", "WAV file should contain WAVE marker"

    @pytest.mark.asyncio
    async def test_tts_supertonic_synthesis(self, media_context, supertonic_service):
        """Test TTS synthesis with Supertonic engine, verify output."""
        storage = media_context("test_tts_supertonic")

        raw = await synthesize_speech({
            "text": "Hello world",
            "engine": "supertonic_v1_1",
            "voice": "F1",
            "speed": 1.0,
        })
        assert not raw.get("is_error"), f"TTS returned error: {raw}"
        result = parse_mcp_result(raw)

        for key in ("audio_path", "download_url", "format", "engine", "file_size_bytes"):
            assert key in result, f"Missing key: {key}"

        assert result["engine"] == "supertonic_v1_1"
        assert result["file_size_bytes"] > 1000

        audio_filename = result["audio_path"].split("/")[-1]
        full_path = storage.get_output_dir() / audio_filename
        assert full_path.exists(), f"Audio file should exist: {full_path}"

    @pytest.mark.asyncio
    async def test_tts_invalid_voice_returns_error(self, media_context):
        """Test that an invalid voice returns MCP-compliant error format."""
        media_context("test_tts_invalid_voice")

        result = await synthesize_speech({
            "text": "Hello world",
            "engine": "kokoro",
            "voice": "nonexistent_voice",
        })
        assert_mcp_error(result, "nonexistent_voice")

    @pytest.mark.asyncio
    async def test_tts_text_too_long_returns_error(self, media_context):
        """Test that text exceeding max length returns MCP-compliant error format."""
        media_context("test_tts_text_long")

        result = await synthesize_speech({
            "text": "x" * 10001,
            "engine": "kokoro",
        })
        assert_mcp_error(result)
        error_text = result["content"][0]["text"].lower()
        assert "10001" in result["content"][0]["text"] or "too long" in error_text

    @pytest.mark.asyncio
    async def test_tts_download_url_present(self, media_context, kokoro_service):
        """Test that successful TTS result contains a valid download URL."""
        media_context("test_tts_download_url")

        raw = await synthesize_speech({
            "text": "Download URL test",
            "engine": "kokoro",
            "voice": "af_heart",
        })
        assert not raw.get("is_error"), f"TTS returned error: {raw}"
        result = parse_mcp_result(raw)

        assert "download_url" in result
        assert "/api/v1/files/dl/" in result["download_url"]


# ---------------------------------------------------------------------------
# STT standalone tests
# ---------------------------------------------------------------------------

class TestSTTToolStandalone:
    """Test STT tool independently."""

    @pytest.mark.asyncio
    async def test_stt_whisper_transcription(self, media_context, kokoro_service, whisper_service):
        """Test STT transcription with Whisper engine using TTS-generated audio."""
        storage = media_context("test_stt_whisper")

        # Generate test audio using TTS
        tts_raw = await synthesize_speech({
            "text": "Testing speech recognition tool",
            "engine": "kokoro",
            "voice": "af_heart",
        })
        assert not tts_raw.get("is_error"), f"TTS failed: {tts_raw}"
        tts_result = parse_mcp_result(tts_raw)
        assert "audio_path" in tts_result

        # Copy generated audio to input directory
        audio_filename = tts_result["audio_path"].split("/")[-1]
        audio_content = (storage.get_output_dir() / audio_filename).read_bytes()
        metadata = await storage.save_input_file(content=audio_content, filename="test_audio.wav")

        # Transcribe
        stt_raw = await transcribe_audio({
            "file_path": metadata.safe_name,
            "engine": "whisper_v3_turbo",
            "language": "auto",
        })
        assert not stt_raw.get("is_error"), f"STT returned error: {stt_raw}"
        result = parse_mcp_result(stt_raw)

        # Verify transcript content
        assert isinstance(result["text"], str)
        assert len(result["text"]) > 0

        transcript = result["text"].lower().strip()
        for word in ["testing", "speech", "recognition"]:
            assert word in transcript, (
                f"Transcript should contain '{word}'. Got: '{result['text']}'"
            )

        assert result["engine"] == "whisper_v3_turbo"
        for key in ("output_path", "download_url", "engine"):
            assert key in result

        # Verify output transcript file
        output_filename = result["output_path"].split("/")[-1]
        output_full_path = storage.get_output_dir() / output_filename
        assert output_full_path.exists(), f"Transcript file should exist: {output_full_path}"
        assert len(output_full_path.read_text()) > 0

    @pytest.mark.asyncio
    async def test_stt_file_not_found_returns_error(self, media_context):
        """Test that a nonexistent file returns MCP-compliant error format."""
        media_context("test_stt_not_found")

        result = await transcribe_audio({
            "file_path": "nonexistent.wav",
            "engine": "whisper_v3_turbo",
        })
        assert_mcp_error(result)

    @pytest.mark.asyncio
    async def test_stt_invalid_format_returns_error(self, media_context):
        """Test that an unsupported file format returns MCP error."""
        storage = media_context("test_stt_invalid_fmt")
        await storage.save_input_file(content=b"this is not audio", filename="fake_audio.txt")

        result = await transcribe_audio({
            "file_path": "fake_audio.txt",
            "engine": "whisper_v3_turbo",
        })
        assert_mcp_error(result, "Unsupported file format")

    @pytest.mark.asyncio
    async def test_stt_path_traversal_returns_error(self, media_context):
        """Test that path traversal attempts return MCP error."""
        media_context("test_stt_traversal")

        result = await transcribe_audio({
            "file_path": "../../etc/passwd",
            "engine": "whisper_v3_turbo",
        })
        assert_mcp_error(result)
        assert "traversal" in result["content"][0]["text"].lower()


# ---------------------------------------------------------------------------
# OCR standalone tests
# ---------------------------------------------------------------------------

class TestOCRToolStandalone:
    """Test OCR tool independently."""

    @pytest.mark.asyncio
    async def test_ocr_direct_call(self, media_context, ocr_service):
        """Test OCR tool with a real table image containing text."""
        storage = media_context("test_ocr_direct")

        fixture_path = Path(__file__).parent / "fixtures" / "ocr_test_table.png"
        assert fixture_path.exists(), f"Test fixture not found: {fixture_path}"

        metadata = await storage.save_input_file(
            content=fixture_path.read_bytes(),
            filename="ocr_test_table.png",
        )

        raw = await perform_ocr({
            "file_path": metadata.safe_name,
            "apply_vietnamese_corrections": False,
        })
        assert not raw.get("is_error"), f"OCR returned error: {raw}"
        result = parse_mcp_result(raw)

        for key in ("text", "output_path", "download_url"):
            assert key in result
        assert result["has_vietnamese_corrections"] is False

        # Verify meaningful text extracted from the table image
        extracted = result["text"]
        assert len(extracted) > 50, f"OCR should extract substantial text, got {len(extracted)} chars"
        assert any(
            word in extracted.lower() for word in ["table", "receipt", "data"]
        ), f"OCR text should contain table-related words, got: {extracted[:200]}"

        # Verify output file on disk
        output_filename = result["output_path"].split("/")[-1]
        full_path = storage.get_output_dir() / output_filename
        assert full_path.exists(), f"OCR output file should exist: {full_path}"
        assert len(full_path.read_text()) > 50

    @pytest.mark.asyncio
    async def test_ocr_file_not_found_returns_error(self, media_context):
        """Test that a nonexistent file returns MCP-compliant error format."""
        media_context("test_ocr_not_found")

        result = await perform_ocr({"file_path": "nonexistent.png"})
        assert_mcp_error(result)

    @pytest.mark.asyncio
    async def test_ocr_invalid_format_returns_error(self, media_context):
        """Test that an unsupported file format returns MCP error."""
        storage = media_context("test_ocr_invalid_fmt")
        metadata = await storage.save_input_file(content=b"fake mp3 content", filename="fake_image.mp3")

        result = await perform_ocr({"file_path": metadata.safe_name})
        assert_mcp_error(result, "Unsupported file format")

    @pytest.mark.asyncio
    async def test_ocr_path_traversal_returns_error(self, media_context):
        """Test that path traversal attempts return MCP error."""
        media_context("test_ocr_traversal")

        result = await perform_ocr({"file_path": "../../../etc/passwd"})
        assert_mcp_error(result)
        assert "traversal" in result["content"][0]["text"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
