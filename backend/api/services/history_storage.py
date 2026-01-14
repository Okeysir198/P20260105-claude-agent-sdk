"""Conversation history storage service.

Stores conversation history in JSONL files for persistence and retrieval.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any


class HistoryStorage:
    """Service for storing and retrieving conversation history."""

    def __init__(self, data_dir: Path | None = None):
        """Initialize history storage.

        Args:
            data_dir: Directory to store history files. Defaults to data/history/
        """
        if data_dir is None:
            data_dir = Path(__file__).parent.parent.parent / "data" / "history"
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _get_session_file(self, session_id: str) -> Path:
        """Get the path to a session's history file."""
        return self.data_dir / f"{session_id}.jsonl"

    def append_message(
        self,
        session_id: str,
        role: str,
        content: str,
        tool_use: list[dict[str, Any]] | None = None,
        tool_results: list[dict[str, Any]] | None = None,
        message_id: str | None = None
    ) -> None:
        """Append a message to the session history.

        Args:
            session_id: Session ID
            role: Message role ('user' or 'assistant')
            content: Message content
            tool_use: Optional list of tool use data
            tool_results: Optional list of tool result data
            message_id: Optional message ID
        """
        # Ensure data directory exists (in case it was deleted)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        session_file = self._get_session_file(session_id)

        message = {
            "id": message_id or f"{role}-{datetime.utcnow().isoformat()}",
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        if tool_use:
            message["tool_use"] = tool_use
        if tool_results:
            message["tool_results"] = tool_results

        with open(session_file, "a") as f:
            f.write(json.dumps(message) + "\n")

    def get_history(self, session_id: str) -> list[dict[str, Any]]:
        """Get all messages for a session.

        Args:
            session_id: Session ID

        Returns:
            List of message dictionaries
        """
        session_file = self._get_session_file(session_id)

        if not session_file.exists():
            return []

        messages = []
        with open(session_file, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        messages.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

        return messages

    def has_history(self, session_id: str) -> bool:
        """Check if a session has history stored.

        Args:
            session_id: Session ID

        Returns:
            True if history file exists
        """
        return self._get_session_file(session_id).exists()

    def delete_history(self, session_id: str) -> bool:
        """Delete history for a session.

        Args:
            session_id: Session ID

        Returns:
            True if deleted, False if not found
        """
        session_file = self._get_session_file(session_id)
        if session_file.exists():
            session_file.unlink()
            return True
        return False


# Global instance
_history_storage: HistoryStorage | None = None


def get_history_storage() -> HistoryStorage:
    """Get the global history storage instance."""
    global _history_storage
    if _history_storage is None:
        _history_storage = HistoryStorage()
    return _history_storage
