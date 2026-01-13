"""
Immutable debtor profile for debt collection sessions.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .types import AccountStatus


@dataclass(frozen=True)
class DebtorProfile:
    """
    Immutable debtor profile loaded from job metadata.

    Contains all debtor information required for identity verification,
    payment processing, and compliance documentation.
    """

    # Required Identity
    full_name: str
    user_id: str
    username: str

    # Identity Documents
    id_number: Optional[str] = None
    passport_number: Optional[str] = None
    birth_date: Optional[str] = None

    # Contact Information
    email: Optional[str] = None
    contact_number: Optional[str] = None
    alternative_number: Optional[str] = None
    residential_address: Optional[str] = None

    # Vehicle Information
    vehicle_registration: Optional[str] = None
    vehicle_make: Optional[str] = None
    vehicle_model: Optional[str] = None
    vehicle_color: Optional[str] = None
    vin_number: Optional[str] = None

    # Banking Information
    bank_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    branch_code: Optional[str] = None
    salary_date: Optional[str] = None
    has_reversal_history: bool = False

    # Debt Information
    outstanding_amount: Optional[float] = None
    overdue_days: Optional[int] = None
    account_status: str = AccountStatus.ACTIVE.value
    monthly_subscription: Optional[float] = None
    cancellation_fee: Optional[float] = None
    partial_payment_received: Optional[float] = None
    agreed_amount: Optional[float] = None

    # Next of Kin
    next_of_kin_name: Optional[str] = None
    next_of_kin_relationship: Optional[str] = None
    next_of_kin_contact: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate required fields."""
        if not self.full_name or not self.full_name.strip():
            raise ValueError("Full name is required")
        if not self.user_id or not self.user_id.strip():
            raise ValueError("User ID is required")
        if not self.username or not self.username.strip():
            raise ValueError("Username is required")
        if self.outstanding_amount is not None and self.outstanding_amount <= 0:
            raise ValueError(f"Outstanding amount must be positive: {self.outstanding_amount}")

    @property
    def shortfall_amount(self) -> Optional[float]:
        """Calculate shortfall for short_paid scripts."""
        if self.partial_payment_received is not None and self.agreed_amount is not None:
            return self.agreed_amount - self.partial_payment_received
        return None

    @classmethod
    def from_metadata(cls, metadata: Dict[str, Any]) -> "DebtorProfile":
        """
        Create DebtorProfile from job metadata dictionary.

        Args:
            metadata: Dictionary containing debtor information

        Returns:
            New DebtorProfile instance
        """
        defaults = {
            "full_name": "",
            "user_id": "",
            "username": "",
            "account_status": AccountStatus.ACTIVE.value,
            "has_reversal_history": False,
        }
        return cls(**{**defaults, **metadata})

    def get_verification_fields(self) -> Dict[str, Any]:
        """
        Get available fields for identity verification.

        Returns:
            Dictionary of non-None verification fields
        """
        fields = {
            "username": self.username,
            "id_number": self.id_number,
            "passport_number": self.passport_number,
            "birth_date": self.birth_date,
            "email": self.email,
            "contact_number": self.contact_number,
            "vehicle_registration": self.vehicle_registration,
            "residential_address": self.residential_address,
        }
        return {k: v for k, v in fields.items() if v is not None}

    def format_outstanding(self) -> str:
        """Format outstanding amount as currency string."""
        if self.outstanding_amount is None:
            return "N/A"
        return f"R{self.outstanding_amount:,.2f}"
