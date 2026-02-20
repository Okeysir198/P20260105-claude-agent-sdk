"""Question manager for AskUserQuestion tool callbacks.

Manages pending questions that require user input during tool execution,
with async waiting and timeout support.
"""
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PendingQuestion:
    """A pending question waiting for user answer."""
    question_id: str
    questions: list[dict[str, Any]]
    answer_event: asyncio.Event = field(default_factory=asyncio.Event)
    answers: dict[str, Any] = field(default_factory=dict)


class QuestionManager:
    """Manages AskUserQuestion tool callbacks for WebSocket sessions.

    Questions are sent to the client, and the manager blocks until an
    answer is received or timeout occurs.
    """

    def __init__(self, default_timeout: float = 60.0):
        self._pending_questions: dict[str, PendingQuestion] = {}
        self._lock = asyncio.Lock()
        self.default_timeout = default_timeout

    def create_question(
        self,
        question_id: str,
        questions: list[dict[str, Any]],
    ) -> PendingQuestion:
        """Create and register a pending question entry."""
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
        timeout: float | None = None,
    ) -> dict[str, Any]:
        """Block until the user submits an answer or timeout expires."""
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

    def submit_answer(
        self,
        question_id: str,
        answers: dict[str, Any],
    ) -> bool:
        """Submit user answers for a pending question. Returns True on success."""
        if question_id not in self._pending_questions:
            logger.warning(f"Answer submitted for unknown question: {question_id}")
            return False

        pending = self._pending_questions[question_id]
        pending.answers = answers
        pending.answer_event.set()
        logger.info(f"Submitted answer for question: {question_id}")
        return True

    def cancel_question(self, question_id: str) -> bool:
        """Cancel a pending question with empty answers. Returns True if found."""
        if question_id not in self._pending_questions:
            return False

        pending = self._pending_questions[question_id]
        # Set empty answers and trigger the event to unblock waiting
        pending.answers = {}
        pending.answer_event.set()
        logger.info(f"Cancelled question: {question_id}")
        return True

    def _cleanup_question(self, question_id: str) -> None:
        """Remove a question from the pending map."""
        if question_id in self._pending_questions:
            del self._pending_questions[question_id]
            logger.debug(f"Cleaned up question: {question_id}")

    def get_pending_count(self) -> int:
        """Get the number of pending questions."""
        return len(self._pending_questions)

    def has_pending_question(self, question_id: str) -> bool:
        """Check if a question is pending."""
        return question_id in self._pending_questions


_question_manager: QuestionManager | None = None


def get_question_manager() -> QuestionManager:
    """Get the global QuestionManager singleton instance."""
    global _question_manager
    if _question_manager is None:
        _question_manager = QuestionManager()
    return _question_manager
