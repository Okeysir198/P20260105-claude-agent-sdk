"""
Enumeration types for debt collection state management.
"""

from enum import Enum


class PersonType(Enum):
    """Type of person answering the call."""
    CORRECT = "correct"
    WRONG = "wrong"
    THIRD_PARTY = "third_party"


class PaymentMethod(Enum):
    """Available payment methods."""
    DEBIT_ORDER = "debit_order"
    DEBICHECK = "debicheck"
    PORTAL = "portal"
    ONCE_OFF = "once_off"
    MANUAL = "manual"


class CallOutcome(Enum):
    """Final outcome of a debt collection call."""
    SUCCESS = "success"
    CALLBACK = "callback"
    ESCALATION = "escalation"
    REFUSAL = "refusal"
    CANCELLED = "cancelled"


class PaymentType(Enum):
    """Type of payment arrangement."""
    FULL = "full"
    PARTIAL = "partial"
    ARRANGEMENT = "arrangement"
    SETTLEMENT = "settlement"
    INSTALLMENT = "installment"


class AccountStatus(Enum):
    """Debtor account status."""
    ACTIVE = "active"
    CANCELLED = "cancelled"
    OVERDUE = "overdue"
    DEFAULT = "default"
    COLLECTIONS = "collections"


class BankValidationStatus(Enum):
    """Bank validation status."""
    PENDING = "pending"
    VALID = "valid"
    INVALID = "invalid"
    FAILED = "failed"


class NegotiationOutcome(Enum):
    """Outcome of payment negotiation."""
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    COUNTER_OFFERED = "counter_offered"
