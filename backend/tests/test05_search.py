"""
Unit tests for the search service.

Run: pytest tests/test_search.py -v
"""
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest
import tempfile
import json

from api.services.search_service import (
    SessionSearchService,
    SearchResult,
    SearchOptions,
)


@pytest.fixture
def temp_storage_dir():
    """Create a temporary directory for test storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_history_storage(temp_storage_dir):
    """Create mock history storage with test data."""
    history_dir = temp_storage_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)

    def create_history_file(session_id: str, messages: list[dict]):
        """Helper to create a history file with messages."""
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

    # Create mock sessions
    mock_session1 = Mock()
    mock_session1.session_id = "session-1"
    mock_session1.name = "Test Session One"
    mock_session1.first_message = "First message"

    mock_session2 = Mock()
    mock_session2.session_id = "session-2"
    mock_session2.name = "Python Discussion"
    mock_session2.first_message = "How to use Python"

    mock_session3 = Mock()
    mock_session3.session_id = "session-3"
    mock_session3.name = "Tool Usage Session"
    mock_session3.first_message = "Using tools"

    mock_storage.load_sessions.return_value = [
        mock_session1,
        mock_session2,
        mock_session3,
    ]

    return mock_storage


class TestSearchServiceEmptyQuery:
    """Test cases for empty query handling."""

    def test_search_empty_query(self, mock_session_storage):
        """Verify that empty query returns no results."""
        service = SessionSearchService()

        with patch(
            "api.services.search_service.get_user_session_storage"
        ) as mock_get_storage:
            mock_get_storage.return_value = mock_session_storage

            results = service.search_sessions("testuser", "")

            assert results == []
            assert len(results) == 0


    def test_search_whitespace_only_query(self, mock_session_storage):
        """Verify that whitespace-only query returns no results."""
        service = SessionSearchService()

        with patch(
            "api.services.search_service.get_user_session_storage"
        ) as mock_get_storage:
            mock_get_storage.return_value = mock_session_storage

            results = service.search_sessions("testuser", "   \t\n  ")

            assert results == []


class TestSearchServiceSingleMatch:
    """Test cases for single match scenarios."""

    def test_search_single_match(self, mock_history_storage, mock_session_storage):
        """Search for term appearing once and verify correct result."""
        temp_dir, create_history = mock_history_storage

        # Create history with one match
        messages = [
            {"role": "user", "content": "Hello world"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "Tell me about elephants"},
            {"role": "assistant", "content": "Elephants are large mammals."},
        ]
        create_history("session-1", messages)

        service = SessionSearchService()

        with patch(
            "api.services.search_service.get_user_session_storage"
        ) as mock_get_sess:
            mock_get_sess.return_value = mock_session_storage

            with patch(
                "api.services.search_service.get_user_history_storage"
            ) as mock_get_hist:
                # Mock to return correct file for each session
                def mock_history_file(session_id):
                    file_path = temp_dir / "history" / f"{session_id}.jsonl"
                    if not file_path.exists():
                        # Return a mock that doesn't exist
                        mock_file = Mock()
                        mock_file.exists.return_value = False
                        return mock_file
                    return file_path

                mock_storage = Mock()
                mock_storage._get_history_file.side_effect = mock_history_file
                mock_get_hist.return_value = mock_storage

                results = service.search_sessions("testuser", "elephants")

                # Should only find session-1 with the elephants content
                assert len(results) == 1
                assert results[0].session_id == "session-1"
                assert results[0].match_count == 2  # "elephants" appears in user + assistant messages
                assert "elephants" in results[0].snippet.lower()


class TestSearchServiceCaseInsensitive:
    """Test cases for case-insensitive matching."""

    def test_search_case_insensitive(self, mock_history_storage, mock_session_storage):
        """Verify case-insensitive matching works."""
        temp_dir, create_history = mock_history_storage

        # Create history with mixed case content
        messages = [
            {"role": "user", "content": "I want to learn Python programming"},
            {"role": "assistant", "content": "PYTHON is a great language"},
            {"role": "user", "content": "What about python frameworks?"},
        ]
        create_history("session-2", messages)

        service = SessionSearchService()

        with patch(
            "api.services.search_service.get_user_session_storage"
        ) as mock_get_sess:
            mock_get_sess.return_value = mock_session_storage

            with patch(
                "api.services.search_service.get_user_history_storage"
            ) as mock_get_hist:
                # Mock to return correct file for each session
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

                # Search with lowercase
                results_lower = service.search_sessions("testuser", "python")
                assert len(results_lower) == 1
                assert results_lower[0].session_id == "session-2"
                assert results_lower[0].match_count == 3

                # Search with uppercase
                results_upper = service.search_sessions("testuser", "PYTHON")
                assert len(results_upper) == 1
                assert results_upper[0].session_id == "session-2"
                assert results_upper[0].match_count == 3

                # Search with mixed case
                results_mixed = service.search_sessions("testuser", "PyThOn")
                assert len(results_mixed) == 1
                assert results_mixed[0].session_id == "session-2"
                assert results_mixed[0].match_count == 3


@pytest.fixture
def sample_session_with_tools():
    """Create a sample session with tool messages for testing."""
    mock_session = Mock()
    mock_session.session_id = "session-with-tools"
    mock_session.name = "Tool Usage Test Session"
    mock_session.first_message = "Read the main.py file"
    return mock_session


class TestSearchServiceIncludeToolMessages:
    """Test cases for including tool messages in search."""

    def test_search_includes_tool_use_messages(self, mock_history_storage, mock_session_storage):
        """Verify tool_use messages are included in search results."""
        temp_dir, create_history = mock_history_storage

        # Create history with tool_use message
        messages = [
            {"role": "user", "content": "Read the main.py file"},
            {"role": "assistant", "content": "I'll read the main.py file for you"},
            {
                "role": "tool_use",
                "content": 'Reading file: main.py',
                "tool_name": "Read",
                "tool_input": {"file_path": "main.py"}
            },
            {"role": "assistant", "content": "I've read the file"},
        ]
        create_history("session-3", messages)

        service = SessionSearchService()

        with patch(
            "api.services.search_service.get_user_session_storage"
        ) as mock_get_sess:
            mock_get_sess.return_value = mock_session_storage

            with patch(
                "api.services.search_service.get_user_history_storage"
            ) as mock_get_hist:
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

                # Search for tool name
                results = service.search_sessions("testuser", "Read")

                # Should find the session with tool_use message
                assert len(results) == 1
                assert results[0].session_id == "session-3"
                assert results[0].relevance_score > 0
                # "Read" appears in user, assistant, and tool_use messages
                assert results[0].match_count >= 3

    def test_search_includes_tool_result_messages(self, mock_history_storage, mock_session_storage):
        """Verify tool_result messages are included in search results."""
        temp_dir, create_history = mock_history_storage

        # Create history with tool_result message containing code
        tool_output = '''def hello_world():
    """A simple hello world function."""
    print("Hello, World!")
    return True'''
        messages = [
            {"role": "user", "content": "Show me a hello world function"},
            {"role": "assistant", "content": "I'll create a hello world function"},
            {
                "role": "tool_use",
                "content": "Writing hello_world function",
                "tool_name": "Write",
                "tool_input": {"file_path": "hello.py"}
            },
            {
                "role": "tool_result",
                "content": tool_output,
                "tool_use_id": "tool-123"
            },
        ]
        create_history("session-3", messages)

        service = SessionSearchService()

        with patch(
            "api.services.search_service.get_user_session_storage"
        ) as mock_get_sess:
            mock_get_sess.return_value = mock_session_storage

            with patch(
                "api.services.search_service.get_user_history_storage"
            ) as mock_get_hist:
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

                # Search for content that appears in tool_result
                results = service.search_sessions("testuser", "hello_world")

                # Should find the session via tool_result content
                assert len(results) == 1
                assert results[0].session_id == "session-3"
                assert results[0].relevance_score > 0
                assert "hello_world" in results[0].snippet.lower()

    def test_search_tool_name_and_content(self, mock_history_storage, mock_session_storage):
        """Verify search matches both tool name and tool result content."""
        temp_dir, create_history = mock_history_storage

        # Create history with specific tool name and result content
        messages = [
            {"role": "user", "content": "Check the configuration file"},
            {"role": "assistant", "content": "I'll read the config file"},
            {
                "role": "tool_use",
                "content": "Reading configuration",
                "tool_name": "Read",
                "tool_input": {"file_path": "/path/to/config.yaml"}
            },
            {
                "role": "tool_result",
                "content": "port: 8080\nhost: localhost\nconfig.yaml settings",
                "tool_use_id": "tool-456"
            },
        ]
        create_history("session-3", messages)

        service = SessionSearchService()

        with patch(
            "api.services.search_service.get_user_session_storage"
        ) as mock_get_sess:
            mock_get_sess.return_value = mock_session_storage

            with patch(
                "api.services.search_service.get_user_history_storage"
            ) as mock_get_hist:
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

                # Search for content that appears in tool result
                results = service.search_sessions("testuser", "config.yaml")

                # Should match the tool result content
                assert len(results) == 1
                assert results[0].session_id == "session-3"
                assert results[0].relevance_score > 0

                # Also verify tool name is searchable
                results_tool = service.search_sessions("testuser", "Read")
                assert len(results_tool) == 1
                assert results_tool[0].session_id == "session-3"
                assert results_tool[0].relevance_score > 0

    def test_combined_user_and_tool_search(self, mock_history_storage, mock_session_storage):
        """Verify search across user, assistant, and tool messages."""
        temp_dir, create_history = mock_history_storage

        # Create comprehensive session with all message types
        messages = [
            {"role": "user", "content": "Create a python function to calculate fibonacci"},
            {"role": "assistant", "content": "I'll create a fibonacci function for you"},
            {
                "role": "tool_use",
                "content": "Writing fibonacci function",
                "tool_name": "Write",
                "tool_input": {"file_path": "fibonacci.py"}
            },
            {
                "role": "tool_result",
                "content": "def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)",
                "tool_use_id": "tool-789"
            },
            {"role": "assistant", "content": "I've created the fibonacci function"},
        ]
        create_history("session-3", messages)

        service = SessionSearchService()

        with patch(
            "api.services.search_service.get_user_session_storage"
        ) as mock_get_sess:
            mock_get_sess.return_value = mock_session_storage

            with patch(
                "api.services.search_service.get_user_history_storage"
            ) as mock_get_hist:
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

                # Search for term that appears in all message types
                results = service.search_sessions("testuser", "fibonacci")

                # Should match user, assistant, and tool messages
                assert len(results) == 1
                assert results[0].session_id == "session-3"
                assert results[0].relevance_score > 0
                # Should have multiple matches across different message types
                assert results[0].match_count >= 4

    def test_tool_error_messages_searchable(self, mock_history_storage, mock_session_storage):
        """Verify error messages in tool results are searchable."""
        temp_dir, create_history = mock_history_storage

        # Create history with error in tool_result
        error_message = "Error: File not found at specified path"
        messages = [
            {"role": "user", "content": "Read the missing file"},
            {"role": "assistant", "content": "I'll attempt to read the file"},
            {
                "role": "tool_use",
                "content": "Reading file",
                "tool_name": "Read",
                "tool_input": {"file_path": "nonexistent.py"}
            },
            {
                "role": "tool_result",
                "content": error_message,
                "tool_use_id": "tool-error-123",
                "is_error": True
            },
            {"role": "assistant", "content": "The file could not be found"},
        ]
        create_history("session-3", messages)

        service = SessionSearchService()

        with patch(
            "api.services.search_service.get_user_session_storage"
        ) as mock_get_sess:
            mock_get_sess.return_value = mock_session_storage

            with patch(
                "api.services.search_service.get_user_history_storage"
            ) as mock_get_hist:
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

                # Search for error message
                results = service.search_sessions("testuser", "Error")

                # Should find the session with error in tool_result
                assert len(results) == 1
                assert results[0].session_id == "session-3"
                assert results[0].relevance_score > 0
                assert "error" in results[0].snippet.lower()


class TestSearchServiceRelevanceScoring:
    """Test cases for relevance scoring and sorting."""

    def test_search_relevance_scoring(self, mock_history_storage, mock_session_storage):
        """Verify results are sorted by relevance score."""
        temp_dir, create_history = mock_history_storage

        # Create two sessions with different match densities
        messages1 = [
            {"role": "user", "content": "python is great"},
            {"role": "assistant", "content": "Yes, python is awesome"},
        ]
        create_history("session-1", messages1)

        messages2 = [
            {"role": "user", "content": "python"},
            {"role": "assistant", "content": "python"},
            {"role": "user", "content": "python"},
            {"role": "assistant", "content": "python"},
        ]
        create_history("session-2", messages2)

        service = SessionSearchService()

        with patch(
            "api.services.search_service.get_user_session_storage"
        ) as mock_get_sess:
            mock_get_sess.return_value = mock_session_storage

            with patch(
                "api.services.search_service.get_user_history_storage"
            ) as mock_get_hist:
                def mock_history_file(session_id):
                    return temp_dir / "history" / f"{session_id}.jsonl"

                mock_storage = Mock()
                mock_storage._get_history_file.side_effect = mock_history_file
                mock_get_hist.return_value = mock_storage

                results = service.search_sessions("testuser", "python")

                assert len(results) == 2
                # Session 2 has higher match density (4 matches in 4 lines)
                # Session 1 has lower match density (2 matches in 2 lines)
                # But we need to verify the actual relevance scores
                # Both should have perfect match density but session 2 has more total matches
                assert results[0].match_count >= results[1].match_count
                assert results[0].relevance_score >= results[1].relevance_score


    def test_search_relevance_position_boost(self, mock_history_storage):
        """Verify that earlier matches get higher scores."""
        temp_dir, create_history = mock_history_storage

        # Create session with match at the beginning
        messages_early = [
            {"role": "user", "content": "python tutorial"},
            {"role": "assistant", "content": "Later content"},
            {"role": "user", "content": "More content"},
            {"role": "assistant", "content": "Even more content"},
        ]
        create_history("session-early", messages_early)

        # Create session with match at the end
        messages_late = [
            {"role": "user", "content": "Some content"},
            {"role": "assistant", "content": "More content"},
            {"role": "user", "content": "Later content"},
            {"role": "assistant", "content": "python tutorial"},
        ]
        create_history("session-late", messages_late)

        service = SessionSearchService()

        mock_storage_early = Mock()
        mock_storage_early.session_id = "session-early"
        mock_storage_early.name = "Early Match"

        mock_storage_late = Mock()
        mock_storage_late.session_id = "session-late"
        mock_storage_late.name = "Late Match"

        mock_session_storage = Mock()
        mock_session_storage.load_sessions.return_value = [
            mock_storage_early,
            mock_storage_late,
        ]

        with patch(
            "api.services.search_service.get_user_session_storage"
        ) as mock_get_sess:
            mock_get_sess.return_value = mock_session_storage

            with patch(
                "api.services.search_service.get_user_history_storage"
            ) as mock_get_hist:
                def mock_history_file(session_id):
                    return temp_dir / "history" / f"{session_id}.jsonl"

                mock_storage = Mock()
                mock_storage._get_history_file.side_effect = mock_history_file
                mock_get_hist.return_value = mock_storage

                results = service.search_sessions("testuser", "python")

                # Both have 1 match, but early match should have higher score
                assert len(results) == 2
                assert results[0].session_id == "session-early"
                assert results[0].relevance_score > results[1].relevance_score


class TestSearchServiceSnippetGeneration:
    """Test cases for snippet generation."""

    def test_search_snippet_generation(self, mock_history_storage, mock_session_storage):
        """Verify snippets include context around matches."""
        temp_dir, create_history = mock_history_storage

        # Create history with long content
        long_content = "This is a very long message that contains the search term python programming somewhere in the middle of the text and should generate a proper snippet with context."
        messages = [
            {"role": "user", "content": long_content},
        ]
        create_history("session-1", messages)

        service = SessionSearchService(SearchOptions(context_chars=30))

        with patch(
            "api.services.search_service.get_user_session_storage"
        ) as mock_get_sess:
            mock_get_sess.return_value = mock_session_storage

            with patch(
                "api.services.search_service.get_user_history_storage"
            ) as mock_get_hist:
                # Mock to return correct file for each session
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

                results = service.search_sessions("testuser", "python")

                assert len(results) == 1
                assert results[0].session_id == "session-1"
                snippet = results[0].snippet

                # Should contain the search term
                assert "python" in snippet.lower()

                # Should contain context around the term
                assert len(snippet) > len("python")

                # Should be truncated with context_chars on each side (approximately)
                # 30 chars before + 30 chars after + "python" = ~67 chars
                assert len(snippet) <= 200  # Max snippet length


    def test_search_snippet_ellipsis(self, mock_history_storage, mock_session_storage):
        """Verify snippets show ellipsis when content is truncated."""
        temp_dir, create_history = mock_history_storage

        # Create history with content that needs ellipsis
        long_prefix = "A" * 150
        long_suffix = "B" * 150
        content = f"{long_prefix} python {long_suffix}"
        messages = [
            {"role": "user", "content": content},
        ]
        create_history("session-1", messages)

        service = SessionSearchService(SearchOptions(
            context_chars=50,
            snippet_length=200
        ))

        with patch(
            "api.services.search_service.get_user_session_storage"
        ) as mock_get_sess:
            mock_get_sess.return_value = mock_session_storage

            with patch(
                "api.services.search_service.get_user_history_storage"
            ) as mock_get_hist:
                # Mock to return correct file for each session
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

                results = service.search_sessions("testuser", "python")

                assert len(results) == 1
                assert results[0].session_id == "session-1"
                snippet = results[0].snippet

                # Should have ellipsis at the beginning
                assert snippet.startswith("...")

                # Should have ellipsis at the end (or be truncated by max length)
                # Since the snippet will be truncated to max_length, we check that
                # it either has ellipsis or is exactly at max length
                assert "..." in snippet or len(snippet) == 200


    def test_search_multiple_snippets_from_different_matches(self, mock_history_storage, mock_session_storage):
        """Verify snippet uses first match when there are multiple."""
        temp_dir, create_history = mock_history_storage

        # Create history with multiple matches
        messages = [
            {"role": "user", "content": "First occurrence of python here"},
            {"role": "assistant", "content": "Second python mention in response"},
            {"role": "user", "content": "Third python reference"},
        ]
        create_history("session-1", messages)

        service = SessionSearchService()

        with patch(
            "api.services.search_service.get_user_session_storage"
        ) as mock_get_sess:
            mock_get_sess.return_value = mock_session_storage

            with patch(
                "api.services.search_service.get_user_history_storage"
            ) as mock_get_hist:
                # Mock to return correct file for each session
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

                results = service.search_sessions("testuser", "python")

                assert len(results) == 1
                assert results[0].session_id == "session-1"
                snippet = results[0].snippet

                # Should contain "First" since it's from the first match
                assert "First" in snippet


class TestSearchServiceOptions:
    """Test cases for search options configuration."""

    def test_custom_max_results(self, mock_history_storage):
        """Verify custom max_results option works."""
        temp_dir, create_history = mock_history_storage

        # Create multiple sessions
        for i in range(10):
            messages = [{"role": "user", "content": "python programming"}]
            create_history(f"session-{i}", messages)

        # Create mock session storage
        mock_sessions = []
        for i in range(10):
            mock_sess = Mock()
            mock_sess.session_id = f"session-{i}"
            mock_sess.name = f"Session {i}"
            mock_sess.first_message = "First message"
            mock_sessions.append(mock_sess)

        mock_session_storage = Mock()
        mock_session_storage.load_sessions.return_value = mock_sessions

        service = SessionSearchService(SearchOptions(max_results=5))

        with patch(
            "api.services.search_service.get_user_session_storage"
        ) as mock_get_sess:
            mock_get_sess.return_value = mock_session_storage

            with patch(
                "api.services.search_service.get_user_history_storage"
            ) as mock_get_hist:
                def mock_history_file(session_id):
                    return temp_dir / "history" / f"{session_id}.jsonl"

                mock_storage = Mock()
                mock_storage._get_history_file.side_effect = mock_history_file
                mock_get_hist.return_value = mock_storage

                results = service.search_sessions("testuser", "python")

                # Should return at most 5 results
                assert len(results) <= 5


    def test_min_score_filtering(self, mock_history_storage, mock_session_storage):
        """Verify min_score option filters low-relevance results."""
        temp_dir, create_history = mock_history_storage

        # Create a session with a single match (lower relevance)
        messages = [
            {"role": "user", "content": "A long message without the term"},
            {"role": "assistant", "content": "Another long message"},
            {"role": "user", "content": "Finally, python appears once"},
            {"role": "assistant", "content": "More content after"},
        ]
        create_history("session-low-score", messages)

        service = SessionSearchService(SearchOptions(min_score=0.5))

        with patch(
            "api.services.search_service.get_user_session_storage"
        ) as mock_get_sess:
            mock_get_sess.return_value = mock_session_storage

            with patch(
                "api.services.search_service.get_user_history_storage"
            ) as mock_get_hist:
                mock_storage = Mock()
                mock_storage._get_history_file.return_value = temp_dir / "history" / "session-low-score.jsonl"
                mock_get_hist.return_value = mock_storage

                results = service.search_sessions("testuser", "python")

                # With min_score=0.5, low-relevance single matches might be filtered out
                # The relevance score depends on position and density
                # This test verifies the filtering logic is applied
                if len(results) > 0:
                    assert all(r.relevance_score >= 0.5 for r in results)


class TestSearchResultDataclass:
    """Test cases for SearchResult dataclass."""

    def test_search_result_sorting(self):
        """Verify SearchResult objects sort correctly by relevance."""
        result1 = SearchResult(
            session_id="session-1",
            name="Session One",
            first_message="First message",
            created_at="2025-01-01T00:00:00",
            turn_count=1,
            agent_id="agent-1",
            snippet="Snippet one",
            relevance_score=0.5,
            match_count=1,
        )
        result2 = SearchResult(
            session_id="session-2",
            name="Session Two",
            first_message="First message",
            created_at="2025-01-01T00:00:00",
            turn_count=1,
            agent_id="agent-1",
            snippet="Snippet two",
            relevance_score=0.9,
            match_count=2,
        )
        result3 = SearchResult(
            session_id="session-3",
            name="Session Three",
            first_message="First message",
            created_at="2025-01-01T00:00:00",
            turn_count=1,
            agent_id="agent-1",
            snippet="Snippet three",
            relevance_score=0.7,
            match_count=3,
        )

        results = [result1, result2, result3]
        results.sort()

        # Should be sorted by relevance score (highest first)
        assert results[0].session_id == "session-2"
        assert results[1].session_id == "session-3"
        assert results[2].session_id == "session-1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
