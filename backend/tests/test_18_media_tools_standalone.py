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

os.environ.setdefault("API_KEY", "test-api-key-for-testing")


def parse_mcp_result(result: dict) -> dict:
    """Extract and parse JSON data from MCP tool result format.

    MCP tools return {"content": [{"type": "text", "text": "<json>"}]}.
    This helper extracts and JSON-parses the text content.
    """
    assert "content" in result, f"Result missing 'content' key: {result}"
    assert isinstance(result["content"], list) and len(result["content"]) > 0
    assert result["content"][0]["type"] == "text"
    return json.loads(result["content"][0]["text"])


class TestListEnginesTools:
    """Test list engines tools independently."""

    @pytest.mark.asyncio
    async def test_list_stt_engines_tool(self):
        """Test list_stt_engines returns correct engines with required fields."""
        from agent.tools.media.stt_tools import list_stt_engines

        handler = list_stt_engines.handler
        raw = await handler({})
        result = parse_mcp_result(raw)

        assert "engines" in result
        engines = result["engines"]
        assert len(engines) == 2

        # Verify each engine has required fields
        for engine in engines:
            assert "id" in engine
            assert "name" in engine
            assert "url" in engine
            assert "status" in engine

        # Verify engine IDs
        assert engines[0]["id"] == "whisper_v3_turbo"
        assert engines[1]["id"] == "nemotron_speech"

    @pytest.mark.asyncio
    async def test_list_tts_engines_tool(self):
        """Test list_tts_engines returns correct engines with required fields."""
        from agent.tools.media.tts_tools import list_tts_engines

        handler = list_tts_engines.handler
        raw = await handler({})
        result = parse_mcp_result(raw)

        assert "engines" in result
        engines = result["engines"]
        assert len(engines) == 3

        # Verify each engine has required fields
        for engine in engines:
            assert "id" in engine
            assert "name" in engine
            assert "url" in engine
            assert "output_format" in engine
            assert "voices" in engine

        # Verify engine IDs
        engine_ids = [e["id"] for e in engines]
        assert "kokoro" in engine_ids
        assert "supertonic_v1_1" in engine_ids
        assert "chatterbox_turbo" in engine_ids


class TestTTSToolStandalone:
    """Test TTS tool independently."""

    @pytest.mark.asyncio
    async def test_tts_kokoro_synthesis(self):
        """Test TTS synthesis with Kokoro engine, verify WAV output and headers."""
        import httpx
        from agent.tools.media.tts_tools import synthesize_speech
        from agent.core.file_storage import FileStorage
        from agent.tools.media.mcp_server import set_username, set_session_id, reset_session_id

        # Check if Kokoro service is running
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get("http://localhost:18034/health")
                if resp.status_code != 200:
                    pytest.skip("Kokoro TTS service not accessible")
        except Exception:
            pytest.skip("Kokoro TTS service not running")

        username = "test_user"
        session_id = "test_tts_kokoro"

        set_username(username)
        session_token = set_session_id(session_id)
        storage = FileStorage(username=username, session_id=session_id)

        try:
            handler = synthesize_speech.handler
            raw = await handler({
                "text": "Hello world",
                "engine": "kokoro",
                "voice": "af_heart",
                "speed": 1.0,
            })
            assert not raw.get("is_error"), f"TTS returned error: {raw}"
            result = parse_mcp_result(raw)

            # Verify all expected keys are present
            assert "audio_path" in result
            assert "download_url" in result
            assert "format" in result
            assert "engine" in result
            assert "voice" in result
            assert "text" in result
            assert "duration_ms" in result
            assert "file_size_bytes" in result

            # Verify values
            assert result["format"] == "wav"
            assert result["engine"] == "kokoro"
            assert result["voice"] == "af_heart"
            assert result["text"] == "Hello world"
            assert result["file_size_bytes"] > 1000
            assert result["duration_ms"] >= 0

            # Verify audio file exists on disk
            audio_filename = result["audio_path"].split("/")[-1]
            full_path = storage.get_output_dir() / audio_filename
            assert full_path.exists(), f"Audio file should exist: {full_path}"

            # Verify WAV headers
            audio_bytes = full_path.read_bytes()
            assert audio_bytes[:4] == b"RIFF", "WAV file should start with RIFF header"
            assert audio_bytes[8:12] == b"WAVE", "WAV file should contain WAVE marker"

        finally:
            reset_session_id(session_token)
            session_dir = storage.get_session_dir()
            if session_dir.exists():
                shutil.rmtree(session_dir)

    @pytest.mark.asyncio
    async def test_tts_supertonic_synthesis(self):
        """Test TTS synthesis with Supertonic engine, verify output."""
        import httpx
        from agent.tools.media.tts_tools import synthesize_speech
        from agent.core.file_storage import FileStorage
        from agent.tools.media.mcp_server import set_username, set_session_id, reset_session_id

        # Check if Supertonic service is running
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get("http://localhost:18030/health")
                if resp.status_code != 200:
                    pytest.skip("Supertonic TTS service not accessible")
        except Exception:
            pytest.skip("Supertonic TTS service not running")

        username = "test_user"
        session_id = "test_tts_supertonic"

        set_username(username)
        session_token = set_session_id(session_id)
        storage = FileStorage(username=username, session_id=session_id)

        try:
            handler = synthesize_speech.handler
            raw = await handler({
                "text": "Hello world",
                "engine": "supertonic_v1_1",
                "voice": "F1",
                "speed": 1.0,
            })

            # Should not be an error
            assert not raw.get("is_error"), f"TTS returned error: {raw}"
            result = parse_mcp_result(raw)

            # Verify expected keys
            assert "audio_path" in result
            assert "download_url" in result
            assert "format" in result
            assert "engine" in result
            assert "file_size_bytes" in result

            assert result["engine"] == "supertonic_v1_1"
            assert result["file_size_bytes"] > 1000

            # Verify audio file exists on disk
            audio_filename = result["audio_path"].split("/")[-1]
            full_path = storage.get_output_dir() / audio_filename
            assert full_path.exists(), f"Audio file should exist: {full_path}"

        finally:
            reset_session_id(session_token)
            session_dir = storage.get_session_dir()
            if session_dir.exists():
                shutil.rmtree(session_dir)

    @pytest.mark.asyncio
    async def test_tts_invalid_voice_returns_error(self):
        """Test that an invalid voice returns MCP-compliant error format."""
        from agent.tools.media.tts_tools import synthesize_speech
        from agent.core.file_storage import FileStorage
        from agent.tools.media.mcp_server import set_username, set_session_id, reset_session_id

        username = "test_user"
        session_id = "test_tts_invalid_voice"

        set_username(username)
        session_token = set_session_id(session_id)
        storage = FileStorage(username=username, session_id=session_id)

        try:
            handler = synthesize_speech.handler
            result = await handler({
                "text": "Hello world",
                "engine": "kokoro",
                "voice": "nonexistent_voice",
            })

            # Verify MCP error format
            assert result.get("is_error") is True
            assert "content" in result
            assert isinstance(result["content"], list)
            assert len(result["content"]) > 0
            assert result["content"][0]["type"] == "text"
            assert "nonexistent_voice" in result["content"][0]["text"]

        finally:
            reset_session_id(session_token)
            session_dir = storage.get_session_dir()
            if session_dir.exists():
                shutil.rmtree(session_dir)

    @pytest.mark.asyncio
    async def test_tts_text_too_long_returns_error(self):
        """Test that text exceeding max length returns MCP-compliant error format."""
        from agent.tools.media.tts_tools import synthesize_speech
        from agent.core.file_storage import FileStorage
        from agent.tools.media.mcp_server import set_username, set_session_id, reset_session_id

        username = "test_user"
        session_id = "test_tts_text_long"

        set_username(username)
        session_token = set_session_id(session_id)
        storage = FileStorage(username=username, session_id=session_id)

        try:
            handler = synthesize_speech.handler
            result = await handler({
                "text": "x" * 10001,
                "engine": "kokoro",
            })

            # Verify MCP error format
            assert result.get("is_error") is True
            assert "content" in result
            assert isinstance(result["content"], list)
            assert result["content"][0]["type"] == "text"
            assert "10001" in result["content"][0]["text"] or "too long" in result["content"][0]["text"].lower()

        finally:
            reset_session_id(session_token)
            session_dir = storage.get_session_dir()
            if session_dir.exists():
                shutil.rmtree(session_dir)

    @pytest.mark.asyncio
    async def test_tts_download_url_present(self):
        """Test that successful TTS result contains a valid download URL."""
        import httpx
        from agent.tools.media.tts_tools import synthesize_speech
        from agent.core.file_storage import FileStorage
        from agent.tools.media.mcp_server import set_username, set_session_id, reset_session_id

        # Check if Kokoro service is running
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get("http://localhost:18034/health")
                if resp.status_code != 200:
                    pytest.skip("Kokoro TTS service not accessible")
        except Exception:
            pytest.skip("Kokoro TTS service not running")

        username = "test_user"
        session_id = "test_tts_download_url"

        set_username(username)
        session_token = set_session_id(session_id)
        storage = FileStorage(username=username, session_id=session_id)

        try:
            handler = synthesize_speech.handler
            raw = await handler({
                "text": "Download URL test",
                "engine": "kokoro",
                "voice": "af_heart",
            })
            assert not raw.get("is_error"), f"TTS returned error: {raw}"
            result = parse_mcp_result(raw)

            assert "download_url" in result
            assert "/api/v1/files/dl/" in result["download_url"]

        finally:
            reset_session_id(session_token)
            session_dir = storage.get_session_dir()
            if session_dir.exists():
                shutil.rmtree(session_dir)


class TestSTTToolStandalone:
    """Test STT tool independently."""

    @pytest.mark.asyncio
    async def test_stt_whisper_transcription(self):
        """Test STT transcription with Whisper engine using TTS-generated audio."""
        import httpx
        from agent.tools.media.stt_tools import transcribe_audio
        from agent.tools.media.tts_tools import synthesize_speech
        from agent.core.file_storage import FileStorage
        from agent.tools.media.mcp_server import set_username, set_session_id, reset_session_id

        # Check if services are running
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get("http://localhost:18034/health")
                if resp.status_code != 200:
                    pytest.skip("Kokoro TTS service not accessible (needed to generate test audio)")
        except Exception:
            pytest.skip("Kokoro TTS service not running")

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get("http://localhost:18050/health")
                if resp.status_code != 200:
                    pytest.skip("Whisper STT service not accessible")
        except Exception:
            pytest.skip("Whisper STT service not running")

        username = "test_user"
        session_id = "test_stt_whisper"

        set_username(username)
        session_token = set_session_id(session_id)
        storage = FileStorage(username=username, session_id=session_id)

        try:
            # Step 1: Generate test audio using TTS
            tts_handler = synthesize_speech.handler
            tts_raw = await tts_handler({
                "text": "Testing speech recognition tool",
                "engine": "kokoro",
                "voice": "af_heart",
            })
            assert not tts_raw.get("is_error"), f"TTS failed: {tts_raw}"
            tts_result = parse_mcp_result(tts_raw)
            assert "audio_path" in tts_result, f"TTS missing audio_path: {tts_result}"

            # Read the generated audio and save to input directory
            audio_filename = tts_result["audio_path"].split("/")[-1]
            audio_full_path = storage.get_output_dir() / audio_filename
            audio_content = audio_full_path.read_bytes()

            metadata = await storage.save_input_file(
                content=audio_content,
                filename="test_audio.wav"
            )

            # Step 2: Transcribe the audio
            stt_handler = transcribe_audio.handler
            stt_raw = await stt_handler({
                "file_path": metadata.safe_name,
                "engine": "whisper_v3_turbo",
                "language": "auto",
            })
            assert not stt_raw.get("is_error"), f"STT returned error: {stt_raw}"
            result = parse_mcp_result(stt_raw)

            # Verify result has expected keys
            assert "text" in result
            assert isinstance(result["text"], str)
            assert len(result["text"]) > 0

            # Verify transcript matches the original TTS text
            original_text = "Testing speech recognition tool"
            transcript = result["text"].lower().strip()
            # Check that key words from the original appear in the transcript
            for word in ["testing", "speech", "recognition"]:
                assert word in transcript, (
                    f"Transcript should contain '{word}'. "
                    f"Original: '{original_text}', Got: '{result['text']}'"
                )

            assert "output_path" in result
            assert "download_url" in result
            assert "engine" in result
            assert result["engine"] == "whisper_v3_turbo"

            # Verify output transcript file exists on disk
            output_filename = result["output_path"].split("/")[-1]
            output_full_path = storage.get_output_dir() / output_filename
            assert output_full_path.exists(), f"Transcript file should exist: {output_full_path}"

            transcript_content = output_full_path.read_text()
            assert len(transcript_content) > 0

        finally:
            reset_session_id(session_token)
            session_dir = storage.get_session_dir()
            if session_dir.exists():
                shutil.rmtree(session_dir)

    @pytest.mark.asyncio
    async def test_stt_file_not_found_returns_error(self):
        """Test that a nonexistent file returns MCP-compliant error format."""
        from agent.tools.media.stt_tools import transcribe_audio
        from agent.core.file_storage import FileStorage
        from agent.tools.media.mcp_server import set_username, set_session_id, reset_session_id

        username = "test_user"
        session_id = "test_stt_not_found"

        set_username(username)
        session_token = set_session_id(session_id)
        storage = FileStorage(username=username, session_id=session_id)

        try:
            handler = transcribe_audio.handler
            result = await handler({
                "file_path": "nonexistent.wav",
                "engine": "whisper_v3_turbo",
            })

            # Verify MCP error format
            assert result.get("is_error") is True
            assert "content" in result
            assert isinstance(result["content"], list)
            assert result["content"][0]["type"] == "text"

        finally:
            reset_session_id(session_token)
            session_dir = storage.get_session_dir()
            if session_dir.exists():
                shutil.rmtree(session_dir)

    @pytest.mark.asyncio
    async def test_stt_invalid_format_returns_error(self):
        """Test that an unsupported file format returns MCP error with format message."""
        from agent.tools.media.stt_tools import transcribe_audio
        from agent.core.file_storage import FileStorage
        from agent.tools.media.mcp_server import set_username, set_session_id, reset_session_id

        username = "test_user"
        session_id = "test_stt_invalid_fmt"

        set_username(username)
        session_token = set_session_id(session_id)
        storage = FileStorage(username=username, session_id=session_id)

        try:
            # Create a .txt file in input directory
            metadata = await storage.save_input_file(
                content=b"this is not audio",
                filename="fake_audio.txt"
            )

            handler = transcribe_audio.handler
            result = await handler({
                "file_path": metadata.safe_name,
                "engine": "whisper_v3_turbo",
            })

            # Verify MCP error format with unsupported format message
            assert result.get("is_error") is True
            assert "content" in result
            assert "Unsupported file format" in result["content"][0]["text"]

        finally:
            reset_session_id(session_token)
            session_dir = storage.get_session_dir()
            if session_dir.exists():
                shutil.rmtree(session_dir)

    @pytest.mark.asyncio
    async def test_stt_path_traversal_returns_error(self):
        """Test that path traversal attempts return MCP error with traversal message."""
        from agent.tools.media.stt_tools import transcribe_audio
        from agent.core.file_storage import FileStorage
        from agent.tools.media.mcp_server import set_username, set_session_id, reset_session_id

        username = "test_user"
        session_id = "test_stt_traversal"

        set_username(username)
        session_token = set_session_id(session_id)
        storage = FileStorage(username=username, session_id=session_id)

        try:
            handler = transcribe_audio.handler
            result = await handler({
                "file_path": "../../etc/passwd",
                "engine": "whisper_v3_turbo",
            })

            # Verify MCP error format with path traversal message
            assert result.get("is_error") is True
            assert "content" in result
            assert "Path traversal" in result["content"][0]["text"] or "traversal" in result["content"][0]["text"].lower()

        finally:
            reset_session_id(session_token)
            session_dir = storage.get_session_dir()
            if session_dir.exists():
                shutil.rmtree(session_dir)


class TestOCRToolStandalone:
    """Test OCR tool independently."""

    @pytest.mark.asyncio
    async def test_ocr_direct_call(self):
        """Test OCR tool with a real table image containing text."""
        import httpx
        from pathlib import Path

        # Skip if VLLM_API_KEY is not set
        if not os.environ.get("VLLM_API_KEY"):
            pytest.skip("OCR service requires VLLM_API_KEY environment variable")

        from agent.tools.media.ocr_tools import perform_ocr
        from agent.core.file_storage import FileStorage
        from agent.tools.media.mcp_server import set_username, set_session_id, reset_session_id

        # Check if OCR service is running
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get("http://localhost:18013/health")
                if resp.status_code != 200:
                    pytest.skip("OCR service not accessible")
        except Exception:
            pytest.skip("OCR service not running")

        username = "test_user"
        session_id = "test_ocr_direct"

        set_username(username)
        session_token = set_session_id(session_id)
        storage = FileStorage(username=username, session_id=session_id)

        try:
            # Use real table image from test fixtures
            fixture_path = Path(__file__).parent / "fixtures" / "ocr_test_table.png"
            assert fixture_path.exists(), f"Test fixture not found: {fixture_path}"
            test_content = fixture_path.read_bytes()

            metadata = await storage.save_input_file(
                content=test_content,
                filename="ocr_test_table.png"
            )

            handler = perform_ocr.handler
            raw = await handler({
                "file_path": metadata.safe_name,
                "apply_vietnamese_corrections": False,
            })

            assert not raw.get("is_error"), f"OCR returned error: {raw}"
            result = parse_mcp_result(raw)

            # Verify expected keys
            assert "text" in result
            assert "output_path" in result
            assert "download_url" in result
            assert result["has_vietnamese_corrections"] is False

            # Verify OCR extracted meaningful text from the table image
            extracted = result["text"]
            assert len(extracted) > 50, f"OCR should extract substantial text, got {len(extracted)} chars"
            # The image contains "Table 1: Summary of Manually Coded Receipt Data"
            assert "table" in extracted.lower() or "receipt" in extracted.lower() or "data" in extracted.lower(), (
                f"OCR text should contain table-related words, got: {extracted[:200]}"
            )

            # Verify output file exists on disk
            output_filename = result["output_path"].split("/")[-1]
            full_path = storage.get_output_dir() / output_filename
            assert full_path.exists(), f"OCR output file should exist: {full_path}"

            # Verify output file content matches result
            saved_text = full_path.read_text()
            assert len(saved_text) > 50, "Saved OCR output should have substantial content"

        finally:
            reset_session_id(session_token)
            session_dir = storage.get_session_dir()
            if session_dir.exists():
                shutil.rmtree(session_dir)

    @pytest.mark.asyncio
    async def test_ocr_file_not_found_returns_error(self):
        """Test that a nonexistent file returns MCP-compliant error format."""
        from agent.tools.media.ocr_tools import perform_ocr
        from agent.core.file_storage import FileStorage
        from agent.tools.media.mcp_server import set_username, set_session_id, reset_session_id

        username = "test_user"
        session_id = "test_ocr_not_found"

        set_username(username)
        session_token = set_session_id(session_id)
        storage = FileStorage(username=username, session_id=session_id)

        try:
            handler = perform_ocr.handler
            result = await handler({
                "file_path": "nonexistent.png",
            })

            # Verify MCP error format
            assert result.get("is_error") is True
            assert "content" in result
            assert isinstance(result["content"], list)
            assert result["content"][0]["type"] == "text"

        finally:
            reset_session_id(session_token)
            session_dir = storage.get_session_dir()
            if session_dir.exists():
                shutil.rmtree(session_dir)

    @pytest.mark.asyncio
    async def test_ocr_invalid_format_returns_error(self):
        """Test that an unsupported file format returns MCP error."""
        from agent.tools.media.ocr_tools import perform_ocr
        from agent.core.file_storage import FileStorage
        from agent.tools.media.mcp_server import set_username, set_session_id, reset_session_id

        username = "test_user"
        session_id = "test_ocr_invalid_fmt"

        set_username(username)
        session_token = set_session_id(session_id)
        storage = FileStorage(username=username, session_id=session_id)

        try:
            # Create a .mp3 file in input directory
            metadata = await storage.save_input_file(
                content=b"fake mp3 content",
                filename="fake_image.mp3"
            )

            handler = perform_ocr.handler
            result = await handler({
                "file_path": metadata.safe_name,
            })

            # Verify MCP error format with unsupported format message
            assert result.get("is_error") is True
            assert "content" in result
            assert "Unsupported file format" in result["content"][0]["text"]

        finally:
            reset_session_id(session_token)
            session_dir = storage.get_session_dir()
            if session_dir.exists():
                shutil.rmtree(session_dir)

    @pytest.mark.asyncio
    async def test_ocr_path_traversal_returns_error(self):
        """Test that path traversal attempts return MCP error."""
        from agent.tools.media.ocr_tools import perform_ocr
        from agent.core.file_storage import FileStorage
        from agent.tools.media.mcp_server import set_username, set_session_id, reset_session_id

        username = "test_user"
        session_id = "test_ocr_traversal"

        set_username(username)
        session_token = set_session_id(session_id)
        storage = FileStorage(username=username, session_id=session_id)

        try:
            handler = perform_ocr.handler
            result = await handler({
                "file_path": "../../../etc/passwd",
            })

            # Verify MCP error format with path traversal message
            assert result.get("is_error") is True
            assert "content" in result
            assert "Path traversal" in result["content"][0]["text"] or "traversal" in result["content"][0]["text"].lower()

        finally:
            reset_session_id(session_token)
            session_dir = storage.get_session_dir()
            if session_dir.exists():
                shutil.rmtree(session_dir)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
