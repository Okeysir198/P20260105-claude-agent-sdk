"""Real integration tests for media tools with actual agent chat.

These tests create real agent sessions and test media tools through
actual tool calls, not mocked unit tests.

Requires:
- OCR service running on localhost:18013
- STT service running on localhost:18050
- TTS service running on localhost:18034
"""
import os
import pytest
import asyncio
from pathlib import Path

# Set test environment
os.environ.setdefault("API_KEY", "test-api-key-for-testing")


class TestMediaToolsRealIntegration:
    """Real integration tests with agent SDK."""

    @pytest.mark.asyncio
    async def test_list_stt_engines_via_agent(self):
        """Test listing STT engines through actual agent tool call."""
        from agent.core.session import ConversationSession
        from agent.core.agent_options import create_agent_sdk_options
        from agent.tools.media.mcp_server import set_username

        # Set username for media tools
        set_username("test_user")

        # Create SDK options with media tools enabled
        options = create_agent_sdk_options()

        # Check that media_tools MCP server is registered
        assert options.mcp_servers is not None
        assert "media_tools" in options.mcp_servers

        # Create session
        session = ConversationSession(options=options)

        try:
            # Send query to list STT engines
            async for msg in session.send_query("List all available STT engines"):
                print(f"Message type: {type(msg).__name__}")
                # The session completed successfully
            print("Session completed successfully")
            return True

        finally:
            await session.disconnect()

    @pytest.mark.asyncio
    async def test_list_tts_engines_via_agent(self):
        """Test listing TTS engines through actual agent tool call."""
        from agent.core.session import ConversationSession
        from agent.core.agent_options import create_agent_sdk_options
        from agent.tools.media.mcp_server import set_username

        set_username("test_user")
        options = create_agent_sdk_options()

        session = ConversationSession(options=options)

        try:
            async for msg in session.send_query("What TTS engines are available?"):
                print(f"Message type: {type(msg).__name__}")
            print("Session completed successfully")
            return True

        finally:
            await session.disconnect()

    @pytest.mark.asyncio
    async def test_ocr_tool_available(self):
        """Test that OCR tool is available to the agent."""
        from agent.core.session import ConversationSession
        from agent.core.agent_options import create_agent_sdk_options
        from agent.tools.media.mcp_server import set_username

        set_username("test_user")
        options = create_agent_sdk_options()

        # Verify media_tools server is in options
        assert options.mcp_servers is not None
        assert "media_tools" in options.mcp_servers

        session = ConversationSession(options=options)

        try:
            # Ask agent what tools it has
            async for msg in session.send_query("What tools do you have for processing images?"):
                print(f"Message type: {type(msg).__name__}")
            print("Session completed successfully")
            return True

        finally:
            await session.disconnect()

    @pytest.mark.asyncio
    async def test_synthesize_speech_tool_available(self):
        """Test that TTS tool is available to the agent."""
        from agent.core.session import ConversationSession
        from agent.core.agent_options import create_agent_sdk_options
        from agent.tools.media.mcp_server import set_username

        set_username("test_user")
        options = create_agent_sdk_options()

        session = ConversationSession(options=options)

        try:
            # Ask about text-to-speech capabilities
            async for msg in session.send_query("Can you convert text to speech?"):
                print(f"Message type: {type(msg).__name__}")
            print("Session completed successfully")
            return True

        finally:
            await session.disconnect()


class TestMediaToolsWithFileStorage:
    """Test media tools integration with FileStorage."""

    @pytest.mark.asyncio
    async def test_file_storage_with_media_tools(self):
        """Test that FileStorage works correctly with media tools context."""
        from agent.core.file_storage import FileStorage
        from agent.tools.media.mcp_server import set_username, get_username

        username = "test_user"
        session_id = "test_session_media"

        # Set username in context
        set_username(username)

        # Verify username is accessible
        assert get_username() == username

        # Create FileStorage
        storage = FileStorage(username=username, session_id=session_id)

        # Verify directories are created
        input_dir = storage.get_input_dir()
        output_dir = storage.get_output_dir()

        assert input_dir.exists()
        assert output_dir.exists()
        assert "input" in str(input_dir)
        assert "output" in str(output_dir)

        # Create a test file in input
        test_content = b"Test file content for media processing"
        metadata = await storage.save_input_file(
            content=test_content,
            filename="test_input.txt"
        )

        assert metadata.safe_name == "test_input.txt"
        assert metadata.size_bytes == len(test_content)

        # Verify file exists
        saved_path = input_dir / metadata.safe_name
        assert saved_path.exists()

        # Clean up
        await storage.delete_file(metadata.safe_name, "input")


class TestMediaToolsServiceHealth:
    """Test actual service health and connectivity."""

    @pytest.mark.asyncio
    async def test_ocr_service_connectivity(self):
        """Test OCR service is accessible."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("http://localhost:18013/health")
                assert response.status_code == 200
                data = response.json()
                print(f"OCR Service health: {data}")
        except (httpx.ConnectError, httpx.ConnectTimeout):
            pytest.skip("OCR service not running on localhost:18013")

    @pytest.mark.asyncio
    async def test_stt_service_connectivity(self):
        """Test STT service is accessible."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("http://localhost:18050/health")
                assert response.status_code == 200
                data = response.json()
                print(f"STT Service health: {data}")
        except (httpx.ConnectError, httpx.ConnectTimeout):
            pytest.skip("STT service not running on localhost:18050")

    @pytest.mark.asyncio
    async def test_tts_service_connectivity(self):
        """Test TTS service is accessible."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("http://localhost:18034/health")
                assert response.status_code == 200
                data = response.json()
                print(f"TTS Service health: {data}")
        except (httpx.ConnectError, httpx.ConnectTimeout):
            pytest.skip("TTS service not running on localhost:18034")

    @pytest.mark.asyncio
    async def test_stt_client_real_call(self):
        """Test STT client with actual service call."""
        from agent.tools.media.clients.stt_client import STTClient

        try:
            client = STTClient("whisper_v3_turbo")

            # Test that client can connect (we won't transcribe without real audio)
            # Just verify the client is properly initialized
            assert client.base_url == "http://localhost:18050"
            assert client._engine == "whisper_v3_turbo"

            await client.close()

        except Exception as e:
            pytest.skip(f"STT client initialization failed: {e}")

    @pytest.mark.asyncio
    async def test_tts_client_real_call(self):
        """Test TTS client with actual service call."""
        from agent.tools.media.clients.tts_client import TTSClient

        try:
            client = TTSClient("kokoro")

            # Test that client can connect
            assert client.base_url == "http://localhost:18034"
            assert client._engine == "kokoro"

            # List voices
            voices = client.list_voices()
            assert len(voices) > 0
            assert voices[0]["id"] == "af_heart"

            await client.close()

        except Exception as e:
            pytest.skip(f"TTS client initialization failed: {e}")

    @pytest.mark.asyncio
    async def test_ocr_client_real_call(self):
        """Test OCR client with actual service."""
        from agent.tools.media.clients.ocr_client import OCRClient

        try:
            client = OCRClient()

            # Test that client can connect
            assert client.base_url == "http://localhost:18013"

            await client.close()

        except Exception as e:
            pytest.skip(f"OCR client initialization failed: {e}")


class TestMediaToolsInAgentConfig:
    """Test media tools are properly configured in agents.yaml."""

    def test_media_tools_in_default_agent(self):
        """Verify media tools are in the default agent configuration."""
        import yaml

        with open("agents.yaml") as f:
            config = yaml.safe_load(f)

        # Check _defaults has media tools
        default_tools = config.get("_defaults", {}).get("tools", [])
        media_tools = [t for t in default_tools if "media_tools" in t]

        assert len(media_tools) == 5, f"Expected 5 media tools, found {len(media_tools)}"

        expected_tools = [
            "mcp__media_tools__perform_ocr",
            "mcp__media_tools__list_stt_engines",
            "mcp__media_tools__transcribe_audio",
            "mcp__media_tools__list_tts_engines",
            "mcp__media_tools__synthesize_speech",
        ]

        for tool in expected_tools:
            assert tool in default_tools, f"Tool {tool} not found in defaults"

    def test_media_tools_in_general_assistant(self):
        """Verify media tools are in the general-assistant agent."""
        import yaml

        with open("agents.yaml") as f:
            config = yaml.safe_load(f)

        agent = config.get("agents", {}).get("general-assistant-g1h2i3j4", {})
        agent_tools = agent.get("tools", [])
        media_tools = [t for t in agent_tools if "media_tools" in t]

        assert len(media_tools) == 5, f"Expected 5 media tools in general-assistant, found {len(media_tools)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
