"""Closing agent tools."""

from typing import Annotated
from pydantic import Field
from livekit.agents.llm import function_tool
from livekit.agents.voice import RunContext

from shared_state import UserData

RunContext_T = RunContext[UserData]


@function_tool()
async def offer_referral(context: RunContext_T) -> str:
    """
    Offer to help with referrals or alternative contacts.

    Usage: Call when offering to take referral information or contact details.
    """
    userdata = context.userdata
    userdata.call.referral_offered = True
    userdata.call.add_note("Referral offered")

    return "Would you like to provide any referral information or alternative contact details we can reach out to?"


@function_tool()
async def update_contact_details(
    new_phone: Annotated[str, Field(description="New phone number")] = None,
    new_email: Annotated[str, Field(description="New email address")] = None,
    context: RunContext_T = None,
) -> str:
    """
    Update customer contact details.

    Usage: Call when customer provides new contact information.
    """
    userdata = context.userdata

    if new_phone:
        userdata.call.add_note(f"Phone update requested: {new_phone}")
    if new_email:
        userdata.call.add_note(f"Email update requested: {new_email}")

    userdata.call.contact_details_updated = True

    return "Thank you. I've noted your updated contact details."
