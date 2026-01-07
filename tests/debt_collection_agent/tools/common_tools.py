"""Common tools for multiple agents."""

from typing import Annotated, Literal

from pydantic import Field
from livekit.agents.llm import function_tool
from livekit.agents.voice import Agent, RunContext

from shared_state import UserData
from state.types import CallOutcome

RunContext_T = RunContext[UserData]


async def transfer_to_agent(agent_name: str, context: RunContext_T, silent: bool = False):
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


@function_tool()
async def schedule_callback(
    date: Annotated[str, Field(description="Callback date in YYYY-MM-DD format (e.g., '2025-12-15')")],
    time: Annotated[str, Field(description="Callback time in HH:MM format (e.g., '14:30')")],
    context: RunContext_T,
):
    """
    Schedule a callback for the customer.

    Usage: Call when customer requests callback or is unavailable now.
    """
    userdata = context.userdata

    userdata.call.callback_scheduled = True
    userdata.call.callback_datetime = f"{date}T{time}"
    userdata.call.call_outcome = CallOutcome.CALLBACK
    userdata.call.add_note(f"Callback scheduled for {date} at {time}")

    return await transfer_to_agent("closing", context)


@function_tool()
async def escalate(
    reason: Annotated[
        Literal["customer_request", "complex_issue", "payment_dispute", "technical_issue"],
        Field(description="Reason for escalation")
    ],
    notes: Annotated[str, Field(description="Detailed notes about why escalation is needed")],
    context: RunContext_T,
):
    """
    Escalate the call to a supervisor or specialist.

    Usage: Call when situation requires human intervention or supervisor authority.
    """
    userdata = context.userdata

    userdata.call.escalation_reason = reason
    userdata.call.escalation_notes = notes
    userdata.call.call_outcome = CallOutcome.ESCALATION
    userdata.call.add_note(f"Escalated: {reason} - {notes}")

    return await transfer_to_agent("closing", context)


@function_tool()
async def end_call(
    outcome: Annotated[
        Literal["success", "callback", "refusal", "cancelled"],
        Field(description="Final call outcome")
    ],
    context: RunContext_T,
) -> str:
    """
    End the call with a specific outcome.

    Usage: Call when conversation is complete and call should be terminated.
    """
    userdata = context.userdata

    outcome_map = {
        "success": CallOutcome.SUCCESS,
        "callback": CallOutcome.CALLBACK,
        "refusal": CallOutcome.REFUSAL,
        "cancelled": CallOutcome.CANCELLED,
    }

    userdata.call.call_outcome = outcome_map[outcome]
    userdata.call.add_note(f"Call ended with outcome: {outcome}")

    return f"Call ended with outcome: {outcome}. Thank you for your time."
