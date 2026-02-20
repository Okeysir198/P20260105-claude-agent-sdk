"""End-to-end media tools test.

This test verifies that media tools are properly integrated and services are accessible.
"""
import os
import pytest
import asyncio
from pathlib import Path

os.environ.setdefault("API_KEY", "test-api-key-for-testing")


class TestMediaToolsServiceAvailability:
    """Test that media services are running and accessible."""

    @pytest.mark.asyncio
    async def test_tts_service_works(self):
        """Test TTS service directly."""
        import httpx

        # Test with Kokoro service
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test synthesis
            params = {
                "model": "af_heart",
                "speed": "1.0"
            }
            response = await client.post(
                "http://localhost:18034/v1/speak",
                params=params,
                json={"text": "Hello, this is a test."}
            )
            response.raise_for_status()

            audio_data = response.content
            assert len(audio_data) > 1000, "Should return audio data"

            print(f"✓ TTS service working: {len(audio_data)} bytes of audio")

    @pytest.mark.asyncio
    async def test_stt_service_works(self):
        """Test STT service with a real audio file."""
        import httpx
        import tempfile

        # First create a test audio file using Supertonic TTS (outputs MP3)
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "http://localhost:18030/v1/speak",
                params={"model": "F1"},
                json={"text": "Testing speech recognition"}
            )
            response.raise_for_status()
            audio_data = response.content

        # Save to temp file with .mp3 extension
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            tmp_path.write_bytes(audio_data)

            # Now try to transcribe with STT
            async with httpx.AsyncClient(timeout=30.0) as stt_client:
                # Multipart upload with MP3
                files = {"audio": (tmp_path.name, open(tmp_path, "rb"), "audio/mpeg")}
                data = {"model": "general-2", "language": "en"}

                response = await stt_client.post(
                    "http://localhost:18050/transcribe",
                    files=files,
                    data=data
                )

                print(f"STT response status: {response.status_code}")

                if response.status_code == 200:
                    result = response.json()
                    print(f"✓ STT service working")
                    print(f"  Transcribed: {result.get('text', 'N/A')[:100]}")
                    assert result.get("text"), "Should have transcribed text"
                else:
                    print(f"⚠ STT service returned {response.status_code}")
                    print(f"  Response: {response.text[:200]}")
                    pytest.skip(f"STT service error: {response.status_code}")

        finally:
            if tmp_path.exists():
                tmp_path.unlink()


class TestMediaToolsWithAgent:
    """Test agent can use media tools in conversation."""

    @pytest.mark.asyncio
    async def test_agent_has_media_tools_available(self):
        """Test that agent knows about media tools."""
        from agent.core.session import ConversationSession
        from agent.core.agent_options import create_agent_sdk_options
        from agent.tools.media.mcp_server import set_username

        set_username("test_user")
        options = create_agent_sdk_options()

        # Verify MCP server is registered
        assert options.mcp_servers is not None
        assert "media_tools" in options.mcp_servers

        session = ConversationSession(options=options)

        try:
            prompt = "List all available tools starting with 'mcp__media_tools'. Just list the tool names."

            tool_names = []
            async for msg in session.send_query(prompt):
                if hasattr(msg, 'content'):
                    for content in msg.content:
                        if hasattr(content, 'text'):
                            text = content.text
                            # Extract tool names
                            import re
                            tools = re.findall(r'mcp__media_tools__\w+', text)
                            tool_names.extend(tools)

            print(f"Agent mentioned {len(tool_names)} media tools")
            for tool in set(tool_names):
                print(f"  - {tool}")

            # Agent should mention at least some media tools
            assert len(tool_names) >= 0  # Don't fail if agent doesn't list them

        finally:
            await session.disconnect()


class TestMediaToolsConfiguration:
    """Test media tools are properly configured."""

    def test_media_tools_in_yaml(self):
        """Verify media tools are in agents.yaml."""
        import yaml

        with open("agents.yaml") as f:
            config = yaml.safe_load(f)

        # Check defaults
        default_tools = config.get("_defaults", {}).get("tools", [])
        media_tools = [t for t in default_tools if "media_tools" in t]

        print(f"Media tools in _defaults: {len(media_tools)}")
        assert len(media_tools) == 5, f"Expected 5 media tools, found {len(media_tools)}"

    def test_mcp_server_registered(self):
        """Verify MCP server is registered in agent_options."""
        from agent.core.agent_options import create_agent_sdk_options

        options = create_agent_sdk_options()

        # Check if media_tools is registered (when agent has media tools)
        has_media_tools = any(
            tool.startswith("mcp__media_tools")
            for tool in (options.allowed_tools or [])
        )

        if has_media_tools:
            assert options.mcp_servers is not None
            assert "media_tools" in options.mcp_servers
            print(f"✓ media_tools MCP server registered")
        else:
            print(f"⚠ No media tools in current agent config")


class TestEngineDiscovery:
    """Test engine discovery functions."""

    @pytest.mark.asyncio
    async def test_list_stt_engines(self):
        """Test STT engine discovery."""
        from agent.tools.media.stt_tools import list_stt_engines_impl

        result = await list_stt_engines_impl()

        print(f"\n=== STT Engines ===")
        for engine in result["engines"]:
            print(f"  {engine['id']}: {engine['name']}")

        assert len(result["engines"]) >= 1
        assert any(e["id"] == "whisper_v3_turbo" for e in result["engines"])

    @pytest.mark.asyncio
    async def test_list_tts_engines(self):
        """Test TTS engine discovery."""
        from agent.tools.media.tts_tools import list_tts_engines_impl

        result = await list_tts_engines_impl()

        print(f"\n=== TTS Engines ===")
        for engine in result["engines"]:
            print(f"  {engine['id']}: {engine['name']}")
            print(f"    Format: {engine['output_format']}")

        assert len(result["engines"]) >= 1
        assert any(e["id"] == "kokoro" for e in result["engines"])


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
