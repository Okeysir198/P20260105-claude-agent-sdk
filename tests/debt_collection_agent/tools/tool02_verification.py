"""Verification agent tools."""

from typing import Annotated
from pydantic import Field
from livekit.agents.llm import function_tool, ToolError
from livekit.agents.voice import RunContext

from shared_state import UserData
from state.types import PersonType

RunContext_T = RunContext[UserData]


@function_tool()
async def verify_field(
    field: Annotated[
        str,
        Field(description="Field to verify: username, id_number, email, contact_number, or vehicle_registration")
    ],
    provided_value: Annotated[str, Field(description="Value provided by customer")],
    context: RunContext_T,
) -> str:
    """
    Verify customer identity by checking provided value against records.

    Usage: Call when customer provides information to verify their identity.
    Compare at least 2 fields before marking as verified.
    """
    userdata = context.userdata
    profile = userdata.debtor
    session = userdata.call

    # Get actual value from profile
    actual_values = {
        "username": profile.username,
        "id_number": profile.id_number,
        "email": profile.email,
        "contact_number": profile.contact_number,
        "vehicle_registration": profile.vehicle_registration,
    }
    actual = actual_values.get(field)

    if not actual:
        raise ToolError(f"Field '{field}' not available for verification")

    # Simple comparison (case-insensitive, strip whitespace)
    if provided_value.lower().strip() == actual.lower().strip():
        session.mark_verified(field)
        session.add_note(f"Verified: {field}")

        if len(session.verified_fields) >= 2:
            session.identity_verified = True
            return f"Identity verified. {field} confirmed. You are now verified."

        return f"Thank you. {field} confirmed. Please verify one more field."
    else:
        session.verification_attempts += 1
        session.add_failed_field(field)

        if session.verification_attempts >= 3:
            session.identity_verified = False
            raise ToolError("Maximum verification attempts exceeded. Please schedule a callback.")

        return f"That doesn't match our records. Please try again."


@function_tool()
async def mark_unavailable(
    reason: Annotated[str, Field(description="Reason customer cannot verify (e.g., 'forgot password', 'no access to documents')")],
    context: RunContext_T,
) -> str:
    """
    Mark customer as unable to verify identity at this time.

    Usage: Call when customer cannot provide verification information.
    """
    userdata = context.userdata
    userdata.call.unavailable_fields.add(reason)
    userdata.call.add_note(f"Verification unavailable: {reason}")

    return "I understand. Let's schedule a callback for when you have access to your information."
