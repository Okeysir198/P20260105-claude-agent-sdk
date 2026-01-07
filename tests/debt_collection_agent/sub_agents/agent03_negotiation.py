"""Negotiation Agent - Explains debt and negotiates payment arrangements."""

from typing import Any

from .base_agent import BaseAgent


class NegotiationAgent(BaseAgent):
    """Agent that explains debt and negotiates payment arrangements."""

    def __init__(
        self,
        instructions: str,
        tools: list[Any],
        **kwargs
    ):
        super().__init__(instructions=instructions, tools=tools, **kwargs)
