"""
Main simulation loop using LangGraph Functional API.

This module provides the entrypoint for running simulated user conversations
with LiveKit voice agents. It uses LangGraph's @entrypoint and @task decorators
for workflow orchestration with checkpointing support.
"""

import asyncio
import uuid
from dataclasses import asdict
from typing import Optional

from langgraph.func import entrypoint, task
from langgraph.checkpoint.memory import InMemorySaver

from .types import SimulationResult, SimulationTurn, TurnEvent
from .config import SimulatedUserConfig, load_config, merge_runtime_config
from .user_agent import SimulatedUserAgent
from .session_runner import AgentSessionRunner
from .console import SimulationConsole

# Shared checkpointer for workflow state persistence
checkpointer = InMemorySaver()


@task
async def generate_user_response(
    user_agent: SimulatedUserAgent,
    agent_message: str,
    runtime_config: Optional[dict] = None,
) -> str:
    """Task: Generate simulated user response to an agent message.

    Args:
        user_agent: The simulated user agent instance.
        agent_message: The agent's message to respond to.
        runtime_config: Optional runtime configuration overrides.

    Returns:
        The simulated user's response text.
    """
    return await user_agent.generate_response(agent_message, runtime_config)


@task
async def process_agent_turn(
    session_runner: AgentSessionRunner,
    user_input: str,
) -> tuple[str, list[TurnEvent]]:
    """Task: Process user input through the agent session.

    Args:
        session_runner: The agent session runner instance.
        user_input: The user's message to send to the agent.

    Returns:
        Tuple of (agent_response_text, list_of_events).
    """
    return await session_runner.send_message(user_input)


@entrypoint(checkpointer=checkpointer)
async def run_simulation(
    config: SimulatedUserConfig,
    runtime_overrides: Optional[dict] = None,
) -> SimulationResult:
    """
    Main simulation entrypoint using LangGraph Functional API.

    Orchestrates the conversation between a simulated user and a LiveKit agent.
    The simulation continues until one of these conditions is met:
    - Maximum turns reached
    - User message contains a stop phrase
    - Agent message contains a stop phrase
    - An error occurs

    Args:
        config: Configuration for the simulation.
        runtime_overrides: Optional dictionary of runtime overrides.

    Returns:
        SimulationResult with all turns, stop reason, and metadata.
    """
    # Merge runtime overrides into config
    if runtime_overrides:
        config = merge_runtime_config(config, runtime_overrides)

    # Initialize components
    user_agent = SimulatedUserAgent(config)
    console = SimulationConsole(config)
    turns: list[SimulationTurn] = []
    turn = 0
    stop_reason = "max_turns"
    error = None

    console.print_header(config)

    try:
        async with AgentSessionRunner(
            start_agent=config.start_agent,
            model=config.agent_model,
        ) as session:

            # Get initial agent greeting (from on_enter)
            initial_greeting = session.get_initial_greeting()

            if initial_greeting:
                console.print_agent_message(initial_greeting, turn=0)

                # Record initial turn (turn 0 - agent speaks first)
                turns.append(
                    SimulationTurn(
                        turn_number=0,
                        user_message="[session_start]",
                        agent_response=initial_greeting,
                        events=[],
                    )
                )

                # Generate first user response to the greeting
                user_response = await generate_user_response(
                    user_agent,
                    initial_greeting,
                )
            else:
                # No greeting - use initial message or default
                user_response = config.initial_message or "Hello"

            # Main simulation loop
            while turn < config.max_turns:
                turn += 1

                # Check if user response contains stop phrase before sending
                if user_agent.should_stop(user_response):
                    console.print_user_message(user_response, turn=turn)
                    turns.append(
                        SimulationTurn(
                            turn_number=turn,
                            user_message=user_response,
                            agent_response="",
                            events=[],
                        )
                    )
                    stop_reason = "user_ended"
                    break

                console.print_user_message(user_response, turn=turn)

                # Process user message through agent
                agent_response, events = await process_agent_turn(
                    session,
                    user_response,
                )

                console.print_agent_message(agent_response, turn=turn)
                console.print_events(events)

                # Record this turn
                turns.append(
                    SimulationTurn(
                        turn_number=turn,
                        user_message=user_response,
                        agent_response=agent_response,
                        events=events,
                    )
                )

                # Check if agent response contains stop phrase
                if user_agent.should_stop(agent_response):
                    stop_reason = "agent_ended"
                    break

                # Generate next user response
                user_response = await generate_user_response(
                    user_agent,
                    agent_response,
                )

    except Exception as e:
        error = str(e)
        stop_reason = "error"
        console.print_error(str(e))

    # Build final result
    result = SimulationResult(
        turns=turns,
        total_turns=turn,
        stop_reason=stop_reason,
        error=error,
        metadata={
            "config": asdict(config),
            "thread_id": str(uuid.uuid4()),
        },
    )

    console.print_summary(result)
    return result


async def run_simulation_async(
    config_path: Optional[str] = None,
    **overrides,
) -> SimulationResult:
    """
    Async function to run simulation with configuration file and overrides.

    Args:
        config_path: Path to YAML config file. If None, uses default.
        **overrides: Runtime overrides for config fields.

    Returns:
        SimulationResult with complete conversation data.
    """
    config = load_config(config_path)
    thread_id = str(uuid.uuid4())

    return await run_simulation.ainvoke(
        config,
        runtime_overrides=overrides if overrides else None,
        config={"configurable": {"thread_id": thread_id}},
    )


def simulate(
    config_path: Optional[str] = None,
    **overrides,
) -> SimulationResult:
    """
    Synchronous convenience function to run simulation.

    This is the main entry point for running simulations from scripts or CLI.
    It wraps the async implementation in asyncio.run().

    Args:
        config_path: Path to YAML config file. If None, uses default location.
        **overrides: Runtime overrides for config fields. Supported keys:
            - model: LLM model for simulated user
            - model_provider: LLM provider
            - temperature: Sampling temperature
            - max_turns: Maximum conversation turns
            - start_agent: Which agent to start with
            - agent_model: Model override for the agent
            - verbose: Enable verbose output
            - show_tool_calls: Show tool calls in output

    Returns:
        SimulationResult containing all turns, stop reason, and metadata.

    Example:
        # Run with defaults
        result = simulate()

        # Run with config file
        result = simulate("my_config.yaml")

        # Run with overrides
        result = simulate(max_turns=10, verbose=True)

        # Access results
        for turn in result.turns:
            print(f"User: {turn.user_message}")
            print(f"Agent: {turn.agent_response}")
    """
    config = load_config(config_path)
    thread_id = str(uuid.uuid4())

    return asyncio.run(
        run_simulation.ainvoke(
            config,
            runtime_overrides=overrides if overrides else None,
            config={"configurable": {"thread_id": thread_id}},
        )
    )


def simulate_streaming(
    config_path: Optional[str] = None,
    **overrides,
):
    """
    Generator that yields simulation updates as they occur.

    Uses LangGraph streaming to provide real-time updates during simulation.

    Args:
        config_path: Path to YAML config file.
        **overrides: Runtime overrides for config fields.

    Yields:
        Tuples of (mode, chunk) where mode indicates the stream type
        and chunk contains the update data.

    Example:
        for mode, chunk in simulate_streaming(max_turns=5):
            if mode == "updates":
                print(f"Update: {chunk}")
    """
    config = load_config(config_path)
    thread_id = str(uuid.uuid4())

    # Use stream() for real-time updates
    for chunk in run_simulation.stream(
        config,
        runtime_overrides=overrides if overrides else None,
        stream_mode="updates",
        config={"configurable": {"thread_id": thread_id}},
    ):
        yield chunk
