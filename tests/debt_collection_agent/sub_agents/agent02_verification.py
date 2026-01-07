"""Verification Agent - POPI-compliant identity verification."""

from typing import Any

from .base_agent import BaseAgent


class VerificationAgent(BaseAgent):
    """Agent that verifies customer identity."""

    def __init__(
        self,
        instructions: str,
        tools: list[Any],
        **kwargs
    ):
        super().__init__(instructions=instructions, tools=tools, **kwargs)
