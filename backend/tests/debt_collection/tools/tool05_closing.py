"""Closing agent tools."""

from typing import Annotated, Optional
from datetime import datetime
from pydantic import Field
from livekit.agents.llm import function_tool
from livekit.agents.voice import RunContext

from shared_state import UserData

RunContext_T = RunContext[UserData]


@function_tool()
async def offer_referral(
    referral_name: Annotated[str, Field(description="Name of the person being referred")],
    referral_contact: Annotated[str, Field(description="Contact number of the referral")],
    context: RunContext_T,
    referral_email: Annotated[Optional[str], Field(description="Email address of the referral (optional)")] = None,
    relationship: Annotated[Optional[str], Field(description="Relationship to customer (e.g., 'friend', 'family', 'colleague')")] = None,
) -> str:
    """
    Record a referral provided by the customer.

    Usage: Call when customer offers to refer someone who might need Cartrack services.
    Customer receives 2 months of free subscription when referral signs up and has unit installed.
    """
    userdata = context.userdata
    call = userdata.call

    referral_data = {
        "name": referral_name,
        "contact": referral_contact,
        "date": datetime.now().isoformat()
    }

    if referral_email:
        referral_data["email"] = referral_email

    if relationship:
        referral_data["relationship"] = relationship

    call.referrals.append(referral_data)

    return f"Thank you for referring {referral_name}. Our team will reach out to them. Remember, when they sign up and have a unit installed, you will receive 2 months of free subscription. We appreciate your recommendation!"


@function_tool()
async def update_contact_details(
    context: RunContext_T,
    contact_number: Annotated[Optional[str], Field(description="Updated primary contact number")] = None,
    alternative_number: Annotated[Optional[str], Field(description="Updated alternative/secondary contact number")] = None,
    email: Annotated[Optional[str], Field(description="Updated email address")] = None,
) -> str:
    """
    Update customer's contact information.

    Usage: Call when customer provides updated contact details.
    At least one field must be provided.
    """
    userdata = context.userdata
    call = userdata.call

    updated_fields = []

    if contact_number:
        updated_fields.append(f"contact number: {contact_number}")

    if alternative_number:
        updated_fields.append(f"alternative number: {alternative_number}")

    if email:
        updated_fields.append(f"email: {email}")

    if updated_fields:
        call.contact_details_updated = True
        call.append_call_notes(f"Contact details updated: {', '.join(updated_fields)}")
        return f"Contact details updated: {', '.join(updated_fields)}"
    else:
        return "No contact details were updated."


@function_tool()
async def update_next_of_kin(
    name: Annotated[str, Field(description="Next of kin / emergency contact name")],
    relationship: Annotated[str, Field(description="Relationship to customer (e.g., 'spouse', 'parent', 'sibling')")],
    contact_number: Annotated[str, Field(description="Next of kin contact number")],
    context: RunContext_T,
) -> str:
    """
    Update next of kin / emergency contact information.

    Usage: Call when customer provides emergency contact details.
    """
    userdata = context.userdata
    call = userdata.call

    call.next_of_kin = {
        "name": name,
        "relationship": relationship,
        "contact_number": contact_number
    }

    return f"Next of kin updated: {name} ({relationship}) - {contact_number}"


@function_tool()
async def explain_subscription(context: RunContext_T) -> str:
    """
    Retrieve subscription notification script for active accounts.

    Usage: Call when customer asks about subscription status or before ending call
    with active account holders to remind them their subscription will continue.
    """
    userdata = context.userdata
    debtor = userdata.debtor
    account_status = debtor.account_status

    if account_status != "active":
        return "This account is not active, so no subscription notification is needed."

    userdata.call.subscription_explained = True
    return "Your Cartrack subscription will continue as normal once the payment arrangement is completed."
