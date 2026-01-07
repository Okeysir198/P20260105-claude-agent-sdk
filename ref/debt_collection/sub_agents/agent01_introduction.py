"""Agent 01: Introduction - First contact with caller.

Purpose: Greet caller and confirm speaking with the correct person (debtor).
Transitions:
    - From: Entry point (session start)
    - To: Verification (debtor confirmed) or Closing (wrong number/third party)
Tools: confirm_person, handle_wrong_person, handle_third_party
"""

from .base_agent import BaseAgent


class IntroductionAgent(BaseAgent):
    """Entry point agent - confirms speaking with correct person."""

    async def on_enter(self) -> None:
        """Initialize agent and prompt first response."""
        await super().on_enter()
        self.session.generate_reply(tool_choice="none")
