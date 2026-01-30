"""
Unit tests for the search service.

Run: pytest tests/test_08_session_search.py -v
"""
from pathlib import Path
from unittest.mock import Mock, patch
import pytest
import tempfile
import json

from api.services.search_service import (
    SessionSearchService,
    SearchResult,
    SearchOptions,
)


@pytest.fixture
def mock_history_storage(temp_storage_dir):
    """Create mock history storage with test data."""
    history_dir = temp_storage_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)

    def create_history_file(session_id: str, messages: list[dict]):
        history_file = history_dir / f"{session_id}.jsonl"
        with open(history_file, "w", encoding="utf-8") as f:
            for msg in messages:
                f.write(json.dumps(msg) + "\n")
        return history_file

    return temp_storage_dir, create_history_file


@pytest.fixture
def mock_session_storage():
    """Create mock session storage."""
    mock_storage = Mock()
    mock_session1 = Mock(session_id="session-1", name="Test Session One", first_message="First message")
    mock_session2 = Mock(session_id="session-2", name="Python Discussion", first_message="How to use Python")
    mock_session3 = Mock(session_id="session-3", name="Tool Usage", first_message="Using tools")
    mock_storage.load_sessions.return_value = [mock_session1, mock_session2, mock_session3]
    return mock_storage


@pytest.fixture
def temp_storage_dir():
    """Create a temporary directory for test storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestSearchServiceBasic:
    """Test basic search functionality."""

    def test_search_empty_query(self, mock_session_storage):
        """Verify that empty query returns no results."""
        service = SessionSearchService()
        with patch("api.services.search_service.get_user_session_storage") as mock_get_storage:
            mock_get_storage.return_value = mock_session_storage
            results = service.search_sessions("testuser", "")
            assert results == []

    def test_search_single_match(self, mock_history_storage, mock_session_storage):
        """Search for term appearing once and verify correct result."""
        temp_dir, create_history = mock_history_storage
        messages = [
            {"role": "user", "content": "Hello world"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "Tell me about elephants"},
            {"role": "assistant", "content": "Elephants are large mammals."},
        ]
        create_history("session-1", messages)

        service = SessionSearchService()

        with patch("api.services.search_service.get_user_session_storage") as mock_get_sess:
            mock_get_sess.return_value = mock_session_storage

            with patch("api.services.search_service.get_user_history_storage") as mock_get_hist:
                def mock_history_file(session_id):
                    file_path = temp_dir / "history" / f"{session_id}.jsonl"
                    if not file_path.exists():
                        mock_file = Mock()
                        mock_file.exists.return_value = False
                        return mock_file
                    return file_path

                mock_storage = Mock()
                mock_storage._get_history_file.side_effect = mock_history_file
                mock_get_hist.return_value = mock_storage

                results = service.search_sessions("testuser", "elephants")

                assert len(results) == 1
                assert results[0].session_id == "session-1"
                assert results[0].match_count == 2

    def test_search_case_insensitive(self, mock_history_storage, mock_session_storage):
        """Verify case-insensitive matching works."""
        temp_dir, create_history = mock_history_storage
        messages = [
            {"role": "user", "content": "I want to learn Python programming"},
            {"role": "assistant", "content": "PYTHON is a great language"},
        ]
        create_history("session-2", messages)

        service = SessionSearchService()

        with patch("api.services.search_service.get_user_session_storage") as mock_get_sess:
            mock_get_sess.return_value = mock_session_storage

            with patch("api.services.search_service.get_user_history_storage") as mock_get_hist:
                def mock_history_file(session_id):
                    file_path = temp_dir / "history" / f"{session_id}.jsonl"
                    if not file_path.exists():
                        mock_file = Mock()
                        mock_file.exists.return_value = False
                        return mock_file
                    return file_path

                mock_storage = Mock()
                mock_storage._get_history_file.side_effect = mock_history_file
                mock_get_hist.return_value = mock_storage

                results_lower = service.search_sessions("testuser", "python")
                results_upper = service.search_sessions("testuser", "PYTHON")

                assert len(results_lower) == 1
                assert len(results_upper) == 1
                assert results_lower[0].match_count == results_upper[0].match_count == 2


class TestSearchServiceToolMessages:
    """Test cases for including tool messages in search."""

    def test_search_tool_use_messages(self, mock_history_storage, mock_session_storage):
        """Verify tool_use messages are included in search results."""
        temp_dir, create_history = mock_history_storage
        messages = [
            {"role": "user", "content": "Read the main.py file"},
            {"role": "assistant", "content": "I'll read the main.py file"},
            {"role": "tool_use", "content": "Reading file: main.py", "tool_name": "Read", "tool_input": {"file_path": "main.py"}},
        ]
        create_history("session-3", messages)

        service = SessionSearchService()

        with patch("api.services.search_service.get_user_session_storage") as mock_get_sess:
            mock_get_sess.return_value = mock_session_storage

            with patch("api.services.search_service.get_user_history_storage") as mock_get_hist:
                def mock_history_file(session_id):
                    file_path = temp_dir / "history" / f"{session_id}.jsonl"
                    if not file_path.exists():
                        mock_file = Mock()
                        mock_file.exists.return_value = False
                        return mock_file
                    return file_path

                mock_storage = Mock()
                mock_storage._get_history_file.side_effect = mock_history_file
                mock_get_hist.return_value = mock_storage

                results = service.search_sessions("testuser", "Read")

                assert len(results) == 1
                assert results[0].session_id == "session-3"
                assert results[0].relevance_score > 0

    def test_search_tool_result_messages(self, mock_history_storage, mock_session_storage):
        """Verify tool_result messages are included in search results."""
        temp_dir, create_history = mock_history_storage
        messages = [
            {"role": "user", "content": "Show me a hello world function"},
            {"role": "tool_use", "content": "Writing function", "tool_name": "Write", "tool_input": {"file_path": "hello.py"}},
            {"role": "tool_result", "content": "def hello_world():\n    print('Hello, World!')", "tool_use_id": "tool-123"},
        ]
        create_history("session-3", messages)

        service = SessionSearchService()

        with patch("api.services.search_service.get_user_session_storage") as mock_get_sess:
            mock_get_sess.return_value = mock_session_storage

            with patch("api.services.search_service.get_user_history_storage") as mock_get_hist:
                def mock_history_file(session_id):
                    file_path = temp_dir / "history" / f"{session_id}.jsonl"
                    if not file_path.exists():
                        mock_file = Mock()
                        mock_file.exists.return_value = False
                        return mock_file
                    return file_path

                mock_storage = Mock()
                mock_storage._get_history_file.side_effect = mock_history_file
                mock_get_hist.return_value = mock_storage

                results = service.search_sessions("testuser", "hello_world")

                assert len(results) == 1
                assert "hello_world" in results[0].snippet.lower()


class TestSearchServiceRelevanceScoring:
    """Test cases for relevance scoring and sorting."""

    def test_search_relevance_scoring(self, mock_history_storage, mock_session_storage):
        """Verify results are sorted by relevance score."""
        temp_dir, create_history = mock_history_storage

        messages1 = [{"role": "user", "content": "python is great"}]
        create_history("session-1", messages1)

        messages2 = [{"role": "user", "content": "python"}, {"role": "assistant", "content": "python"}]
        create_history("session-2", messages2)

        service = SessionSearchService()

        with patch("api.services.search_service.get_user_session_storage") as mock_get_sess:
            mock_get_sess.return_value = mock_session_storage

            with patch("api.services.search_service.get_user_history_storage") as mock_get_hist:
                def mock_history_file(session_id):
                    return temp_dir / "history" / f"{session_id}.jsonl"

                mock_storage = Mock()
                mock_storage._get_history_file.side_effect = mock_history_file
                mock_get_hist.return_value = mock_storage

                results = service.search_sessions("testuser", "python")

                assert len(results) == 2
                assert results[0].relevance_score >= results[1].relevance_score


class TestSearchResultDataclass:
    """Test cases for SearchResult dataclass."""

    def test_search_result_sorting(self):
        """Verify SearchResult objects sort correctly by relevance."""
        result1 = SearchResult(session_id="session-1", name="Session One", first_message="First",
                               created_at="2025-01-01T00:00:00", turn_count=1, agent_id="agent-1",
                               snippet="Snippet one", relevance_score=0.5, match_count=1)
        result2 = SearchResult(session_id="session-2", name="Session Two", first_message="First",
                               created_at="2025-01-01T00:00:00", turn_count=1, agent_id="agent-1",
                               snippet="Snippet two", relevance_score=0.9, match_count=2)
        result3 = SearchResult(session_id="session-3", name="Session Three", first_message="First",
                               created_at="2025-01-01T00:00:00", turn_count=1, agent_id="agent-1",
                               snippet="Snippet three", relevance_score=0.7, match_count=3)

        results = [result1, result2, result3]
        results.sort()

        assert results[0].session_id == "session-2"
        assert results[1].session_id == "session-3"
        assert results[2].session_id == "session-1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
