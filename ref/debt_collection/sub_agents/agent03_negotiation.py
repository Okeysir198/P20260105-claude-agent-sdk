"""Agent 03: Negotiation - Debt explanation and payment arrangement.

Purpose: Explain outstanding debt and negotiate settlement or installment plan.
Transitions:
    - From: Verification (identity confirmed)
    - To: Payment (agreement reached) or Closing (refused/callback)
Tools: explain_debt, propose_settlement, propose_installment, schedule_callback
"""

from .base_agent import BaseAgent


class NegotiationAgent(BaseAgent):
    """Explains debt and negotiates payment (settlement/installment)."""

    async def on_enter(self) -> None:
        """Initialize agent and prompt first response."""
        await super().on_enter()
        self.session.generate_reply(tool_choice="none")
