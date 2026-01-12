"""
Mutable call state for debt collection sessions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Union

from .types import (
    BankValidationStatus,
    CallOutcome,
    NegotiationOutcome,
    PaymentMethod,
    PaymentType,
    PersonType,
)


@dataclass
class CallState:
    """
    Mutable state tracking call progression through debt collection workflow.

    Maintains current state including completed steps, verification status,
    negotiation outcomes, and payment arrangements.
    """

    # Script Configuration
    script_type: str = "standard"
    authority: Optional[str] = None
    authority_contact: Optional[str] = None

    # Introduction Phase
    person_confirmed: bool = False
    person_type: Optional[PersonType] = None
    third_party_relationship: Optional[str] = None

    # Verification Phase
    identity_verified: bool = False
    verified_fields: Set[str] = field(default_factory=set)
    unavailable_fields: Set[str] = field(default_factory=set)
    verification_attempts: int = 0
    failed_verification_fields: List[str] = field(default_factory=list)
    current_field_attempts: int = 0
    max_field_attempts: int = 3

    # Negotiation Phase
    reason_explained: bool = False
    consequences_explained: bool = False
    benefits_explained: bool = False
    discount_offered: bool = False
    discount_amount: Optional[float] = None
    discount_accepted: bool = False
    tier1_offered: bool = False
    tier2_offered: bool = False

    # Negotiation Tracking
    payment_arrangement_type: Optional[PaymentType] = None
    discount_applied: bool = False
    discount_percentage: Optional[float] = None
    settlement_amount: Optional[float] = None
    installment_amount: Optional[float] = None
    installment_months: Optional[int] = None
    total_installment_amount: Optional[float] = None
    arrangement_accepted: bool = False
    negotiation_outcome: Optional[NegotiationOutcome] = None

    # Payment Phase
    payment_type: Optional[PaymentType] = None
    payment_method: Optional[PaymentMethod] = None
    payment_arrangements: List[Dict[str, Any]] = field(default_factory=list)
    payment_confirmed: bool = False
    debicheck_sent: bool = False
    portal_link_sent: bool = False

    # Bank Validation
    bank_validation_status: Optional[BankValidationStatus] = None
    bank_details_updated: bool = False

    # Details Update Phase
    contact_details_updated: bool = False
    banking_details_updated: bool = False
    next_of_kin_updated: bool = False

    # Closing Phase
    subscription_explained: bool = False
    referral_offered: bool = False
    referral_accepted: bool = False
    referrals: List[Dict[str, Any]] = field(default_factory=list)
    next_of_kin: Optional[Dict[str, str]] = None

    # Cancellation Phase
    cancellation_requested: bool = False
    cancellation_ticket_id: Optional[str] = None

    # Callback Management
    callback_scheduled: bool = False
    callback_datetime: Optional[str] = None
    callback_reason: Optional[str] = None

    # Escalation
    escalation_reason: Optional[str] = None
    escalation_notes: Optional[str] = None

    # Call Outcome
    call_outcome: Optional[CallOutcome] = None
    call_notes: List[str] = field(default_factory=list)

    def add_note(self, note: str) -> None:
        """
        Append a timestamped note to call notes.

        Args:
            note: Note text to append
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.call_notes.append(f"[{timestamp}] {note}")

    def append_call_notes(self, note: str) -> None:
        """Alias for add_note for backward compatibility."""
        self.add_note(note)

    def add_failed_field(self, field_name: str) -> None:
        """Record a field that failed verification."""
        if field_name not in self.failed_verification_fields:
            self.failed_verification_fields.append(field_name)

    def add_payment_arrangement(
        self,
        amount: float,
        date: str,
        method: Union[PaymentMethod, str],
        description: Optional[str] = None,
    ) -> None:
        """
        Add a payment arrangement.

        Args:
            amount: Payment amount
            date: Payment date (ISO format or DD/MM/YYYY)
            method: Payment method (PaymentMethod enum or string)
            description: Optional description
        """
        method_value = method.value if isinstance(method, PaymentMethod) else method
        self.payment_arrangements.append({
            "amount": amount,
            "date": date,
            "method": method_value,
            "description": description,
            "created_at": datetime.now().isoformat(),
        })

    def add_referral(
        self,
        name: str,
        contact: str,
        relationship: Optional[str] = None,
    ) -> None:
        """
        Add a referral record.

        Args:
            name: Referral name
            contact: Contact number
            relationship: Relationship to debtor
        """
        self.referrals.append({
            "name": name,
            "contact": contact,
            "relationship": relationship,
            "created_at": datetime.now().isoformat(),
        })

    def set_person_type(self, person_type: PersonType) -> None:
        """Set the person type and mark person as confirmed."""
        self.person_type = person_type
        self.person_confirmed = True

    def mark_verified(self, field_name: str) -> None:
        """Mark a field as successfully verified."""
        self.verified_fields.add(field_name)
        self.verification_attempts += 1

    def is_introduction_complete(self) -> bool:
        """Check if introduction phase is complete."""
        return self.person_confirmed and self.person_type is not None

    def is_verification_complete(self) -> bool:
        """Check if verification phase is complete."""
        return self.identity_verified

    def is_negotiation_complete(self) -> bool:
        """Check if negotiation phase is complete."""
        return self.reason_explained and self.consequences_explained

    def is_payment_complete(self) -> bool:
        """Check if payment phase is complete."""
        return self.payment_confirmed

    def get_progress(self) -> Dict[str, bool]:
        """Get completion status of each phase."""
        return {
            "introduction": self.is_introduction_complete(),
            "verification": self.is_verification_complete(),
            "negotiation": self.is_negotiation_complete(),
            "payment": self.is_payment_complete(),
            "closing": self.call_outcome is not None,
        }
