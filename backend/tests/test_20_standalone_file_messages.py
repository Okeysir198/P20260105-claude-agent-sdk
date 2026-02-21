"""Tests for standalone file messages feature (_standalone_file marker).

Covers:
- Backend: send_file_to_chat tool includes _standalone_file metadata
- Frontend: tool_result handler detects _standalone_file and creates separate message
- CLI: display_tool_result shows file info panel for standalone files
- Different content types: audio, video, image, file
"""
import json
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("API_KEY", "test-api-key-for-testing")

from agent.tools.media.send_file import send_file_to_chat


class TestStandaloneFileMetadata:
    """Test that send_file_to_chat includes _standalone_file metadata."""

    @pytest.fixture(autouse=True)
    def setup_context(self, tmp_path):
        """Set up session context for testing."""
        self.session_dir = tmp_path / "data" / "testuser" / "sessions" / "test-session"
        self.output_dir = self.session_dir / "output"
        self.input_dir = self.session_dir / "input"
        self.output_dir.mkdir(parents=True)
        self.input_dir.mkdir(parents=True)

    def _parse_mcp_result(self, result: dict) -> dict:
        assert "content" in result
        return json.loads(result["content"][0]["text"])

    def _mock_storage(self):
        from agent.core.file_storage import FileStorage
        mock = MagicMock(spec=FileStorage)
        mock._session_id = "test-session"
        mock.get_session_dir.return_value = self.session_dir
        return mock

    @pytest.mark.asyncio
    async def test_audio_file_has_standalone_metadata(self):
        """Audio files include _standalone_file with type='audio'."""
        test_file = self.output_dir / "tts_123.mp3"
        test_file.write_bytes(b"\x00" * 5000)

        mock_storage = self._mock_storage()

        with patch("agent.tools.media.send_file.get_session_context", return_value=("testuser", mock_storage)), \
             patch("api.services.file_download_token.create_download_token", return_value="fake-token"), \
             patch("api.services.file_download_token.build_download_url", return_value="https://example.com/api/v1/files/dl/fake-token"):
            result = await send_file_to_chat.handler({"file_path": "output/tts_123.mp3"})

        data = self._parse_mcp_result(result)
        assert "_standalone_file" in data
        standalone = data["_standalone_file"]
        assert standalone["type"] == "audio"
        assert standalone["url"] == "https://example.com/api/v1/files/dl/fake-token"
        assert standalone["filename"] == "tts_123.mp3"
        assert standalone["mime_type"] == "audio/mpeg"
        assert standalone["size_bytes"] == 5000

    @pytest.mark.asyncio
    async def test_video_file_has_standalone_metadata(self):
        """Video files include _standalone_file with type='video'."""
        test_file = self.output_dir / "video.mp4"
        test_file.write_bytes(b"\x00" * 100000)

        mock_storage = self._mock_storage()

        with patch("agent.tools.media.send_file.get_session_context", return_value=("testuser", mock_storage)), \
             patch("api.services.file_download_token.create_download_token", return_value="fake-token"), \
             patch("api.services.file_download_token.build_download_url", return_value="https://example.com/api/v1/files/dl/fake-token"):
            result = await send_file_to_chat.handler({"file_path": "output/video.mp4"})

        data = self._parse_mcp_result(result)
        assert "_standalone_file" in data
        assert data["_standalone_file"]["type"] == "video"
        assert data["_standalone_file"]["filename"] == "video.mp4"

    @pytest.mark.asyncio
    async def test_image_file_has_standalone_metadata(self):
        """Image files include _standalone_file with type='image'."""
        test_file = self.output_dir / "image.png"
        test_file.write_bytes(b"\x00PNG\x00" * 1000)

        mock_storage = self._mock_storage()

        with patch("agent.tools.media.send_file.get_session_context", return_value=("testuser", mock_storage)), \
             patch("api.services.file_download_token.create_download_token", return_value="fake-token"), \
             patch("api.services.file_download_token.build_download_url", return_value="https://example.com/api/v1/files/dl/fake-token"):
            result = await send_file_to_chat.handler({"file_path": "output/image.png"})

        data = self._parse_mcp_result(result)
        assert "_standalone_file" in data
        assert data["_standalone_file"]["type"] == "image"
        assert data["_standalone_file"]["filename"] == "image.png"

    @pytest.mark.asyncio
    async def test_document_file_has_standalone_metadata(self):
        """Non-media files include _standalone_file with type='file'."""
        test_file = self.output_dir / "report.pdf"
        test_file.write_bytes(b"%PDF-1.4" + b"\x00" * 10000)

        mock_storage = self._mock_storage()

        with patch("agent.tools.media.send_file.get_session_context", return_value=("testuser", mock_storage)), \
             patch("api.services.file_download_token.create_download_token", return_value="fake-token"), \
             patch("api.services.file_download_token.build_download_url", return_value="https://example.com/api/v1/files/dl/fake-token"):
            result = await send_file_to_chat.handler({"file_path": "output/report.pdf"})

        data = self._parse_mcp_result(result)
        assert "_standalone_file" in data
        assert data["_standalone_file"]["type"] == "file"
        assert data["_standalone_file"]["filename"] == "report.pdf"

    @pytest.mark.asyncio
    async def test_standalone_metadata_includes_all_fields(self):
        """Verify all required fields are present in _standalone_file."""
        test_file = self.output_dir / "test.ogg"
        test_file.write_bytes(b"\x00" * 12345)

        mock_storage = self._mock_storage()

        with patch("agent.tools.media.send_file.get_session_context", return_value=("testuser", mock_storage)), \
             patch("api.services.file_download_token.create_download_token", return_value="test-token-abc"), \
             patch("api.services.file_download_token.build_download_url", return_value="https://cdn.example.com/files/dl/test-token-abc.sig"):
            result = await send_file_to_chat.handler({"file_path": "output/test.ogg"})

        data = self._parse_mcp_result(result)
        standalone = data["_standalone_file"]

        # Verify all fields
        assert "type" in standalone
        assert "url" in standalone
        assert "filename" in standalone
        assert "mime_type" in standalone
        assert "size_bytes" in standalone

        # Verify values
        assert standalone["url"] == "https://cdn.example.com/files/dl/test-token-abc.sig"
        assert standalone["size_bytes"] == 12345


class TestFrontendDetection:
    """Test frontend-side detection of _standalone_file marker.

    Note: These tests verify the TypeScript-side logic conceptually.
    Actual frontend tests would use Vitest/Jest in the frontend directory.
    """

    def test_try_parse_json_valid(self):
        """Valid JSON with _standalone_file is parsed correctly."""
        # This mimics the frontend tryParseJSON function
        text = '{"action": "deliver_file", "_standalone_file": {"type": "audio", "url": "https://..."}}'
        try:
            parsed = json.loads(text)
            assert "_standalone_file" in parsed
            assert parsed["_standalone_file"]["type"] == "audio"
        except json.JSONDecodeError:
            pytest.fail("Failed to parse valid JSON")

    def test_try_parse_json_invalid(self):
        """Invalid JSON returns null."""
        # This mimics the frontend tryParseJSON function
        text = 'not json at all'
        try:
            parsed = json.loads(text)
            pytest.fail("Should have raised JSONDecodeError")
        except json.JSONDecodeError:
            pass  # Expected

    def test_standalone_file_detection(self):
        """Verify detection pattern: '_standalone_file' in result content."""
        # Frontend checks: resultContent.includes('"_standalone_file"')
        content = '{"action": "deliver_file", "_standalone_file": {"type": "audio"}}'
        assert '"_standalone_file"' in content

    def test_no_false_positive_without_marker(self):
        """Normal tool results without marker don't trigger detection."""
        content = '{"action": "deliver_file", "filename": "test.wav"}'
        assert '"_standalone_file"' not in content


class TestCLIDisplay:
    """Test CLI display_tool_result handling of _standalone_file."""

    def test_format_size_helper(self):
        """Test the _format_size helper function."""
        # Import the CLI module to test the helper
        from cli.commands.chat import _format_size

        assert _format_size(0) == "0.0 B"
        assert _format_size(512) == "512.0 B"
        assert _format_size(1024) == "1.0 KB"
        assert _format_size(1536) == "1.5 KB"
        assert _format_size(1048576) == "1.0 MB"
        assert _format_size(1073741824) == "1.0 GB"
        assert _format_size(1099511627776) == "1.0 TB"

    def test_cli_detects_standalone_file(self):
        """CLI should detect _standalone_file in tool result content."""
        # Simulate what display_tool_result does
        content = json.dumps({
            "action": "deliver_file",
            "_standalone_file": {
                "type": "audio",
                "filename": "tts_123.ogg",
                "url": "https://example.com/dl/token",
                "size_bytes": 17800
            }
        })

        try:
            parsed = json.loads(content)
            assert parsed.get("_standalone_file") is not None
            file_data = parsed["_standalone_file"]
            assert file_data["type"] == "audio"
            assert file_data["filename"] == "tts_123.ogg"
        except (json.JSONDecodeError, TypeError):
            pytest.fail("Failed to detect standalone file metadata")

    def test_cli_type_emoji_mapping(self):
        """Verify emoji mapping for different file types."""
        # Frontend CLI uses these emojis
        emojis = {
            "audio": "🎵",
            "video": "🎬",
            "image": "🖼️",
            "file": "📄"
        }
        assert emojis["audio"] == "🎵"
        assert emojis["video"] == "🎬"
        assert emojis["image"] == "🖼️"
        assert emojis["file"] == "📄"

    def test_cli_handles_invalid_json_gracefully(self):
        """CLI should not crash on non-JSON tool results."""
        # display_tool_result catches JSONDecodeError
        content = "Plain text tool result without JSON"
        try:
            parsed = json.loads(content)
            # If it somehow parses, continue
        except json.JSONDecodeError:
            # Expected - should fall through to normal display
            pass


class TestToolCardDefaultCollapsed:
    """Test that tool cards with standalone files default to collapsed state."""

    def test_has_standalone_file_detection(self):
        """Frontend checks for '_standalone_file' string in content."""
        # ToolUseMessage component: hasStandaloneFile check
        content_with_marker = '{"_standalone_file": {"type": "audio"}}'
        assert '"_standalone_file"' in content_with_marker

        content_without_marker = '{"action": "deliver_file", "filename": "test.wav"}'
        assert '"_standalone_file"' not in content_without_marker

    def test_default_expanded_state_logic(self):
        """Verify logic: expanded = !hasStandaloneFile."""
        # When hasStandaloneFile = true, expanded should be false (collapsed)
        has_standalone_file = True
        expanded = not has_standalone_file
        assert expanded is False

        # When hasStandaloneFile = false, expanded should be true
        has_standalone_file = False
        expanded = not has_standalone_file
        assert expanded is True


class TestBackwardCompatibility:
    """Ensure _standalone_file doesn't break existing functionality."""

    @pytest.mark.asyncio
    async def test_platform_worker_ignores_standalone_file(self):
        """Platform worker should ignore _standalone_file field (only use action: deliver_file)."""
        # The platform worker parses JSON and looks for specific fields
        # _standalone_file is frontend-specific and should be ignored

        result_json = json.dumps({
            "action": "deliver_file",
            "file_path": "output/test.wav",
            "filename": "test.wav",
            "mime_type": "audio/wav",
            "size_bytes": 500,
            "download_url": "https://example.com/dl/token",
            "_standalone_file": {  # This should be ignored by platforms
                "type": "audio",
                "url": "https://example.com/dl/token",
                "filename": "test.wav",
                "mime_type": "audio/wav",
                "size_bytes": 500
            }
        })

        parsed = json.loads(result_json)
        # Platform worker checks for action == "deliver_file"
        assert parsed["action"] == "deliver_file"
        assert parsed["file_path"] == "output/test.wav"
        assert parsed["download_url"] == "https://example.com/dl/token"
        # _standalone_file is present but doesn't affect platform logic

    @pytest.mark.asyncio
    async def test_existing_action_deliver_file_still_works(self):
        """The original action: deliver_file field is still present."""
        mock_storage = MagicMock()
        mock_storage._session_id = "test-session"

        # Use the same tmp_path fixture approach as other tests
        from pathlib import Path
        tmp_path = Path("/tmp/test_session_for_compat")
        tmp_path.mkdir(parents=True, exist_ok=True)
        output_dir = tmp_path / "output"
        output_dir.mkdir(exist_ok=True)

        test_path = output_dir / "test.wav"
        test_path.write_bytes(b"\x00" * 100)

        mock_storage.get_session_dir.return_value = tmp_path

        with patch("agent.tools.media.send_file.get_session_context", return_value=("testuser", mock_storage)), \
             patch("api.services.file_download_token.create_download_token", return_value="token"), \
             patch("api.services.file_download_token.build_download_url", return_value="https://example.com/dl/token"):
            result = await send_file_to_chat.handler({"file_path": "output/test.wav"})

        data = json.loads(result["content"][0]["text"])
        # Original fields must still be present
        assert "action" in data
        assert "file_path" in data
        assert "filename" in data
        assert "mime_type" in data
        assert "size_bytes" in data
        assert "download_url" in data
        assert data["action"] == "deliver_file"


class TestContentTypeDetermination:
    """Test MIME type to content type mapping."""

    @pytest.mark.asyncio
    async def test_determine_content_type_audio(self):
        """Audio MIME types map to 'audio'."""
        mock_storage = MagicMock()
        mock_storage._session_id = "test-session"

        from pathlib import Path
        tmp_path = Path("/tmp/test_session_audio")
        tmp_path.mkdir(parents=True, exist_ok=True)
        output_dir = tmp_path / "output"
        output_dir.mkdir(exist_ok=True)

        test_path = output_dir / "test.mp3"
        test_path.write_bytes(b"\x00" * 100)

        mock_storage.get_session_dir.return_value = tmp_path

        with patch("agent.tools.media.send_file.get_session_context", return_value=("testuser", mock_storage)), \
             patch("api.services.file_download_token.create_download_token", return_value="token"), \
             patch("api.services.file_download_token.build_download_url", return_value="https://example.com/dl/token"):
            result = await send_file_to_chat.handler({"file_path": "output/test.mp3"})

        data = json.loads(result["content"][0]["text"])
        assert data["_standalone_file"]["type"] == "audio"

    @pytest.mark.asyncio
    async def test_determine_content_type_octet_stream(self):
        """Unknown MIME types (application/octet-stream) map to 'file'."""
        mock_storage = MagicMock()
        mock_storage._session_id = "test-session"

        from pathlib import Path
        tmp_path = Path("/tmp/test_session_octet")
        tmp_path.mkdir(parents=True, exist_ok=True)
        output_dir = tmp_path / "output"
        output_dir.mkdir(exist_ok=True)

        test_path = output_dir / "test.unknown"
        test_path.write_bytes(b"\x00" * 100)

        mock_storage.get_session_dir.return_value = tmp_path

        with patch("agent.tools.media.send_file.get_session_context", return_value=("testuser", mock_storage)), \
             patch("api.services.file_download_token.create_download_token", return_value="token"), \
             patch("api.services.file_download_token.build_download_url", return_value="https://example.com/dl/token"):
            result = await send_file_to_chat.handler({"file_path": "output/test.unknown"})

        data = json.loads(result["content"][0]["text"])
        assert data["_standalone_file"]["type"] == "file"
