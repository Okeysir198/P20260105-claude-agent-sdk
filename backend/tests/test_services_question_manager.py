"""Tests for QuestionManager service."""
import asyncio
import time

import pytest

from api.services.question_manager import PendingQuestion, QuestionManager, get_question_manager


class TestPendingQuestion:
    """Test cases for PendingQuestion dataclass."""

    def test_create_pending_question(self):
        """Test creating a pending question."""
        questions = [{"id": "q1", "text": "Question 1"}]
        before = time.time()
        pending = PendingQuestion(
            question_id="q_123",
            questions=questions
        )
        after = time.time()

        assert pending.question_id == "q_123"
        assert pending.questions == questions
        assert not pending.answer_event.is_set()
        assert pending.answers == {}
        assert before <= pending.created_at <= after


class TestQuestionManager:
    """Test cases for QuestionManager."""

    def test_init_with_default_timeout(self):
        """Test initialization with default timeout."""
        manager = QuestionManager()
        assert manager.default_timeout == 60.0
        assert manager.get_pending_count() == 0

    def test_init_with_custom_timeout(self):
        """Test initialization with custom timeout."""
        manager = QuestionManager(default_timeout=30.0)
        assert manager.default_timeout == 30.0

    def test_create_question(self):
        """Test creating a pending question."""
        manager = QuestionManager()
        questions = [{"id": "q1", "text": "Question 1"}]

        pending = manager.create_question("q_123", questions)

        assert pending.question_id == "q_123"
        assert pending.questions == questions
        assert manager.get_pending_count() == 1
        assert manager.has_pending_question("q_123")

    @pytest.mark.asyncio
    async def test_submit_answer_success(self):
        """Test submitting answer to pending question."""
        manager = QuestionManager()
        questions = [{"id": "q1", "text": "Question 1"}]
        manager.create_question("q_123", questions)

        answers = {"q1": "Answer 1"}
        result = await manager.submit_answer("q_123", answers)

        assert result is True
        # submit_answer doesn't clean up - wait_for_answer does
        assert manager.get_pending_count() == 1

    @pytest.mark.asyncio
    async def test_submit_answer_unknown_question(self):
        """Test submitting answer to unknown question."""
        manager = QuestionManager()

        result = await manager.submit_answer("unknown_q", {"answer": "value"})

        assert result is False

    @pytest.mark.asyncio
    async def test_wait_for_answer_success(self):
        """Test waiting for answer successfully."""
        manager = QuestionManager(default_timeout=5.0)
        questions = [{"id": "q1", "text": "Question 1"}]
        manager.create_question("q_123", questions)

        # Submit answer in background
        async def submit_later():
            await asyncio.sleep(0.1)
            await manager.submit_answer("q_123", {"q1": "Answer 1"})

        task = asyncio.create_task(submit_later())
        answers = await manager.wait_for_answer("q_123")
        await task

        assert answers == {"q1": "Answer 1"}
        assert manager.get_pending_count() == 0  # Cleaned up by wait_for_answer

    @pytest.mark.asyncio
    async def test_wait_for_answer_timeout(self):
        """Test waiting for answer times out."""
        manager = QuestionManager(default_timeout=0.2)
        questions = [{"id": "q1", "text": "Question 1"}]
        manager.create_question("q_123", questions)

        with pytest.raises(asyncio.TimeoutError):
            await manager.wait_for_answer("q_123")

        # Question should be cleaned up after timeout
        assert manager.get_pending_count() == 0

    @pytest.mark.asyncio
    async def test_wait_for_answer_unknown_question(self):
        """Test waiting for unknown question raises KeyError."""
        manager = QuestionManager()

        with pytest.raises(KeyError, match="Question not found"):
            await manager.wait_for_answer("unknown_q")

    @pytest.mark.asyncio
    async def test_wait_for_answer_custom_timeout(self):
        """Test waiting with custom timeout override."""
        manager = QuestionManager(default_timeout=5.0)
        questions = [{"id": "q1", "text": "Question 1"}]
        manager.create_question("q_123", questions)

        with pytest.raises(asyncio.TimeoutError):
            await manager.wait_for_answer("q_123", timeout=0.1)

    def test_cancel_question_success(self):
        """Test canceling a pending question."""
        manager = QuestionManager()
        questions = [{"id": "q1", "text": "Question 1"}]
        manager.create_question("q_123", questions)

        result = manager.cancel_question("q_123")

        assert result is True
        # cancel_question doesn't remove from pending - wait_for_answer does
        assert manager.get_pending_count() == 1

    def test_cancel_question_unknown(self):
        """Test canceling unknown question."""
        manager = QuestionManager()

        result = manager.cancel_question("unknown_q")

        assert result is False

    @pytest.mark.asyncio
    async def test_cancel_unblocks_waiter(self):
        """Test that canceling unblocks waiting coroutine."""
        manager = QuestionManager(default_timeout=5.0)
        questions = [{"id": "q1", "text": "Question 1"}]
        manager.create_question("q_123", questions)

        # Cancel in background
        async def cancel_later():
            await asyncio.sleep(0.1)
            manager.cancel_question("q_123")

        task = asyncio.create_task(cancel_later())
        answers = await manager.wait_for_answer("q_123")
        await task

        # Empty answers when canceled
        assert answers == {}

    @pytest.mark.asyncio
    async def test_cleanup_orphaned_questions(self):
        """Test cleanup of orphaned questions."""
        manager = QuestionManager()

        # Create multiple questions with different ages
        pending1 = manager.create_question("q1", [])
        pending2 = manager.create_question("q2", [])
        pending3 = manager.create_question("q3", [])

        # Manually set created_at to simulate old questions
        pending1.created_at = time.time() - 400  # 400s old (orphaned)
        pending2.created_at = time.time() - 100  # 100s old (not orphaned)
        pending3.created_at = time.time() - 350  # 350s old (orphaned)

        assert manager.get_pending_count() == 3

        # Clean up questions older than 300s
        cleaned = await manager.cleanup_orphaned_questions(max_age_seconds=300)

        assert cleaned == 2  # q1 and q3 should be cleaned
        assert manager.get_pending_count() == 1
        assert manager.has_pending_question("q2")
        assert not manager.has_pending_question("q1")
        assert not manager.has_pending_question("q3")

    @pytest.mark.asyncio
    async def test_cleanup_orphaned_questions_none(self):
        """Test cleanup when no questions are orphaned."""
        manager = QuestionManager()

        manager.create_question("q1", [])
        manager.create_question("q2", [])

        # All questions are fresh
        cleaned = await manager.cleanup_orphaned_questions(max_age_seconds=300)

        assert cleaned == 0
        assert manager.get_pending_count() == 2

    @pytest.mark.asyncio
    async def test_cleanup_orphaned_questions_empty(self):
        """Test cleanup when no questions exist."""
        manager = QuestionManager()

        cleaned = await manager.cleanup_orphaned_questions(max_age_seconds=300)

        assert cleaned == 0
        assert manager.get_pending_count() == 0

    def test_get_pending_count(self):
        """Test getting pending question count."""
        manager = QuestionManager()

        assert manager.get_pending_count() == 0

        manager.create_question("q1", [])
        manager.create_question("q2", [])

        assert manager.get_pending_count() == 2

    def test_has_pending_question(self):
        """Test checking if question is pending."""
        manager = QuestionManager()

        assert not manager.has_pending_question("q1")

        manager.create_question("q1", [])

        assert manager.has_pending_question("q1")

        manager.cancel_question("q1")

        # Still pending until wait_for_answer cleans it up
        assert manager.has_pending_question("q1")


class TestQuestionManagerSingleton:
    """Test cases for QuestionManager singleton."""

    def test_get_singleton(self):
        """Test getting singleton instance."""
        manager1 = get_question_manager()
        manager2 = get_question_manager()

        assert manager1 is manager2

    def test_singleton_persists(self):
        """Test that singleton persists across calls."""
        manager = get_question_manager()
        manager.create_question("test_q", [])

        same_manager = get_question_manager()

        assert same_manager.has_pending_question("test_q")
