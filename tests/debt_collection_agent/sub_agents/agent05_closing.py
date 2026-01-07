"""Closing Agent - Handles referrals, contact updates, and call wrap-up."""

from typing import Any

from .base_agent import BaseAgent


class ClosingAgent(BaseAgent):
    """Agent that handles call closing and wrap-up."""

    def __init__(
        self,
        instructions: str,
        tools: list[Any],
        **kwargs
    ):
        super().__init__(instructions=instructions, tools=tools, **kwargs)
