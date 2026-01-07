"""
Shared state aggregator for debt collection voice agent sessions.

This module provides the UserData container that aggregates debtor profile,
call state, and agent tracking into a single session state object.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional

from state import CallState, DebtorProfile
from state.types import CallOutcome

if TYPE_CHECKING:
    from livekit.agents import Agent

logger = logging.getLogger("debt-collection-agent")


@dataclass
class UserData:
    """
    Main session state container for debt collection calls.

    Aggregates debtor profile, call state, and agent transition tracking.
    """

    debtor: DebtorProfile
    call: CallState = field(default_factory=CallState)
    agents: Dict[str, "Agent"] = field(default_factory=dict)
    prev_agent: Optional["Agent"] = None

    # Metadata
    session_id: Optional[str] = None
    call_start_time: Optional[str] = None
    current_agent_id: Optional[str] = None
    job_context: Optional[Any] = None

    def summarize(self) -> str:
        """
        Generate a text summary of the session state for agent context.

        Returns:
            Formatted string containing debtor info and call progress
        """
        lines = [
            f"Session: {self.session_id or 'N/A'}",
            "",
            "Debtor:",
            f"  Name: {self.debtor.full_name}",
            f"  User ID: {self.debtor.user_id}",
            f"  Username: {self.debtor.username}",
        ]

        if self.debtor.outstanding_amount is not None:
            lines.append(f"  Outstanding: {self.debtor.format_outstanding()}")
        if self.debtor.overdue_days is not None:
            lines.append(f"  Overdue: {self.debtor.overdue_days} days")
        lines.append(f"  Status: {self.debtor.account_status}")

        if self.debtor.email or self.debtor.contact_number:
            lines.extend(["", "Contact:"])
            if self.debtor.email:
                lines.append(f"  Email: {self.debtor.email}")
            if self.debtor.contact_number:
                lines.append(f"  Phone: {self.debtor.contact_number}")

        progress = self.call.get_progress()
        lines.extend([
            "",
            "Call Progress:",
            f"  Script: {self.call.script_type}",
            f"  Person Type: {self.call.person_type.value if self.call.person_type else 'unknown'}",
            f"  Introduction: {'done' if progress['introduction'] else 'pending'}",
            f"  Verification: {'done' if progress['verification'] else 'pending'}",
            f"  Negotiation: {'done' if progress['negotiation'] else 'pending'}",
            f"  Payment: {'done' if progress['payment'] else 'pending'}",
            f"  Closing: {'done' if progress['closing'] else 'pending'}",
        ])

        if self.call.identity_verified:
            lines.append(
                f"  Verified Fields: {len(self.call.verified_fields)} "
                f"({self.call.verification_attempts} attempts)"
            )

        if self.call.discount_offered and self.call.discount_amount:
            status = "accepted" if self.call.discount_accepted else "pending"
            lines.append(f"  Discount: R{self.call.discount_amount:,.2f} ({status})")

        if self.call.payment_type:
            lines.extend([
                "",
                "Payment:",
                f"  Type: {self.call.payment_type.value if self.call.payment_type else 'N/A'}",
                f"  Method: {self.call.payment_method.value if self.call.payment_method else 'N/A'}",
                f"  Confirmed: {'Yes' if self.call.payment_confirmed else 'No'}",
            ])
            if self.call.payment_arrangements:
                lines.append(f"  Arrangements: {len(self.call.payment_arrangements)}")

        if self.call.call_outcome:
            lines.append(f"\nOutcome: {self.call.call_outcome.value}")

        if self.call.escalation_reason:
            lines.extend(["", f"Escalation: {self.call.escalation_reason}"])

        if self.call.call_notes:
            lines.extend(["", "Recent Notes:"])
            for note in self.call.call_notes[-5:]:
                lines.append(f"  {note}")

        return "\n".join(lines)

    def cleanup(self) -> None:
        """
        Clean up session resources at end of call.

        Breaks circular references and clears large collections.
        Should be called in a finally block.
        """
        logger.info("Cleaning up UserData resources")

        if self.agents:
            logger.debug(f"Clearing {len(self.agents)} agent references")
            self.agents.clear()

        self.prev_agent = None

        if self.call.call_notes:
            logger.debug(f"Clearing {len(self.call.call_notes)} call notes")
            self.call.call_notes.clear()

        if self.call.payment_arrangements:
            logger.debug(f"Clearing {len(self.call.payment_arrangements)} arrangements")
            self.call.payment_arrangements.clear()

        if self.call.referrals:
            logger.debug(f"Clearing {len(self.call.referrals)} referrals")
            self.call.referrals.clear()

        self.job_context = None
        logger.info("UserData cleanup complete")

    def set_outcome(self, outcome: CallOutcome, note: Optional[str] = None) -> None:
        """
        Set the call outcome with optional note.

        Args:
            outcome: Final call outcome
            note: Optional note to add
        """
        self.call.call_outcome = outcome
        if note:
            self.call.add_note(note)

    def get_duration_seconds(self) -> Optional[int]:
        """Get call duration in seconds if start time is set."""
        if not self.call_start_time:
            return None
        try:
            start = datetime.fromisoformat(self.call_start_time)
            return int((datetime.now() - start).total_seconds())
        except ValueError:
            return None


def get_test_debtor() -> Dict[str, Any]:
    """
    Default test debtor data for local development.

    Returns:
        Dictionary with 'debtor' and 'script_type' keys
    """
    return {
        "debtor": {
            "full_name": "John Smith",
            "user_id": "12345",
            "username": "jsmith",
            "email": "john.smith@example.com",
            "contact_number": "0821234567",
            "id_number": "8501125678901",
            "birth_date": "1985-01-12",
            "residential_address": "123 Main Street, Johannesburg, 2000",
            "vehicle_registration": "ABC123GP",
            "vehicle_make": "Toyota",
            "vehicle_model": "Corolla",
            "vehicle_color": "Silver",
            "outstanding_amount": 5000.00,
            "overdue_days": 45,
            "account_status": "overdue",
            "monthly_subscription": 500.00,
            "cancellation_fee": 1500.00,
            "salary_date": "25",
            "bank_name": "Standard Bank",
            "bank_account_number": "1234567890",
        },
        "script_type": "ratio1_inflow",
    }


def create_test_userdata() -> UserData:
    """
    Create test UserData instance for eval framework.

    Returns:
        Fully populated UserData instance for testing
    """
    data = get_test_debtor()
    debtor = DebtorProfile.from_metadata(data["debtor"])
    call = CallState(script_type=data["script_type"])
    return UserData(debtor=debtor, call=call)
