"""Service for searching session history and metadata."""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

from agent.core.storage import get_user_session_storage, get_user_history_storage


@dataclass
class SearchResult:
    """Represents a search result with relevance score."""

    session_id: str
    name: str | None
    first_message: str | None
    created_at: str
    turn_count: int
    agent_id: str | None
    snippet: str
    relevance_score: float
    match_count: int = 0

    def __lt__(self, other):
        """Sort by relevance score (highest first)."""
        return self.relevance_score > other.relevance_score

    def __lt__(self, other):
        """Sort by relevance score (highest first)."""
        return self.relevance_score > other.relevance_score


@dataclass
class SearchOptions:
    """Options for search behavior."""

    max_results: int = 50
    snippet_length: int = 200
    context_chars: int = 100
    min_score: float = 0.1


class SessionSearchService:
    """Service for searching session history and metadata."""

    def __init__(self, options: SearchOptions | None = None):
        """Initialize search service with options.

        Args:
            options: Search configuration options
        """
        self.options = options or SearchOptions()

    def search_sessions(
        self,
        username: str,
        query: str,
    ) -> list[SearchResult]:
        """Search all sessions for a user.

        Args:
            username: Username to search sessions for
            query: Search query string

        Returns:
            List of search results sorted by relevance
        """
        if not query or not query.strip():
            return []

        search_query = query.strip().lower()
        results: list[SearchResult] = []

        # Get all sessions for user
        session_storage = get_user_session_storage(username)
        sessions = session_storage.load_sessions()

        for session in sessions:
            result = self._search_session_file(
                username=username,
                session_id=session.session_id,
                session=session,
                query=search_query,
            )

            # Filter by minimum relevance score
            if result and result.relevance_score >= self.options.min_score:
                results.append(result)

        # Sort by relevance (highest first)
        results.sort()

        # Return top N results
        return results[: self.options.max_results]

    def _search_session_file(
        self,
        username: str,
        session_id: str,
        session,
        query: str,
    ) -> SearchResult | None:
        """Search a single session history file.

        Reads file line-by-line to avoid loading entire file into memory.

        Args:
            username: Username
            session_id: Session ID
            session: Session object with metadata
            query: Normalized (lowercase) search query

        Returns:
            SearchResult if matches found, None otherwise
        """
        history_storage = get_user_history_storage(username)
        history_path = history_storage._get_history_file(session_id)

        if not history_path.exists():
            return None

        match_count = 0
        first_match_pos = 0
        total_lines = 0
        matched_lines: list[tuple[int, str]] = []  # (line_num, content)

        try:
            with open(history_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f):
                    total_lines += 1
                    if not line.strip():
                        continue

                    try:
                        message = json.loads(line)

                        # Extract searchable content based on message type
                        role = message.get("role")
                        content = message.get("content", "")
                        searchable_content = content

                        # For tool messages, include tool name and content
                        if role == "tool_use":
                            tool_name = message.get("tool_name", "")
                            searchable_content = f"{tool_name} {content}".strip()
                        elif role == "tool_result":
                            # For tool results, search the output content
                            searchable_content = content

                        # Search in all message types (user, assistant, tool_use, tool_result)
                        if query in searchable_content.lower():
                            match_count += 1
                            if first_match_pos == 0:
                                first_match_pos = line_num

                            # Store matched line for snippet generation
                            matched_lines.append((line_num, searchable_content))

                    except json.JSONDecodeError:
                        # Skip malformed lines
                        continue

        except (IOError, OSError) as e:
            # Log error but continue with other sessions
            logger.error(f"Error reading history file {history_path}: {e}")
            return None

        if match_count == 0:
            return None

        # Calculate relevance score
        # Score based on: match density + position boost
        match_density = match_count / max(total_lines, 1)
        position_boost = 1.0 - (first_match_pos / max(total_lines, 1))
        relevance_score = (match_density * 0.7) + (position_boost * 0.3)

        # Generate snippet from matched content
        snippet = self._generate_snippet(matched_lines, query)

        return SearchResult(
            session_id=session_id,
            name=session.name,
            first_message=session.first_message,
            created_at=session.created_at,
            turn_count=match_count,
            agent_id=session.agent_id,
            snippet=snippet,
            relevance_score=relevance_score,
            match_count=match_count,
        )

    def _generate_snippet(
        self,
        matched_lines: list[tuple[int, str]],
        query: str,
    ) -> str:
        """Generate a snippet with context around matches.

        Args:
            matched_lines: List of (line_num, content) for matches
            query: Normalized search query

        Returns:
            Snippet string with highlighted context
        """
        if not matched_lines:
            return ""

        # Sort by line number to get first match
        matched_lines.sort(key=lambda x: x[0])

        # Use content from first match
        _, content = matched_lines[0]
        content_lower = content.lower()

        # Find query position in content
        query_pos = content_lower.find(query)
        if query_pos == -1:
            # Case mismatch fallback - use first match position
            return content[: self.options.snippet_length]

        # Calculate snippet boundaries with context
        start = max(0, query_pos - self.options.context_chars)
        end = min(
            len(content),
            query_pos + len(query) + self.options.context_chars,
        )

        snippet = content[start:end]

        # Add ellipsis if truncated
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."

        return snippet[: self.options.snippet_length]
