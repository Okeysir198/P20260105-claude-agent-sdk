"""Test workflow - runs test cases through agents."""

import time
import uuid
from typing import Optional

from langgraph.func import entrypoint
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.config import get_stream_writer

from ..core.config import ConfigurationError
from ..core.session import TestSession
from ..schemas.models import Turn, TestResult


class LLMResponseError(Exception):
    """Raised when LLM returns empty response (typically due to API errors)."""
    pass

checkpointer = InMemorySaver()


def thread_config(thread_id: Optional[str] = None) -> dict:
    """Create config dict for workflow invocation.

    Args:
        thread_id: Optional thread ID (generates UUID if not provided)
    """
    return {"configurable": {"thread_id": thread_id or str(uuid.uuid4())}}


@entrypoint(checkpointer=checkpointer)
async def test_workflow(test_case: dict) -> TestResult:
    """Run a test case through the agent.

    Args:
        test_case: Dict with 'name', 'turns', and runtime options from EvalRunner:
            - _runtime_model: LLM model (REQUIRED - set by EvalRunner)
            - _runtime_temperature: LLM temperature (REQUIRED - set by EvalRunner)
            - _runtime_start_agent: Starting agent ID
            - _runtime_version: Agent version to use

    Raises:
        ConfigurationError: If model or temperature not provided
        LLMResponseError: If LLM returns empty response (API error)
    """
    start_time = time.time()
    writer = get_stream_writer()

    # Extract runtime options from input (LangGraph entrypoints only accept one input)
    # STRICT: No fallbacks - model and temperature must be set by EvalRunner
    model = test_case.get("_runtime_model")
    temperature = test_case.get("_runtime_temperature")

    if model is None:
        raise ConfigurationError(
            "Model not provided in test case. "
            "Use EvalRunner to run tests (it resolves config automatically)."
        )
    if temperature is None:
        raise ConfigurationError(
            "Temperature not provided in test case. "
            "Use EvalRunner to run tests (it resolves config automatically)."
        )

    start_agent = test_case.get("_runtime_start_agent")
    version = test_case.get("_runtime_version")

    test_name = test_case.get("name", "Unknown")
    target_agent = start_agent or test_case.get("_sub_agent_id") or test_case.get("agent")
    turns_data = test_case.get("turns", [])
    test_data = test_case.get("_default_test_data", {})

    writer({"event": "started", "test_name": test_name, "model": model, "temperature": temperature})

    turns: list[Turn] = []
    error = None
    stop_reason = "completed"

    try:
        async with TestSession(
            start_agent=target_agent,
            model=model,
            temperature=temperature,
            test_data=test_data,
            version=version
        ) as session:
            # Get initial greeting (Turn 0)
            greeting = session.get_initial_greeting()
            if greeting:
                turns.append(Turn(
                    turn_number=0,
                    user_input="[session_start]",
                    agent_response=greeting,
                    events=[]
                ))
                writer({"event": "agent_response", "turn": 0, "content": greeting})

            # Process each turn
            for i, turn_data in enumerate(turns_data, 1):
                user_input = turn_data.get("user_input", "")
                writer({"event": "user_input", "turn": i, "content": user_input})

                response, events = await session.send_message(user_input)

                # STRICT: Validate LLM actually returned a response
                # Empty response typically means API error (wrong model, auth failure, etc.)
                if not response or not response.strip():
                    raise LLMResponseError(
                        f"LLM returned empty response for turn {i}. "
                        f"This typically indicates an API error (invalid model, auth failure, etc.). "
                        f"Model: {model}, Temperature: {temperature}"
                    )

                turns.append(Turn(
                    turn_number=i,
                    user_input=user_input,
                    agent_response=response,
                    events=events
                ))

                # Stream each event
                for event in events:
                    writer({
                        "event": "turn_event",
                        "turn": i,
                        "type": event.type.value,
                        "content": event.content
                    })

                # Stream full agent response
                writer({"event": "agent_response", "turn": i, "content": response})

    except Exception as e:
        error = str(e)
        stop_reason = "error"

    writer({"event": "completed", "total_turns": len(turns)})

    duration_ms = (time.time() - start_time) * 1000

    return TestResult(
        turns=turns,
        total_turns=len(turns),
        duration_ms=duration_ms,
        stop_reason=stop_reason,
        error=error,
        test_name=test_name,
        metadata={"test_case": test_case}
    )
