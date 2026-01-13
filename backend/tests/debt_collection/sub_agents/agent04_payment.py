"""Agent 04: Payment - Capture banking details for DebiCheck.

Purpose: Collect bank account details and set up DebiCheck mandate.
Transitions:
    - From: Negotiation (payment arrangement agreed)
    - To: Closing (details captured or payment portal offered)
Tools: capture_bank_details, confirm_debit_date, send_payment_link
"""

from .base_agent import BaseAgent


class PaymentAgent(BaseAgent):
    """Captures payment details (DebiCheck mandate or payment portal)."""

    async def on_enter(self) -> None:
        """Initialize agent and prompt first response."""
        await super().on_enter()
        self.session.generate_reply(tool_choice="none")
