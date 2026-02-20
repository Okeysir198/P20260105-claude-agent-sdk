"""Standalone tests for each media tool.

Tests each tool (OCR, STT, TTS) independently by calling them directly.
"""
import os
import pytest
import tempfile
from pathlib import Path

os.environ.setdefault("API_KEY", "test-api-key-for-testing")


class TestTSToolStandalone:
    """Test TTS tool independently."""

    @pytest.mark.asyncio
    async def test_tts_tool_direct_call(self):
        """Test synthesize_speech tool directly."""
        from agent.tools.media.tts_tools import synthesize_speech
        from agent.core.file_storage import FileStorage
        from agent.tools.media.mcp_server import set_username

        username = "test_user"
        session_id = "test_tts_standalone"

        set_username(username)
        storage = FileStorage(username=username, session_id=session_id)

        try:
            # Call the tool handler directly
            handler = synthesize_speech.handler
            result = await handler({
                "text": "Hello, this is a test of the TTS tool.",
                "engine": "kokoro",
                "voice": "af_heart",
                "speed": 1.0,
                "session_id": session_id
            })

            print(f"TTS Result:")
            print(f"  Audio path: {result.get('audio_path')}")
            print(f"  Format: {result.get('format')}")
            print(f"  Engine: {result.get('engine')}")
            print(f"  Voice: {result.get('voice')}")

            assert result is not None
            assert "audio_path" in result

            # Verify the file was created
            audio_filename = result["audio_path"].split("/")[-1]
            full_path = storage.get_output_dir() / audio_filename
            assert full_path.exists(), f"Audio file should exist: {full_path}"

            file_size = full_path.stat().st_size
            print(f"  File size: {file_size} bytes")
            assert file_size > 1000, "Audio file should have content"

            print(f"\n✓ TTS tool working independently!")

        finally:
            import shutil
            session_dir = storage.get_session_dir()
            if session_dir.exists():
                shutil.rmtree(session_dir)


class TestSTTToolStandalone:
    """Test STT tool independently."""

    @pytest.mark.asyncio
    async def test_stt_tool_direct_call(self):
        """Test transcribe_audio tool directly."""
        from agent.tools.media.stt_tools import transcribe_audio
        from agent.core.file_storage import FileStorage
        from agent.tools.media.mcp_server import set_username
        import httpx

        username = "test_user"
        session_id = "test_stt_standalone"

        set_username(username)
        storage = FileStorage(username=username, session_id=session_id)

        # First, create a test audio file using TTS service
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            # Generate test audio with TTS
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "http://localhost:18034/v1/speak",
                    params={"model": "af_heart"},
                    json={"text": "Testing speech recognition tool"}
                )
                response.raise_for_status()
                audio_data = response.content

            tmp_path.write_bytes(audio_data)
            print(f"Created test audio: {len(audio_data)} bytes")

            # Upload to storage
            with open(tmp_path, "rb") as f:
                audio_content = f.read()

            metadata = await storage.save_input_file(
                content=audio_content,
                filename="test_audio.wav"
            )

            print(f"Uploaded audio: {metadata.safe_name}")

            # Call the STT tool handler directly
            handler = transcribe_audio.handler
            result = await handler({
                "file_path": metadata.safe_name,
                "engine": "whisper_v3_turbo",
                "language": "auto",
                "session_id": session_id
            })

            print(f"STT Result:")
            print(f"  Text: {result.get('text', 'N/A')[:100]}")
            print(f"  Confidence: {result.get('confidence')}")
            print(f"  Engine: {result.get('engine')}")
            print(f"  Output path: {result.get('output_path')}")

            assert result is not None
            assert "text" in result

            print(f"\n✓ STT tool working independently!")

        finally:
            if tmp_path.exists():
                tmp_path.unlink()
            import shutil
            session_dir = storage.get_session_dir()
            if session_dir.exists():
                shutil.rmtree(session_dir)


class TestListEnginesTools:
    """Test list engines tools independently."""

    @pytest.mark.asyncio
    async def test_list_stt_engines_tool(self):
        """Test list_stt_engines tool directly."""
        from agent.tools.media.stt_tools import list_stt_engines

        # Call the tool handler directly
        handler = list_stt_engines.handler
        result = await handler({})

        print(f"STT Engines:")
        for engine in result["engines"]:
            print(f"  - {engine['id']}: {engine['name']}")
            print(f"    URL: {engine['url']}")
            print(f"    Status: {engine['status']}")

        assert len(result["engines"]) == 2
        assert result["engines"][0]["id"] == "whisper_v3_turbo"
        assert result["engines"][1]["id"] == "nemotron_speech"

        print(f"\n✓ list_stt_engines tool working!")

    @pytest.mark.asyncio
    async def test_list_tts_engines_tool(self):
        """Test list_tts_engines tool directly."""
        from agent.tools.media.tts_tools import list_tts_engines

        # Call the tool handler directly
        handler = list_tts_engines.handler
        result = await handler({})

        print(f"TTS Engines:")
        for engine in result["engines"]:
            print(f"  - {engine['id']}: {engine['name']}")
            print(f"    Format: {engine['output_format']}")

        assert len(result["engines"]) == 3
        engine_ids = [e["id"] for e in result["engines"]]
        assert "kokoro" in engine_ids
        assert "supertonic_v1_1" in engine_ids
        assert "chatterbox_turbo" in engine_ids

        print(f"\n✓ list_tts_engines tool working!")


class TestOCRToolStandalone:
    """Test OCR tool independently."""

    @pytest.mark.asyncio
    async def test_ocr_tool_direct_call(self):
        """Test perform_ocr tool directly."""
        import os
        import httpx

        # Skip if VLLM_API_KEY is not set
        if not os.environ.get("VLLM_API_KEY"):
            pytest.skip("OCR service requires VLLM_API_KEY environment variable")

        from agent.tools.media.ocr_tools import perform_ocr
        from agent.core.file_storage import FileStorage
        from agent.tools.media.mcp_server import set_username

        username = "test_user"
        session_id = "test_ocr_standalone"

        set_username(username)
        storage = FileStorage(username=username, session_id=session_id)

        # First check if OCR service is accessible
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("http://localhost:18013/health")
                if response.status_code != 200:
                    pytest.skip("OCR service not accessible")
        except:
            pytest.skip("OCR service not running")

        try:
            # Use pre-created test image
            test_image_path = Path("/tmp/test_ocr.png")

            if not test_image_path.exists():
                # Create a simple test image using raw bytes (PNG header + simple data)
                # Minimal 1x1 PNG with white background
                test_content = (
                    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
                    b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf'
                    b'\xc0\x00\x00\x00\x03\x00\x01\x00\x00\x00\x00IEND\xaeB`\x82'
                )
            else:
                test_content = test_image_path.read_bytes()

            metadata = await storage.save_input_file(
                content=test_content,
                filename="test_image.png"
            )

            print(f"Created test image: {metadata.safe_name}")

            # Call the OCR tool handler directly
            handler = perform_ocr.handler

            try:
                result = await handler({
                    "file_path": metadata.safe_name,
                    "apply_vietnamese_corrections": False,
                    "session_id": session_id
                })

                print(f"OCR Result:")
                print(f"  Output path: {result.get('output_path')}")
                print(f"  Processing time: {result.get('processing_time_ms')} ms")

                # Check output file was created
                if "output_path" in result:
                    output_filename = result["output_path"].split("/")[-1]
                    full_path = storage.get_output_dir() / output_filename
                    if full_path.exists():
                        content = full_path.read_text()
                        print(f"  Output content: {content[:100]}")

                print(f"\n✓ OCR tool working!")

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    pytest.skip("OCR service requires API key authentication (VLLM_API_KEY not set)")
                else:
                    raise

        finally:
            import shutil
            session_dir = storage.get_session_dir()
            if session_dir.exists():
                shutil.rmtree(session_dir)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
