"""Normalization for AskUserQuestion tool input.

The model sometimes serializes the questions field as a JSON string instead
of a list. This module handles both formats gracefully.
"""
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def normalize_questions_field(questions: Any, context: str = "") -> list:
    """Normalize questions field to a list, handling both list and JSON string formats."""
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
