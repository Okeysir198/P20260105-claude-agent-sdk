"""
State package for debt collection voice agent.

Provides:
- Types: Enumerations for person types, payment methods, outcomes
- Profile: Immutable debtor profile data
- Session: Mutable call session state
"""

from .types import (
    PersonType,
    PaymentMethod,
    CallOutcome,
    PaymentType,
    AccountStatus,
    BankValidationStatus,
    NegotiationOutcome,
)
from .profile import DebtorProfile
from .session import CallState

__all__ = [
    # Types
    "PersonType",
    "PaymentMethod",
    "CallOutcome",
    "PaymentType",
    "AccountStatus",
    "BankValidationStatus",
    "NegotiationOutcome",
    # Dataclasses
    "DebtorProfile",
    "CallState",
]
