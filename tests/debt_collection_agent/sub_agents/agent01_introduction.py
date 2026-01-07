"""Introduction Agent - Confirms speaking with correct person."""

from typing import Any

from .base_agent import BaseAgent


class IntroductionAgent(BaseAgent):
    """Agent that confirms we're speaking with the correct person."""

    def __init__(
        self,
        instructions: str,
        tools: list[Any],
        **kwargs
    ):
        super().__init__(instructions=instructions, tools=tools, **kwargs)
