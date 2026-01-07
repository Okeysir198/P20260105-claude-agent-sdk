# @function_tool Design Patterns

Reference patterns for LiveKit function tools.

> **IMPORTANT**: In Python, parameters with default values must come AFTER
> parameters without defaults. Always place `context: RunContext_T` BEFORE
> any optional parameters with defaults (like `= None`).

## Basic Tool Structure

```python
from typing import Annotated
from pydantic import Field
from livekit.agents.llm import function_tool
from livekit.agents.voice import RunContext

from shared_state import UserData

# Type alias for readability
RunContext_T = RunContext[UserData]


@function_tool()
async def my_tool(
    param1: Annotated[str, Field(description="What this parameter does")],
    param2: Annotated[int, Field(description="Numeric parameter", ge=0)],
    context: RunContext_T,
) -> str:
    """
    Tool docstring becomes the LLM's understanding of when to use this tool.

    Usage: Explain when the LLM should call this tool.
    """
    userdata = context.userdata

    # Update state
    userdata.call.some_field = param1

    # Return message for LLM to speak (or None for silent)
    return f"Processed {param1}."
```

## RunContext[UserData] Parameter

Always include `context: RunContext[UserData]` to access session state:

```python
@function_tool()
async def process_data(context: RunContext_T) -> str:
    """Process current data."""
    userdata = context.userdata

    # Access profile (immutable)
    name = userdata.debtor.full_name

    # Access call state (mutable)
    userdata.call.data_processed = True
    userdata.call.add_note("Data processed successfully")

    # Access session
    current_agent = context.session.current_agent

    return "Data processed."
```

## Annotated Parameters with Field

Use `Annotated[type, Field(...)]` for parameter documentation:

```python
from typing import Annotated, Literal, Optional
from pydantic import Field

@function_tool()
async def schedule_callback(
    date: Annotated[str, Field(
        description="Callback date in YYYY-MM-DD format (e.g., '2025-12-15')"
    )],
    time: Annotated[str, Field(
        description="Callback time in HH:MM format (e.g., '14:30')"
    )],
    context: RunContext_T,
    reason: Annotated[Optional[str], Field(
        description="Optional reason for callback"
    )] = None,
) -> str:
    """Schedule a callback for the customer.

    IMPORTANT: In Python, parameters with defaults must come AFTER parameters
    without defaults. Place 'context' BEFORE any optional parameters.
    """
    ...
```

## Literal Types for Constrained Values

Use `Literal` for enumerated choices:

```python
@function_tool()
async def set_outcome(
    outcome: Annotated[
        Literal["success", "callback", "refusal", "escalation"],
        Field(description="Call outcome type")
    ],
    context: RunContext_T,
) -> str:
    """Set the call outcome."""
    userdata = context.userdata
    userdata.call.outcome = outcome
    return f"Outcome set to {outcome}."
```

## End Call Tool (REQUIRED)

**CRITICAL**: The `end_call` tool MUST delete the LiveKit room to disconnect all participants.
This is the proper pattern - always include this in common_tools.py:

```python
import asyncio
import os
from typing import Annotated, Literal, Optional

from pydantic import Field
from livekit import api
from livekit.agents.llm import function_tool, ToolError
from livekit.agents.voice import RunContext

from shared_state import UserData

RunContext_T = RunContext[UserData]


@function_tool()
async def end_call(
    outcome: Annotated[
        Literal[
            "success",
            "callback_scheduled",
            "customer_refused",
            "escalated",
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
    session = userdata.session

    # Record call outcome
    session.call_outcome = outcome
    if notes:
        session.add_note(notes)
    session.add_note(f"Call ended with outcome: {outcome}")

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

        return None  # Silent completion

    except Exception as e:
        raise ToolError(f"Failed to end call: {str(e)}")
```

**Key Points:**
1. Uses `livekit.api` to delete the room
2. Checks for test mode (no job_context) to allow eval testing
3. Waits 1 second for pending speech before disconnecting
4. Returns `None` for silent completion (no TTS after disconnect)

## Return Message for TTS

Return a string for the agent to speak:

```python
@function_tool()
async def confirm_appointment(
    date: Annotated[str, Field(description="Appointment date")],
    time: Annotated[str, Field(description="Appointment time")],
    context: RunContext_T,
) -> str:
    """Confirm an appointment."""
    userdata = context.userdata
    userdata.call.appointment_confirmed = True

    # Return message for agent to speak
    return f"Your appointment is confirmed for {date} at {time}."
```

## Agent Transfer Pattern

Return `Agent` or `tuple[Agent, str]` for handoffs:

```python
from livekit.agents.voice import Agent

@function_tool()
async def confirm_person(
    context: RunContext_T,
) -> tuple[Agent, str] | Agent:
    """
    Called when caller confirms their identity.

    Usage: Call when customer says "yes" or "that's me".
    """
    userdata = context.userdata
    userdata.call.person_confirmed = True

    # Silent handoff (next agent speaks first)
    return userdata.agents["verification"]

    # OR announced handoff (current agent speaks before transfer)
    # return (userdata.agents["verification"], "Let me verify your identity.")
```

## Transfer Helper Function

Centralize transfer logic:

```python
async def transfer_to_agent(
    agent_name: str,
    context: RunContext_T,
    silent: bool = False,
) -> tuple[Agent, str] | Agent:
    """Transfer to another agent by name."""
    userdata = context.userdata

    if agent_name not in userdata.agents:
        raise ValueError(f"Unknown agent: {agent_name}")

    next_agent = userdata.agents[agent_name]
    userdata.prev_agent = context.session.current_agent

    if silent:
        return next_agent
    return (next_agent, f"Transferring to {agent_name}.")


# Usage in tool:
@function_tool()
async def proceed_to_payment(context: RunContext_T) -> tuple[Agent, str] | Agent:
    """Proceed to payment processing."""
    userdata = context.userdata
    userdata.call.negotiation_complete = True
    return await transfer_to_agent("payment", context, silent=True)
```

## Error Handling with ToolError

Use `ToolError` for recoverable errors:

```python
from livekit.agents.llm import function_tool, ToolError

@function_tool()
async def validate_date(
    date: Annotated[str, Field(description="Date in YYYY-MM-DD format")],
    context: RunContext_T,
) -> str:
    """Validate a date."""
    try:
        parsed = datetime.strptime(date, "%Y-%m-%d")
        if parsed.date() < date.today():
            raise ToolError("Date must be in the future")
        return f"Date {date} is valid."
    except ValueError:
        raise ToolError("Invalid date format. Use YYYY-MM-DD.")
```

## Tool Registry Pattern

Centralize tool access:

```python
# tools/__init__.py

from .common_tools import schedule_callback, escalate, end_call
from .tool01_intro import confirm_person, handle_wrong_person

TOOL_REGISTRY = {
    # Common tools
    "schedule_callback": schedule_callback,
    "escalate": escalate,
    "end_call": end_call,
    # Introduction tools
    "confirm_person": confirm_person,
    "handle_wrong_person": handle_wrong_person,
}


def get_tools_by_names(tool_names: list[str], strict: bool = True) -> list:
    """Get tools from registry by name.

    Args:
        tool_names: List of tool names to retrieve
        strict: If True, raise error on missing. If False, log warning.
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
        error_msg = f"Unknown tools: {missing}"
        if strict:
            raise ValueError(error_msg)
        else:
            import logging
            logging.warning(error_msg)

    return tools
```

## Docstring Best Practices

Write clear docstrings for LLM understanding:

```python
@function_tool()
async def offer_discount(
    percentage: Annotated[int, Field(description="Discount percentage (5-25)")],
    context: RunContext_T,
) -> str:
    """
    Offer a discount to the customer.

    Usage: Call when customer is hesitant about full payment.
    Only offer if customer has not already received a discount.

    Note: Returns calculated settlement amount for agent to communicate.
    """
    ...
```

## Complete Tool Module Example

```python
"""Payment tools for the agent."""

from typing import Annotated, Optional
from pydantic import Field
from livekit.agents.llm import function_tool, ToolError
from livekit.agents.voice import RunContext

from shared_state import UserData

RunContext_T = RunContext[UserData]


@function_tool()
async def capture_payment(
    amount: Annotated[float, Field(description="Payment amount", gt=0)],
    method: Annotated[
        str,
        Field(description="Payment method: 'card', 'bank_transfer', 'debit_order'")
    ],
    context: RunContext_T,
) -> str:
    """
    Capture a payment from the customer.

    Usage: Call when customer agrees to make a payment.
    Validates amount is within acceptable range.
    """
    userdata = context.userdata

    # Validation
    max_amount = userdata.profile.outstanding_amount or 10000
    if amount > max_amount:
        raise ToolError(f"Amount exceeds maximum: {max_amount}")

    # Update state
    userdata.call.payment_captured = True
    userdata.call.payment_amount = amount
    userdata.call.payment_method = method
    userdata.call.add_note(f"Payment captured: {amount} via {method}")

    return f"Payment of {amount} captured via {method}."


@function_tool()
async def confirm_payment(
    context: RunContext_T,
) -> str:
    """
    Confirm the captured payment.

    Usage: Call after customer confirms payment details are correct.
    """
    userdata = context.userdata

    if not userdata.call.payment_captured:
        raise ToolError("No payment has been captured yet")

    userdata.call.payment_confirmed = True

    return "Payment confirmed successfully."
```
