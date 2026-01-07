"""Introduction agent tools."""

from typing import Annotated
from pydantic import Field
from livekit.agents.llm import function_tool
from livekit.agents.voice import Agent, RunContext

from .common_tools import transfer_to_agent
from shared_state import UserData
from state.types import PersonType, CallOutcome

RunContext_T = RunContext[UserData]


@function_tool()
async def confirm_person(context: RunContext_T):
    """
    Called when the caller confirms they are the correct person.

    Usage: Call this ONLY when the customer explicitly confirms "Yes" or "That's me"
    to the question "Am I speaking with [full_name]?"
    """
    userdata = context.userdata
    userdata.call.person_confirmed = True
    userdata.call.person_type = PersonType.CORRECT
    userdata.call.add_note("Person confirmed as correct")

    return await transfer_to_agent("verification", context, silent=True)


@function_tool()
async def handle_wrong_person(context: RunContext_T):
    """
    Called when the person on the line is NOT the debtor (wrong number).

    Usage: Call when caller says "Wrong number", "You have the wrong person", etc.
    """
    userdata = context.userdata
    userdata.call.person_confirmed = False
    userdata.call.person_type = PersonType.WRONG
    userdata.call.call_outcome = CallOutcome.REFUSAL
    userdata.call.add_note("Wrong person - not the debtor")

    return await transfer_to_agent("closing", context, silent=True)


@function_tool()
async def handle_third_party(
    relationship: Annotated[str, Field(description="Relationship to debtor (e.g., 'spouse', 'parent', 'colleague')")],
    context: RunContext_T,
):
    """
    Called when a third party (not the debtor) answers the call.

    Usage: Call when caller says "I'm his wife", "This is her mother", etc.
    """
    userdata = context.userdata
    userdata.call.person_confirmed = False
    userdata.call.person_type = PersonType.THIRD_PARTY
    userdata.call.third_party_relationship = relationship
    userdata.call.call_outcome = CallOutcome.CALLBACK
    userdata.call.add_note(f"Third party: {relationship}")

    return await transfer_to_agent("closing", context, silent=True)
