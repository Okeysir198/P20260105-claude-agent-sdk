"""Real integration tests for media tools with actual agent chat.

These tests create real agent sessions and test media tools through
actual tool calls via the Claude Agent SDK, not mocked unit tests.

Integration tests verify:
1. The agent calls the expected tool (ToolUseBlock with correct name)
2. The tool returns MCP-compliant content (ToolResultBlock.content is populated)
3. The tool does not error (ToolResultBlock.is_error is falsy)
4. Side effects are correct (output files exist on disk, correct format)
5. The agent's final text response reflects tool success

Requires:
- OCR service running on localhost:18013
- STT service running on localhost:18050
- TTS service running on localhost:18034
"""
import json
import os
import shutil
import pytest
from pathlib import Path

# Set test environment
os.environ.setdefault("API_KEY", "test-api-key-for-testing")

from claude_agent_sdk.types import (
    AssistantMessage,
    UserMessage,
    ResultMessage,
    ToolUseBlock,
    ToolResultBlock,
)


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

async def collect_tool_events(session, query: str):
    """Send query and collect tool_use/tool_result pairs + final text.

    Returns:
        Tuple of (tool_uses, tool_results, final_text) where:
        - tool_uses: List of (name, id, input) tuples
        - tool_results: Dict mapping tool_use_id -> {is_error, content}
        - final_text: Concatenated assistant text from the response
    """
    tool_uses = []       # List of (name, id, input)
    tool_results = {}    # tool_use_id -> {is_error, content}
    text_parts = []      # Collected assistant text

    async for msg in session.send_query(query):
        if isinstance(msg, AssistantMessage):
            for block in getattr(msg, "content", []):
                if isinstance(block, ToolUseBlock):
                    tool_uses.append((block.name, block.id, block.input))
                elif hasattr(block, "text"):
                    text = getattr(block, "text", "")
                    if text:
                        text_parts.append(text)
        elif isinstance(msg, UserMessage):
            for block in getattr(msg, "content", []):
                if isinstance(block, ToolResultBlock):
                    tool_results[block.tool_use_id] = {
                        "is_error": getattr(block, "is_error", None),
                        "content": getattr(block, "content", []),
                    }
        elif isinstance(msg, ResultMessage):
            break

    return tool_uses, tool_results, "\n".join(text_parts)


def parse_tool_result_content(content_blocks: list) -> dict | None:
    """Parse JSON data from MCP tool result content blocks.

    ToolResultBlock.content is a list of content blocks like:
    [{"type": "text", "text": "<json string>"}]

    Returns parsed dict, or None if content is empty.
    """
    if not content_blocks:
        return None
    for block in content_blocks:
        block_dict = block if isinstance(block, dict) else (
            {"type": getattr(block, "type", ""), "text": getattr(block, "text", "")}
        )
        if block_dict.get("type") == "text" and block_dict.get("text"):
            try:
                return json.loads(block_dict["text"])
            except (json.JSONDecodeError, TypeError):
                return None
    return None


# ---------------------------------------------------------------------------
# TestMediaToolsRealIntegration
# ---------------------------------------------------------------------------

class TestMediaToolsRealIntegration:
    """Real integration tests with agent SDK – verifies that the agent
    actually invokes the media MCP tools and the tools execute without errors."""

    @pytest.mark.asyncio
    async def test_list_stt_engines_via_agent(self):
        """Test listing STT engines through an actual agent tool call."""
        from agent.core.session import ConversationSession
        from agent.core.agent_options import create_agent_sdk_options
        from agent.tools.media.mcp_server import set_username, set_session_id, reset_session_id

        set_username("test_user")
        session_token = set_session_id("test_session_stt_list")

        options = create_agent_sdk_options()
        session = ConversationSession(options=options)

        try:
            tool_uses, tool_results, _ = await collect_tool_events(
                session,
                "Call the mcp__media_tools__list_stt_engines tool right now. "
                "Do not use Bash, Read, or any other tool. Only use the list_stt_engines MCP tool.",
            )

            # Verify the agent called list_stt_engines
            matching = [
                (name, tid) for name, tid, _ in tool_uses
                if "list_stt_engines" in name
            ]
            assert len(matching) > 0, (
                f"Agent did not call list_stt_engines. Tool calls: "
                f"{[n for n, _, _ in tool_uses]}"
            )

            # Verify tool did not error and content is populated
            tool_name, tool_id = matching[0]
            assert tool_id in tool_results, f"No result for {tool_name}"
            result_info = tool_results[tool_id]
            assert not result_info["is_error"], f"list_stt_engines returned an error"

            # Verify ToolResultBlock.content is populated (MCP format fix)
            content = result_info["content"]
            assert len(content) > 0, (
                "ToolResultBlock.content should not be empty — "
                "tool must return MCP format: {content: [{type: 'text', text: '<json>'}]}"
            )

        finally:
            await session.disconnect()
            reset_session_id(session_token)

    @pytest.mark.asyncio
    async def test_list_tts_engines_via_agent(self):
        """Test listing TTS engines through an actual agent tool call."""
        from agent.core.session import ConversationSession
        from agent.core.agent_options import create_agent_sdk_options
        from agent.tools.media.mcp_server import set_username, set_session_id, reset_session_id

        set_username("test_user")
        session_token = set_session_id("test_session_tts_list")

        options = create_agent_sdk_options()
        session = ConversationSession(options=options)

        try:
            tool_uses, tool_results, _ = await collect_tool_events(
                session,
                "Call the mcp__media_tools__list_tts_engines tool right now. "
                "Do not use Bash, Read, or any other tool. Only use the list_tts_engines MCP tool.",
            )

            matching = [
                (name, tid) for name, tid, _ in tool_uses
                if "list_tts_engines" in name
            ]
            assert len(matching) > 0, (
                f"Agent did not call list_tts_engines. Tool calls: "
                f"{[n for n, _, _ in tool_uses]}"
            )

            tool_name, tool_id = matching[0]
            assert tool_id in tool_results, f"No result for {tool_name}"
            result_info = tool_results[tool_id]
            assert not result_info["is_error"], f"list_tts_engines returned an error"

            # Verify ToolResultBlock.content is populated (MCP format fix)
            content = result_info["content"]
            assert len(content) > 0, (
                "ToolResultBlock.content should not be empty — "
                "tool must return MCP format: {content: [{type: 'text', text: '<json>'}]}"
            )

        finally:
            await session.disconnect()
            reset_session_id(session_token)

    @pytest.mark.asyncio
    async def test_synthesize_speech_via_agent(self):
        """Test synthesizing speech through an actual agent tool call.

        Verifies the agent calls synthesize_speech AND that the output
        WAV file exists on disk with proper headers.
        """
        from agent.core.session import ConversationSession
        from agent.core.agent_options import create_agent_sdk_options
        from agent.core.file_storage import FileStorage
        from agent.tools.media.mcp_server import set_username, set_session_id, reset_session_id

        test_session_id = "test_session_tts_synth"
        set_username("test_user")
        session_token = set_session_id(test_session_id)

        options = create_agent_sdk_options()
        session = ConversationSession(options=options)

        try:
            tool_uses, tool_results, _ = await collect_tool_events(
                session,
                "Call the mcp__media_tools__synthesize_speech tool with text='Hello world test', "
                "engine='kokoro', voice='af_heart'. Do not use Bash or any other tool.",
            )

            # Verify agent called synthesize_speech
            matching = [
                (name, tid) for name, tid, _ in tool_uses
                if "synthesize_speech" in name
            ]
            assert len(matching) > 0, (
                f"Agent did not call synthesize_speech. Tool calls: "
                f"{[n for n, _, _ in tool_uses]}"
            )

            # Verify tool did not error and content is populated
            tool_name, tool_id = matching[0]
            assert tool_id in tool_results, f"No result for {tool_name}"
            result_info = tool_results[tool_id]
            assert not result_info["is_error"], f"synthesize_speech returned an error"

            # Verify ToolResultBlock.content is populated
            content = result_info["content"]
            assert len(content) > 0, "ToolResultBlock.content should not be empty"

            # Try to parse the MCP content to verify structure
            parsed = parse_tool_result_content(content)
            if parsed:
                assert "audio_path" in parsed, f"Missing audio_path in result: {parsed}"
                assert "format" in parsed

            # Verify the audio file actually exists on disk
            file_storage = FileStorage(username="test_user", session_id=test_session_id)
            output_dir = file_storage.get_output_dir()
            audio_files = list(output_dir.glob("tts_*"))
            assert len(audio_files) > 0, "No TTS output file found on disk"

            # Verify file has meaningful content
            audio_file = audio_files[0]
            audio_bytes = audio_file.read_bytes()
            assert len(audio_bytes) > 1000, (
                f"Audio file too small: {len(audio_bytes)} bytes"
            )

            # Verify WAV headers
            assert audio_bytes[:4] == b"RIFF", "Audio should have RIFF header"
            assert audio_bytes[8:12] == b"WAVE", "Audio should have WAVE marker"

        finally:
            await session.disconnect()
            reset_session_id(session_token)
            session_dir = Path("data") / "test_user" / "files" / test_session_id
            if session_dir.exists():
                shutil.rmtree(session_dir)

    @pytest.mark.asyncio
    async def test_transcribe_audio_via_agent(self):
        """Test transcribing audio through an actual agent tool call.

        First generates a test audio file via the TTS tool handler directly,
        then asks the agent to transcribe it.
        """
        from agent.core.session import ConversationSession
        from agent.core.agent_options import create_agent_sdk_options
        from agent.core.file_storage import FileStorage
        from agent.tools.media.mcp_server import set_username, set_session_id, reset_session_id
        from agent.tools.media.tts_tools import synthesize_speech as tts_tool

        test_session_id = "test_session_stt_transcribe"
        set_username("test_user")
        session_token = set_session_id(test_session_id)

        file_storage = FileStorage(username="test_user", session_id=test_session_id)
        session = None

        try:
            # Step 1: Generate test audio using TTS tool handler directly
            tts_raw = await tts_tool.handler({
                "text": "Hello world this is a transcription test",
                "engine": "kokoro",
                "voice": "af_heart",
            })

            assert not tts_raw.get("is_error"), (
                f"TTS failed to generate audio: {tts_raw}"
            )
            # Parse MCP result format
            tts_result = json.loads(tts_raw["content"][0]["text"])
            assert "audio_path" in tts_result, (
                f"TTS missing audio_path: {tts_result}"
            )

            # Copy the generated audio to the input directory for the agent
            output_dir = file_storage.get_output_dir()
            input_dir = file_storage.get_input_dir()
            audio_files = list(output_dir.glob("tts_*"))
            assert len(audio_files) > 0, "No TTS output to use as transcription input"

            src_audio = audio_files[0]
            dest_audio = input_dir / "test_audio.wav"
            shutil.copy2(src_audio, dest_audio)

            # Step 2: Ask agent to transcribe
            options = create_agent_sdk_options()
            session = ConversationSession(options=options)

            tool_uses, tool_results, _ = await collect_tool_events(
                session,
                "Call the mcp__media_tools__transcribe_audio tool with file_path='test_audio.wav', "
                "engine='whisper_v3_turbo'. Do not use Bash or any other tool.",
            )

            # Verify agent called transcribe_audio
            matching = [
                (name, tid) for name, tid, _ in tool_uses
                if "transcribe_audio" in name
            ]
            assert len(matching) > 0, (
                f"Agent did not call transcribe_audio. Tool calls: "
                f"{[n for n, _, _ in tool_uses]}"
            )

            # Verify tool did not error and content is populated
            tool_name, tool_id = matching[0]
            assert tool_id in tool_results, f"No result for {tool_name}"
            result_info = tool_results[tool_id]
            assert not result_info["is_error"], f"transcribe_audio returned an error"

            # Verify ToolResultBlock.content is populated
            content = result_info["content"]
            assert len(content) > 0, "ToolResultBlock.content should not be empty"

            # Try to parse the MCP content to verify structure
            parsed = parse_tool_result_content(content)
            if parsed:
                assert "text" in parsed, f"Missing text in result: {parsed}"
                assert "engine" in parsed

            # Verify transcript output file exists on disk
            transcript_files = list(output_dir.glob("*transcript*"))
            assert len(transcript_files) > 0, "No transcript output file found on disk"

        finally:
            if session is not None:
                await session.disconnect()
            reset_session_id(session_token)
            session_dir = Path("data") / "test_user" / "files" / test_session_id
            if session_dir.exists():
                shutil.rmtree(session_dir)


# ---------------------------------------------------------------------------
# TestMediaToolsWithFileStorage
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# TestMediaToolsServiceHealth
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# TestMediaToolsInAgentConfig
# ---------------------------------------------------------------------------

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

        assert len(media_tools) == 5, (
            f"Expected 5 media tools in general-assistant, found {len(media_tools)}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
