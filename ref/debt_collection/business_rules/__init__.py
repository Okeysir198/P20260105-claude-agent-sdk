"""
Business Rules Module for Debt Collection Voice Agent.

Public API for configuration data and context generation.
"""

from .config import (
    AUTHORITIES,
    SCRIPT_TYPES,
    FEES,
    BUSINESS_HOURS,
    get_campaign_deadline,
)

from .script_context import (
    get_consequences,
    get_benefits,
    build_negotiation_context,
    build_payment_context,
)

__all__ = [
    # Configuration data
    "AUTHORITIES",
    "SCRIPT_TYPES",
    "FEES",
    "BUSINESS_HOURS",
    "get_campaign_deadline",
    # Context generation
    "build_negotiation_context",
    "build_payment_context",
    "get_consequences",
    "get_benefits",
]
