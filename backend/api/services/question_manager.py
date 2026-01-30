"""Question manager service for AskUserQuestion tool callbacks.

Manages pending questions that require user input during tool execution.
Supports async waiting with timeout for user answers.
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PendingQuestion:
    """Represents a pending question waiting for user answer.

    Attributes:
        question_id: Unique identifier for the question.
        questions: List of question objects from the tool input.
        answer_event: Async event signaling when answer is received.
        answers: Dict mapping question IDs to user answers.
        created_at: Timestamp when the question was created.
    """
    question_id: str
    questions: list[dict[str, Any]]
    answer_event: asyncio.Event = field(default_factory=asyncio.Event)
    answers: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)


class QuestionManager:
    """Manages AskUserQuestion tool callbacks for WebSocket sessions.

    Provides a mechanism for the SDK's can_use_tool callback to wait for
    user input when the AskUserQuestion tool is invoked. Questions are
    sent to the client, and the manager blocks until an answer is received
    or timeout occurs.

    Thread-safe via asyncio locks.

    Attributes:
        _pending_questions: Map of question_id to PendingQuestion.
        _lock: Async lock for thread-safe operations.
        default_timeout: Default timeout in seconds for waiting on answers.
    """

    def __init__(self, default_timeout: float = 60.0):
        """Initialize the question manager.

        Args:
            default_timeout: Default timeout in seconds for waiting on answers.
        """
        self._pending_questions: dict[str, PendingQuestion] = {}
        self._lock = asyncio.Lock()
        self.default_timeout = default_timeout

    def create_question(
        self,
        question_id: str,
        questions: list[dict[str, Any]]
    ) -> PendingQuestion:
        """Create a pending question entry.

        Args:
            question_id: Unique identifier for the question.
            questions: List of question objects from tool input.

        Returns:
            The created PendingQuestion instance.
        """
        pending = PendingQuestion(
            question_id=question_id,
            questions=questions
        )
        self._pending_questions[question_id] = pending
        logger.info(f"Created pending question: {question_id} with {len(questions)} questions")
        return pending

    async def wait_for_answer(
        self,
        question_id: str,
        timeout: float | None = None
    ) -> dict[str, Any]:
        """Wait for user to submit an answer to a pending question.

        Blocks until the answer is received or timeout occurs.

        Args:
            question_id: The question ID to wait for.
            timeout: Timeout in seconds. Uses default_timeout if None.

        Returns:
            Dict mapping question IDs to user answers.

        Raises:
            asyncio.TimeoutError: If timeout expires before answer is received.
            KeyError: If question_id is not found.
        """
        if question_id not in self._pending_questions:
            raise KeyError(f"Question not found: {question_id}")

        pending = self._pending_questions[question_id]
        effective_timeout = timeout if timeout is not None else self.default_timeout

        try:
            await asyncio.wait_for(
                pending.answer_event.wait(),
                timeout=effective_timeout
            )
            logger.info(f"Received answer for question: {question_id}")
            return pending.answers
        finally:
            # Clean up the pending question
            self._cleanup_question(question_id)

    async def submit_answer(
        self,
        question_id: str,
        answers: dict[str, Any]
    ) -> bool:
        """Submit user answers for a pending question.

        Thread-safe method that uses async lock to prevent race conditions.
        Note: The question is not immediately cleaned up here. Cleanup happens
        in wait_for_answer's finally block or via cleanup_orphaned_questions.

        Args:
            question_id: The question ID to answer.
            answers: Dict mapping question IDs to user answers.

        Returns:
            True if the answer was submitted successfully, False if question not found.
        """
        async with self._lock:
            if question_id not in self._pending_questions:
                logger.warning(f"Answer submitted for unknown question: {question_id}")
                return False

            pending = self._pending_questions[question_id]
            pending.answers = answers
            pending.answer_event.set()
            logger.info(f"Submitted answer for question: {question_id}")
            return True

    def cancel_question(self, question_id: str) -> bool:
        """Cancel a pending question without submitting an answer.

        Args:
            question_id: The question ID to cancel.

        Returns:
            True if cancelled successfully, False if not found.
        """
        if question_id not in self._pending_questions:
            return False

        pending = self._pending_questions[question_id]
        # Set empty answers and trigger the event to unblock waiting
        pending.answers = {}
        pending.answer_event.set()
        logger.info(f"Cancelled question: {question_id}")
        return True

    def _cleanup_question(self, question_id: str) -> None:
        """Remove a question from pending questions.

        Args:
            question_id: The question ID to remove.
        """
        if question_id in self._pending_questions:
            del self._pending_questions[question_id]
            logger.debug(f"Cleaned up question: {question_id}")

    def get_pending_count(self) -> int:
        """Get the number of pending questions.

        Returns:
            Count of pending questions.
        """
        return len(self._pending_questions)

    def has_pending_question(self, question_id: str) -> bool:
        """Check if a question is pending.

        Args:
            question_id: The question ID to check.

        Returns:
            True if the question is pending.
        """
        return question_id in self._pending_questions

    async def cleanup_orphaned_questions(self, max_age_seconds: float = 300) -> int:
        """Remove orphaned questions older than max_age_seconds.

        Orphaned questions are those that have been pending for too long,
        likely due to client disconnection or timeout issues. This prevents
        memory leaks from accumulating stale questions.

        Args:
            max_age_seconds: Maximum age in seconds before a question is considered orphaned.
                           Default is 300 seconds (5 minutes).

        Returns:
            Number of questions cleaned up.
        """
        async with self._lock:
            current_time = time.time()
            orphaned_ids = [
                question_id
                for question_id, pending in self._pending_questions.items()
                if (current_time - pending.created_at) > max_age_seconds
            ]

            for question_id in orphaned_ids:
                # Cancel the question to unblock any waiters
                pending = self._pending_questions[question_id]
                pending.answers = {}
                pending.answer_event.set()
                # Remove from pending questions
                del self._pending_questions[question_id]
                logger.info(f"Cleaned up orphaned question: {question_id} (age: {current_time - pending.created_at:.1f}s)")

            if orphaned_ids:
                logger.info(f"Cleaned up {len(orphaned_ids)} orphaned questions")

            return len(orphaned_ids)


# Global singleton instance
_question_manager: QuestionManager | None = None


def get_question_manager() -> QuestionManager:
    """Get the global QuestionManager singleton instance.

    Returns:
        The global QuestionManager instance.

    Example:
        ```python
        from api.services.question_manager import get_question_manager

        manager = get_question_manager()
        manager.create_question(question_id, questions)
        answers = await manager.wait_for_answer(question_id)
        ```
    """
    global _question_manager
    if _question_manager is None:
        _question_manager = QuestionManager()
    return _question_manager
