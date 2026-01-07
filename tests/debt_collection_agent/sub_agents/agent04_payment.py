"""Payment Agent - Captures payment arrangements and processes setup."""

from typing import Any

from .base_agent import BaseAgent


class PaymentAgent(BaseAgent):
    """Agent that captures payment arrangements."""

    def __init__(
        self,
        instructions: str,
        tools: list[Any],
        **kwargs
    ):
        super().__init__(instructions=instructions, tools=tools, **kwargs)
