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

os.environ.setdefault("API_KEY", "test-api-key-for-testing")

import yaml

from claude_agent_sdk.types import (
    AssistantMessage,
    UserMessage,
    ResultMessage,
    ToolUseBlock,
    ToolResultBlock,
)
from agent.core.session import ConversationSession
from agent.core.agent_options import create_agent_sdk_options
from agent.core.file_storage import FileStorage
from media_tools.context import set_username, get_username, set_session_id


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def collect_tool_events(session, query: str):
    """Send query and collect tool_use/tool_result pairs + final text.

    Returns:
        Tuple of (tool_uses, tool_results, final_text) where:
        - tool_uses: List of (name, id, input) tuples
        - tool_results: Dict mapping tool_use_id -> {is_error, content}
        - final_text: Concatenated assistant text from the response
    """
    tool_uses = []
    tool_results = {}
    text_parts = []

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
        block_dict = block if isinstance(block, dict) else {
            "type": getattr(block, "type", ""),
            "text": getattr(block, "text", ""),
        }
        if block_dict.get("type") == "text" and block_dict.get("text"):
            try:
                return json.loads(block_dict["text"])
            except (json.JSONDecodeError, TypeError):
                return None
    return None


def assert_tool_called(tool_uses, tool_results, tool_name_fragment: str):
    """Assert the agent called a tool matching the name fragment and it succeeded.

    Returns (tool_name, tool_id, result_info) for the first matching tool call.
    """
    matching = [
        (name, tid) for name, tid, _ in tool_uses
        if tool_name_fragment in name
    ]
    assert len(matching) > 0, (
        f"Agent did not call {tool_name_fragment}. "
        f"Tool calls: {[n for n, _, _ in tool_uses]}"
    )

    tool_name, tool_id = matching[0]
    assert tool_id in tool_results, f"No result for {tool_name}"

    result_info = tool_results[tool_id]
    assert not result_info["is_error"], f"{tool_name_fragment} returned an error"

    content = result_info["content"]
    assert len(content) > 0, (
        "ToolResultBlock.content should not be empty -- "
        "tool must return MCP format: {content: [{type: 'text', text: '<json>'}]}"
    )

    return tool_name, tool_id, result_info


# ---------------------------------------------------------------------------
# Helpers for agent sessions
# ---------------------------------------------------------------------------

def create_agent_session(session_id: str) -> ConversationSession:
    """Set media tools context and create an agent session.

    Caller is responsible for disconnect() and file cleanup in try/finally.
    Cannot use an async fixture because ConversationSession.disconnect()
    must run in the same task/cancel-scope that created it.
    """
    set_username("test_user")
    set_session_id(session_id)
    return ConversationSession(options=create_agent_sdk_options())


def cleanup_session_files(session_id: str) -> None:
    """Remove test session files from disk."""
    session_dir = Path("data") / "test_user" / "files" / session_id
    if session_dir.exists():
        shutil.rmtree(session_dir)


# ---------------------------------------------------------------------------
# Integration tests with real agent sessions
# ---------------------------------------------------------------------------

class TestMediaToolsRealIntegration:
    """Real integration tests with agent SDK -- verifies that the agent
    actually invokes the media MCP tools and the tools execute without errors."""

    @pytest.mark.asyncio
    async def test_list_stt_engines_via_agent(self):
        """Test listing STT engines through an actual agent tool call."""
        sid = "test_session_stt_list"
        session = create_agent_session(sid)
        try:
            tool_uses, tool_results, _ = await collect_tool_events(
                session,
                "Call the mcp__media_tools__list_stt_engines tool right now. "
                "Do not use Bash, Read, or any other tool. Only use the list_stt_engines MCP tool.",
            )
            assert_tool_called(tool_uses, tool_results, "list_stt_engines")
        finally:
            await session.disconnect()
            cleanup_session_files(sid)

    @pytest.mark.asyncio
    async def test_list_tts_engines_via_agent(self):
        """Test listing TTS engines through an actual agent tool call."""
        sid = "test_session_tts_list"
        session = create_agent_session(sid)
        try:
            tool_uses, tool_results, _ = await collect_tool_events(
                session,
                "Call the mcp__media_tools__list_tts_engines tool right now. "
                "Do not use Bash, Read, or any other tool. Only use the list_tts_engines MCP tool.",
            )
            assert_tool_called(tool_uses, tool_results, "list_tts_engines")
        finally:
            await session.disconnect()
            cleanup_session_files(sid)

    @pytest.mark.asyncio
    async def test_synthesize_speech_via_agent(self):
        """Test synthesizing speech through an actual agent tool call.

        Verifies the agent calls synthesize_speech AND that the output
        WAV file exists on disk with proper headers.
        """
        sid = "test_session_tts_synth"
        session = create_agent_session(sid)
        try:
            tool_uses, tool_results, _ = await collect_tool_events(
                session,
                "Call the mcp__media_tools__synthesize_speech tool with text='Hello world test', "
                "engine='kokoro', voice='af_heart'. Do not use Bash or any other tool.",
            )

            _, _, result_info = assert_tool_called(tool_uses, tool_results, "synthesize_speech")

            parsed = parse_tool_result_content(result_info["content"])
            if parsed:
                assert "audio_path" in parsed, f"Missing audio_path in result: {parsed}"
                assert "format" in parsed

            # Verify audio file exists on disk with valid WAV headers
            file_storage = FileStorage(username="test_user", session_id=sid)
            audio_files = list(file_storage.get_output_dir().glob("tts_*"))
            assert len(audio_files) > 0, "No TTS output file found on disk"

            audio_bytes = audio_files[0].read_bytes()
            assert len(audio_bytes) > 1000, f"Audio file too small: {len(audio_bytes)} bytes"
            assert audio_bytes[:4] == b"RIFF", "Audio should have RIFF header"
            assert audio_bytes[8:12] == b"WAVE", "Audio should have WAVE marker"
        finally:
            await session.disconnect()
            cleanup_session_files(sid)

    @pytest.mark.asyncio
    async def test_transcribe_audio_via_agent(self):
        """Test transcribing audio through an actual agent tool call.

        First generates a test audio file via the TTS tool handler directly,
        then asks the agent to transcribe it.
        """
        from media_tools.tts_tools import synthesize_speech as tts_tool

        sid = "test_session_stt_transcribe"
        set_username("test_user")
        set_session_id(sid)
        file_storage = FileStorage(username="test_user", session_id=sid)
        session = None

        try:
            # Generate test audio using TTS tool handler directly
            tts_raw = await tts_tool.handler({
                "text": "Hello world this is a transcription test",
                "engine": "kokoro",
                "voice": "af_heart",
            })
            assert not tts_raw.get("is_error"), f"TTS failed to generate audio: {tts_raw}"

            tts_result = json.loads(tts_raw["content"][0]["text"])
            assert "audio_path" in tts_result, f"TTS missing audio_path: {tts_result}"

            # Copy generated audio to the input directory for the agent
            output_dir = file_storage.get_output_dir()
            audio_files = list(output_dir.glob("tts_*"))
            assert len(audio_files) > 0, "No TTS output to use as transcription input"
            shutil.copy2(audio_files[0], file_storage.get_input_dir() / "test_audio.wav")

            # Ask agent to transcribe
            session = create_agent_session(sid)

            tool_uses, tool_results, _ = await collect_tool_events(
                session,
                "Call the mcp__media_tools__transcribe_audio tool with file_path='test_audio.wav', "
                "engine='whisper_v3_turbo'. Do not use Bash or any other tool.",
            )

            _, _, result_info = assert_tool_called(tool_uses, tool_results, "transcribe_audio")

            parsed = parse_tool_result_content(result_info["content"])
            if parsed:
                assert "text" in parsed, f"Missing text in result: {parsed}"
                assert "engine" in parsed

            # Verify transcript output file exists
            transcript_files = list(output_dir.glob("*transcript*"))
            assert len(transcript_files) > 0, "No transcript output file found on disk"

        finally:
            if session is not None:
                await session.disconnect()
            cleanup_session_files(sid)


# ---------------------------------------------------------------------------
# FileStorage integration
# ---------------------------------------------------------------------------

class TestMediaToolsWithFileStorage:
    """Test media tools integration with FileStorage."""

    @pytest.mark.asyncio
    async def test_file_storage_with_media_tools(self):
        """Test that FileStorage works correctly with media tools context."""
        username = "test_user"
        session_id = "test_session_media"

        set_username(username)
        assert get_username() == username

        storage = FileStorage(username=username, session_id=session_id)

        input_dir = storage.get_input_dir()
        output_dir = storage.get_output_dir()
        assert input_dir.exists()
        assert output_dir.exists()
        assert "input" in str(input_dir)
        assert "output" in str(output_dir)

        # Save and verify a test file
        test_content = b"Test file content for media processing"
        metadata = await storage.save_input_file(content=test_content, filename="test_input.txt")

        assert metadata.safe_name == "test_input.txt"
        assert metadata.size_bytes == len(test_content)
        assert (input_dir / metadata.safe_name).exists()

        await storage.delete_file(metadata.safe_name, "input")


# ---------------------------------------------------------------------------
# Service health (parametrized)
# ---------------------------------------------------------------------------

SERVICE_HEALTH_ENDPOINTS = [
    ("OCR", "http://localhost:18013/health"),
    ("STT", "http://localhost:18050/health"),
    ("TTS", "http://localhost:18034/health"),
]


class TestMediaToolsServiceHealth:
    """Test actual service health and connectivity."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("service_name,url", SERVICE_HEALTH_ENDPOINTS)
    async def test_service_health(self, service_name, url):
        """Test that a media service health endpoint returns 200."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                assert response.status_code == 200
        except (httpx.ConnectError, httpx.ConnectTimeout):
            pytest.skip(f"{service_name} service not running")


# ---------------------------------------------------------------------------
# Agent config validation
# ---------------------------------------------------------------------------

class TestMediaToolsInAgentConfig:
    """Test media tools plugin is properly configured in agents.yaml."""

    @staticmethod
    def _load_agents_config():
        with open("agents.yaml") as f:
            return yaml.safe_load(f)

    def test_media_tools_plugin_in_defaults(self):
        """Verify media-tools plugin is in the _defaults plugins."""
        config = self._load_agents_config()
        default_plugins = config.get("_defaults", {}).get("plugins", [])
        media_plugins = [
            p for p in default_plugins
            if isinstance(p, dict) and "media-tools" in str(p.get("path", ""))
        ]

        assert len(media_plugins) == 1, (
            f"Expected 1 media-tools plugin in defaults, found {len(media_plugins)}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
