"""Agent 02: Verification - POPI-compliant identity verification.

Purpose: Verify caller identity by confirming 2+ personal data fields.
Transitions:
    - From: Introduction (person confirmed)
    - To: Negotiation (verified) or Closing (failed/unavailable)
Tools: verify_field, mark_unavailable
"""

from .base_agent import BaseAgent


class VerificationAgent(BaseAgent):
    """Verifies debtor identity through fuzzy matching (requires 2+ fields)."""

    async def on_enter(self) -> None:
        """Initialize agent and prompt first response."""
        await super().on_enter()
        self.session.generate_reply(tool_choice="none")
