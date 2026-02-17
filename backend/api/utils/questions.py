"""Question field normalization utilities for AskUserQuestion tool.

This module provides a canonical implementation for normalizing the questions
field from AskUserQuestion tool input, which may be sent as:
- A proper list (correct format)
- A JSON string (needs parsing)
- An unexpected type (handled gracefully)

The model/provider sometimes serializes questions as a JSON string instead of
an array, causing validation failures. This module handles that edge case.
"""
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def normalize_questions_field(questions: Any, context: str = "") -> list:
    """Normalize the questions field from AskUserQuestion tool input.

    The model/provider sometimes sends questions as a JSON string instead of
    a proper array. This function handles both formats and returns a list.

    Args:
        questions: The questions field value - may be a list (correct) or
            a JSON string (needs parsing).
        context: Description of where this normalization is being called from,
            used for logging.

    Returns:
        A list of question dicts. Returns empty list if parsing fails.

    Examples:
        >>> normalize_questions_field([{"question": "What is your name?"}])
        [{'question': 'What is your name?'}]

        >>> normalize_questions_field('[{"question": "What is your name?"}]')
        [{'question': 'What is your name?'}]

        >>> normalize_questions_field(None)
        []

        >>> normalize_questions_field("invalid")
        []
    """
    if isinstance(questions, list):
        return questions

    if isinstance(questions, str):
        stripped = questions.strip()
        if not stripped:
            logger.warning(f"[{context}] AskUserQuestion questions is empty string, returning empty list")
            return []

        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, list):
                logger.info(
                    f"[{context}] Parsed AskUserQuestion questions from JSON string: "
                    f"{len(parsed)} questions"
                )
                return parsed
            else:
                logger.warning(
                    f"[{context}] Parsed AskUserQuestion questions JSON is not a list "
                    f"(got {type(parsed).__name__}), returning empty list"
                )
                return []
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(
                f"[{context}] Failed to parse AskUserQuestion questions string as JSON: {e}. "
                f"Raw value (first 200 chars): {stripped[:200]}"
            )
            return []

    logger.warning(
        f"[{context}] AskUserQuestion questions has unexpected type {type(questions).__name__}, "
        f"returning empty list"
    )
    return []
