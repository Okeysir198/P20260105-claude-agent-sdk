"""Agent 05: Closing - Call wrap-up and referral offers.

Purpose: Update contact details, offer referrals, confirm next steps, end call.
Transitions:
    - From: Any agent (various exit conditions)
    - To: End call (disconnect)
Tools: update_contact_info, offer_referral, end_call
"""

from .base_agent import BaseAgent


class ClosingAgent(BaseAgent):
    """Final agent - updates contact info, offers referrals, ends call."""

    async def on_enter(self) -> None:
        """Initialize agent and prompt first response."""
        await super().on_enter()
        self.session.generate_reply(tool_choice="none")
