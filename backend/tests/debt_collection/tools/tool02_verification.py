"""Verification agent tools."""

from typing import Annotated
from pydantic import Field
from livekit.agents.llm import function_tool
from livekit.agents.voice import Agent, RunContext

from .common_tools import transfer_to_agent, fuzzy_match
from shared_state import UserData

RunContext_T = RunContext[UserData]


@function_tool()
async def verify_field(
    field_name: Annotated[str, Field(description="Name of the field being verified (e.g., 'id_number', 'vehicle_registration', 'birth_date')")],
    provided_value: Annotated[str, Field(description="Value provided by the customer")],
    context: RunContext_T,
) -> str | tuple[Agent, str] | Agent:
    """
    Verify a single customer data field using fuzzy matching.
    Updates verified_fields set and auto-transfers to negotiation when 2+ fields verified.

    Supported fields:
    - username, id_number, birth_date, passport_number
    - vehicle_registration, vehicle_make, vehicle_model, vehicle_color
    - residential_address, contact_number, email
    """
    userdata = context.userdata
    debtor_info = userdata.debtor

    actual_value = getattr(debtor_info, field_name, None)

    if actual_value is None:
        return f"The field '{field_name}' is not available in our system. Please ask about a different field."

    userdata.call.verification_attempts += 1

    is_match = fuzzy_match(provided_value, str(actual_value), field_name=field_name)

    if is_match:
        userdata.call.verified_fields.add(field_name)
        userdata.call.current_field_attempts = 0

        # Auto-transfer to negotiation when 2+ fields verified
        if len(userdata.call.verified_fields) >= 2:
            userdata.call.identity_verified = True
            userdata.call.append_call_notes(f"Identity verified via {list(userdata.call.verified_fields)}")
            return await transfer_to_agent("negotiation", context, silent=True)

        return f"Thank you for confirming your {field_name.replace('_', ' ')}. That matches our records."
    else:
        userdata.call.add_failed_field(field_name)
        userdata.call.current_field_attempts += 1

        if userdata.call.current_field_attempts >= userdata.call.max_field_attempts:
            return f"The {field_name.replace('_', ' ')} you provided doesn't match our records. Let me try a different field to verify your identity."

        return f"The {field_name.replace('_', ' ')} doesn't match our records. Could you please verify it again?"


@function_tool()
async def mark_unavailable(
    field_name: Annotated[str, Field(description="Name of the field that's unavailable (e.g., 'passport_number', 'vehicle_registration')")],
    context: RunContext_T,
) -> str:
    """
    Mark a field as unavailable when customer doesn't have/remember the information.

    Usage: Call when customer says "I don't know", "I don't have that", "I can't remember", etc.
    """
    userdata = context.userdata
    userdata.call.unavailable_fields.add(field_name)
    userdata.call.current_field_attempts = 0

    all_fields = ["username", "id_number", "birth_date", "vehicle_registration", "residential_address", "contact_number"]
    available_fields = [f for f in all_fields if f not in userdata.call.verified_fields and f not in userdata.call.unavailable_fields]

    if available_fields:
        next_field = available_fields[0]
        return f"No problem. Can you verify your {next_field.replace('_', ' ')} instead?"
    else:
        return "I understand. Let me see what other information we can verify."
