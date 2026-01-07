"""Common tools for multiple agents."""

import asyncio
import os
import random
from typing import Annotated, Literal, Optional
from datetime import datetime, date

from pydantic import Field
from livekit import api
from livekit.agents.llm import function_tool, ToolError
from livekit.agents.voice import Agent, RunContext

from utils.fuzzy_match import fuzzy_match as _fuzzy_match_comprehensive
from shared_state import UserData
from business_rules import BUSINESS_HOURS
from state.types import CallOutcome

RunContext_T = RunContext[UserData]


def fuzzy_match(provided: str, actual: str, threshold: float = 0.8, field_name: str = "default") -> bool:
    """Simplified fuzzy matching wrapper for backward compatibility."""
    if not provided or not actual:
        return False
    result = _fuzzy_match_comprehensive(provided, actual, field_name)
    return result["matched"]


async def transfer_to_agent(agent_name: str, context: RunContext_T, silent: bool = False) -> tuple[Agent, str] | Agent:
    """
    Transfer to another agent by name.

    Args:
        agent_name: Target agent name
        context: Current run context
        silent: If True, current agent doesn't speak (returns agent only)

    Returns:
        Agent instance (silent) or (Agent, str) tuple (announced)
    """
    userdata = context.userdata
    current_agent = context.session.current_agent

    if agent_name not in userdata.agents:
        raise ValueError(f"Agent '{agent_name}' not found in available agents: {list(userdata.agents.keys())}")

    next_agent = userdata.agents[agent_name]
    userdata.prev_agent = current_agent

    return next_agent if silent else (next_agent, f"Transferring to {agent_name}.")


def validate_business_hours(date_str: str, time_str: str) -> tuple[bool, str]:
    """Validate callback date/time is within business hours."""
    try:
        callback_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        callback_time = datetime.strptime(time_str, "%H:%M").time()

        if callback_date < date.today():
            return False, "Callback date must be in the future"

        start = BUSINESS_HOURS["start"]
        end = BUSINESS_HOURS["end"]
        if not (start <= callback_time <= end):
            return False, f"Callback time must be between {start.strftime('%H:%M')} and {end.strftime('%H:%M')}"

        if callback_date.weekday() not in BUSINESS_HOURS["days"]:
            return False, "Callback date must be on a business day (Mon-Sat)"

        return True, ""
    except ValueError as e:
        return False, f"Invalid date/time format: {str(e)}"


@function_tool()
async def schedule_callback(
    date: Annotated[str, Field(description="Callback date in YYYY-MM-DD format (e.g., '2025-12-15')")],
    time: Annotated[str, Field(description="Callback time in HH:MM format (e.g., '14:30')")],
    context: RunContext_T,
) -> tuple[Agent, str] | Agent | str:
    """
    Schedule a callback for the customer.

    Validates business hours and transfers to closing.

    Usage: Call when customer requests callback or is unavailable now.
    """
    userdata = context.userdata

    is_valid, error_msg = validate_business_hours(date, time)
    if not is_valid:
        start = BUSINESS_HOURS["start"].strftime("%H:%M")
        end = BUSINESS_HOURS["end"].strftime("%H:%M")
        return f"Cannot schedule callback: {error_msg}. Please provide a valid date and time during business hours (Mon-Sat, {start}-{end})."

    userdata.call.callback_scheduled = True
    userdata.call.callback_datetime = f"{date}T{time}"
    userdata.call.call_outcome = CallOutcome.CALLBACK

    return await transfer_to_agent("closing", context)


@function_tool()
async def escalate(
    reason: Annotated[
        Literal["customer_request", "complex_issue", "payment_dispute", "technical_issue", "aggressive_customer"],
        Field(description="Reason for escalation")
    ],
    notes: Annotated[str, Field(description="Detailed notes about why escalation is needed")],
    context: RunContext_T,
) -> tuple[Agent, str] | Agent:
    """
    Escalate the call to a supervisor or specialist.

    Usage: Call when situation requires human intervention or supervisor authority.
    """
    userdata = context.userdata

    userdata.call.escalation_reason = reason
    userdata.call.escalation_notes = notes
    userdata.call.call_outcome = CallOutcome.ESCALATION

    return await transfer_to_agent("closing", context)


@function_tool()
async def handle_cancellation_request(
    contract_id: Annotated[str, Field(description="Contract or account ID for cancellation request")],
    reason: Annotated[str, Field(description="Customer's reason for wanting to cancel")],
    context: RunContext_T,
) -> tuple[Agent, str] | Agent:
    """
    Log cancellation request and create support ticket.

    Usage: Call when customer requests to cancel their Cartrack subscription.
    This creates a ticket for the cancellations team - do not cancel immediately.
    """
    userdata = context.userdata

    ticket_id = f"CXL{random.randint(100000, 999999)}"

    userdata.call.cancellation_requested = True
    userdata.call.cancellation_ticket_id = ticket_id
    userdata.call.append_call_notes(f"Cancellation request - Contract: {contract_id}, Reason: {reason}, Ticket: {ticket_id}")

    return await transfer_to_agent("closing", context)

@function_tool()
async def end_call(
    outcome: Annotated[
        Literal[
            "ptp_committed",
            "settlement_committed",
            "installment_committed",
            "callback_scheduled",
            "wrong_person",
            "third_party",
            "customer_refused",
            "escalated",
            "verification_failed",
            "customer_disconnected",
        ],
        Field(description="Call outcome/disposition code")
    ],
    context: RunContext_T,
    notes: Annotated[Optional[str], Field(description="Additional notes about the call")] = None,
) -> Optional[str]:
    """
    End the call with specified outcome and disconnect all participants.

    This is the final tool call in the workflow. After calling this,
    the room will be deleted and all participants disconnected.

    Usage: Call when the conversation is complete and ready to end.
    """
    userdata = context.userdata
    call = userdata.call

    # Record call outcome
    call.call_outcome = outcome
    if notes:
        call.append_call_notes(notes)
    call.append_call_notes(f"Call ended with outcome: {outcome}")

    # In test mode (no job_context), just record outcome and return
    if not userdata.job_context:
        return f"Call ended with outcome: {outcome} (test mode - no room to disconnect)"

    # Get room name from JobContext
    room_name = userdata.job_context.job.room.name

    try:
        # Initialize LiveKit API client
        api_client = api.LiveKitAPI(
            os.getenv("LIVEKIT_URL"),
            os.getenv("LIVEKIT_API_KEY"),
            os.getenv("LIVEKIT_API_SECRET"),
        )

        # Wait 1 second to allow any pending speech to complete
        await asyncio.sleep(1.0)

        # Delete the room (disconnects all participants)
        await api_client.room.delete_room(api.DeleteRoomRequest(
            room=room_name,
        ))

        return None

    except Exception as e:
        raise ToolError(f"Failed to end call: {str(e)}")