"""
Tools Package for Debt Collection Multi-Agent System.

Public API: TOOL_REGISTRY and get_tools_by_names()
Individual tools are accessed via the registry, not direct imports.
"""

import logging
from typing import Any

# Import all tools to register them
from .common_tools import schedule_callback, escalate, handle_cancellation_request, end_call
from .tool01_introduction import confirm_person, handle_wrong_person, handle_third_party
from .tool02_verification import verify_field, mark_unavailable
from .tool03_negotiation import offer_settlement, offer_installment, accept_arrangement, explain_consequences, explain_benefits, offer_tier2_fallback
from .tool04_payment import capture_immediate_debit, validate_bank_details, update_bank_details, setup_debicheck, send_portal_link, confirm_portal_payment, confirm_arrangement
from .tool05_closing import offer_referral, update_contact_details, update_next_of_kin, explain_subscription

logger = logging.getLogger(__name__)

# Tool Registry - single source of truth for all tools
TOOL_REGISTRY = {
    # Introduction tools
    "confirm_person": confirm_person,
    "handle_wrong_person": handle_wrong_person,
    "handle_third_party": handle_third_party,
    # Verification tools
    "verify_field": verify_field,
    "mark_unavailable": mark_unavailable,
    # Negotiation tools
    "offer_settlement": offer_settlement,
    "offer_installment": offer_installment,
    "accept_arrangement": accept_arrangement,
    "explain_consequences": explain_consequences,
    "explain_benefits": explain_benefits,
    "offer_tier2_fallback": offer_tier2_fallback,
    # Payment tools
    "capture_immediate_debit": capture_immediate_debit,
    "validate_bank_details": validate_bank_details,
    "update_bank_details": update_bank_details,
    "setup_debicheck": setup_debicheck,
    "send_portal_link": send_portal_link,
    "confirm_portal_payment": confirm_portal_payment,
    "confirm_arrangement": confirm_arrangement,
    # Closing tools
    "offer_referral": offer_referral,
    "update_contact_details": update_contact_details,
    "update_next_of_kin": update_next_of_kin,
    "explain_subscription": explain_subscription,
    # Common tools
    "schedule_callback": schedule_callback,
    "escalate": escalate,
    "handle_cancellation_request": handle_cancellation_request,
    "end_call": end_call,
}


def get_tools_by_names(tool_names: list[str], strict: bool = True) -> list[Any]:
    """
    Get tools from registry by name.

    Args:
        tool_names: List of tool names to retrieve
        strict: If True, raise error on missing tools. If False, log warning.

    Returns:
        List of tool functions

    Raises:
        ValueError: If strict=True and any tools are missing
    """
    tools = []
    missing = []

    for name in tool_names:
        tool = TOOL_REGISTRY.get(name)
        if tool:
            tools.append(tool)
        else:
            missing.append(name)

    if missing:
        available = sorted(TOOL_REGISTRY.keys())
        error_msg = (
            f"Unknown tools: {missing}\n"
            f"Available tools: {available}"
        )

        if strict:
            raise ValueError(error_msg)
        else:
            logger.warning(error_msg)

    return tools


__all__ = [
    "TOOL_REGISTRY",
    "get_tools_by_names",
]
