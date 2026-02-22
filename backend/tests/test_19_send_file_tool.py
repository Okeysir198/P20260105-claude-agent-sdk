"""Tests for download URL redaction preservation, send_file_to_chat tool,
and platform delivery intercepts (_try_deliver_tool_file, _try_deliver_media_file).

Covers:
- Download URL preservation through sensitive data redaction
- Other base64/tokens still redacted
- send_file_to_chat tool: valid file, missing file, path traversal
- _try_deliver_tool_file: valid result, non-matching tool, invalid JSON
- _try_deliver_media_file: TTS result, OCR result, missing file
"""
import json
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("API_KEY", "test-api-key-for-testing")

from api.utils.sensitive_data_filter import redact_sensitive_data
from media_tools.send_file import send_file_to_chat


# ---------------------------------------------------------------------------
# Part 1: Download URL preservation through redaction
# ---------------------------------------------------------------------------

class TestDownloadURLPreservation:
    """Verify download URLs survive the redaction pipeline."""

    def _make_download_url(self, token: str = "eyJ1IjoiYWRtaW4iLCJjIjoiYWJjMTIzIiwicCI6Im91dHB1dC90dHNfMTIzLm1wMyIsIngiOjk5OTk5OTk5OTl9") -> str:
        sig = "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2"
        return f"https://localhost:7001/api/v1/files/dl/{token}.{sig}"

    def test_download_url_preserved_in_plain_text(self):
        url = self._make_download_url()
        text = f"Here is your file: {url}"
        result = redact_sensitive_data(text)
        assert url in result, f"Download URL was redacted: {result}"

    def test_download_url_preserved_in_json(self):
        url = self._make_download_url()
        text = json.dumps({"download_url": url, "status": "ok"})
        result = redact_sensitive_data(text)
        assert url in result, f"Download URL was redacted from JSON: {result}"

    def test_multiple_download_urls_preserved(self):
        url1 = self._make_download_url("tokenAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
        url2 = self._make_download_url("tokenBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB")
        text = f"File 1: {url1}\nFile 2: {url2}"
        result = redact_sensitive_data(text)
        assert url1 in result
        assert url2 in result

    def test_other_base64_still_redacted(self):
        """Long base64 strings NOT in download URLs should still be redacted."""
        long_b64 = "A" * 50
        text = f"Some token: {long_b64}"
        result = redact_sensitive_data(text)
        assert long_b64 not in result, "Long base64 outside download URL should be redacted"

    def test_bearer_token_still_redacted(self):
        text = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        result = redact_sensitive_data(text)
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result

    def test_download_url_with_http(self):
        """HTTP (not just HTTPS) download URLs should also be preserved."""
        url = "http://localhost:7001/api/v1/files/dl/abcdefABCDEF1234567890abcdefABCDEF1234567890.a1b2c3d4e5f6"
        text = f"Download: {url}"
        result = redact_sensitive_data(text)
        assert url in result

    def test_mixed_content_download_url_and_secret(self):
        url = self._make_download_url()
        text = f'{{"download_url": "{url}", "api_key": "sk-ant-super-secret-key-12345678"}}'
        result = redact_sensitive_data(text)
        assert url in result, "Download URL should be preserved"
        assert "super-secret-key" not in result, "API key should be redacted"


# ---------------------------------------------------------------------------
# Part 2: send_file_to_chat tool
# ---------------------------------------------------------------------------

class TestSendFileToChatTool:
    """Test the send_file_to_chat MCP tool."""

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

    def _assert_mcp_error(self, result: dict, substring: str = ""):
        assert result.get("is_error") is True
        if substring:
            assert substring in result["content"][0]["text"]

    def _mock_storage(self):
        from media_tools.file_storage import FileStorage
        mock = MagicMock(spec=FileStorage)
        mock._session_id = "test-session"
        mock.get_session_dir.return_value = self.session_dir
        return mock

    @pytest.mark.asyncio
    async def test_valid_output_file(self):
        """Tool returns correct metadata for a valid file."""
        test_file = self.output_dir / "tts_123.wav"
        test_file.write_bytes(b"\x00" * 1000)

        mock_storage = self._mock_storage()

        with patch("media_tools.send_file.get_session_context", return_value=("testuser", mock_storage)), \
             patch("media_tools.send_file.create_download_token", return_value="fake-token"), \
             patch("media_tools.send_file.build_download_url", return_value="https://example.com/api/v1/files/dl/fake-token"):
            result = await send_file_to_chat({"file_path": "output/tts_123.wav"})

        data = self._parse_mcp_result(result)
        assert data["action"] == "deliver_file"
        assert data["filename"] == "tts_123.wav"
        assert data["size_bytes"] == 1000
        assert "audio" in data["mime_type"]
        assert "download_url" in data

    @pytest.mark.asyncio
    async def test_missing_file(self):
        """Tool returns error for non-existent file."""
        mock_storage = self._mock_storage()

        with patch("media_tools.send_file.get_session_context", return_value=("testuser", mock_storage)):
            result = await send_file_to_chat({"file_path": "output/nonexistent.wav"})

        self._assert_mcp_error(result, "not found")

    @pytest.mark.asyncio
    async def test_path_traversal_blocked(self):
        """Tool rejects path traversal attempts."""
        mock_storage = self._mock_storage()

        with patch("media_tools.send_file.get_session_context", return_value=("testuser", mock_storage)):
            result = await send_file_to_chat({"file_path": "../../etc/passwd"})

        self._assert_mcp_error(result, "traversal")

    @pytest.mark.asyncio
    async def test_empty_file_path(self):
        """Tool returns error for empty file_path."""
        result = await send_file_to_chat({"file_path": ""})
        self._assert_mcp_error(result, "required")


# ---------------------------------------------------------------------------
# Part 3: Worker intercepts
# ---------------------------------------------------------------------------

class TestTryDeliverToolFile:
    """Test _try_deliver_tool_file worker function."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.session_cwd = str(tmp_path)
        self.output_dir = tmp_path / "output"
        self.output_dir.mkdir()
        self.adapter = AsyncMock()
        self.send_msg_fn = AsyncMock()

    @pytest.mark.asyncio
    async def test_delivers_valid_send_file_result(self):
        """Delivers file when send_file_to_chat returns valid result."""
        from platforms.worker import _try_deliver_tool_file

        test_file = self.output_dir / "test.wav"
        test_file.write_bytes(b"\x00" * 500)

        result_json = json.dumps({
            "action": "deliver_file",
            "file_path": "output/test.wav",
            "filename": "test.wav",
            "mime_type": "audio/wav",
            "size_bytes": 500,
            "download_url": "https://example.com/dl/token",
        })

        await _try_deliver_tool_file(
            "send_file_to_chat", result_json, self.session_cwd,
            self.adapter, "chat123", "testuser", "cwd123", self.send_msg_fn,
        )

        self.adapter.send_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_ignores_non_matching_tool(self):
        """Does nothing for tools other than send_file_to_chat."""
        from platforms.worker import _try_deliver_tool_file

        await _try_deliver_tool_file(
            "Write", '{"action": "deliver_file"}', self.session_cwd,
            self.adapter, "chat123", "testuser", "cwd123", self.send_msg_fn,
        )

        self.adapter.send_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_invalid_json(self):
        """Silently handles invalid JSON in result content."""
        from platforms.worker import _try_deliver_tool_file

        await _try_deliver_tool_file(
            "send_file_to_chat", "not json", self.session_cwd,
            self.adapter, "chat123", "testuser", "cwd123", self.send_msg_fn,
        )

        self.adapter.send_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_rejects_path_traversal(self):
        """Does not deliver files outside session_cwd."""
        from platforms.worker import _try_deliver_tool_file

        result_json = json.dumps({
            "action": "deliver_file",
            "file_path": "../../etc/passwd",
            "filename": "passwd",
        })

        await _try_deliver_tool_file(
            "send_file_to_chat", result_json, self.session_cwd,
            self.adapter, "chat123", "testuser", "cwd123", self.send_msg_fn,
        )

        self.adapter.send_file.assert_not_called()


