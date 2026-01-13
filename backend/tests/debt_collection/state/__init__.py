"""
Modular state management for debt collection voice agents.

This package provides clean, type-safe state management:
- types: Enumeration types (PersonType, PaymentMethod, CallOutcome, etc.)
- profile: Immutable DebtorProfile dataclass
- session: Mutable CallState dataclass
"""

from .profile import DebtorProfile
from .session import CallState
from .types import (
    AccountStatus,
    BankValidationStatus,
    CallOutcome,
    NegotiationOutcome,
    PaymentMethod,
    PaymentType,
    PersonType,
)

__all__ = [
    # Profile
    "DebtorProfile",
    # Session
    "CallState",
    # Types
    "AccountStatus",
    "BankValidationStatus",
    "CallOutcome",
    "NegotiationOutcome",
    "PaymentMethod",
    "PaymentType",
    "PersonType",
]
