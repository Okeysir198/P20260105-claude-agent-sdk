"""Simulation workflow - LLM-powered user conversations with memory."""

import time
import uuid
from pathlib import Path
from typing import Optional, Annotated, Literal

import yaml
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.func import entrypoint
from langgraph.config import get_stream_writer
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

from ..core.config import get_eval_dir, get_config, ConfigurationError
from ..core.session import TestSession
from ..schemas.models import SimulationResult, Turn, EventType


def load_simulation_config(config_path: Optional[str] = None) -> dict:
    """Load simulation config from YAML file."""
    if config_path:
        path = Path(config_path)
    else:
        path = get_eval_dir() / "simulated_user_config.yaml"

    if path.exists():
        return yaml.safe_load(path.read_text())
    return {}


def get_preset(config: dict, preset_name: str) -> dict:
    """Get persona preset from config."""
    presets = config.get("presets", {})
    return presets.get(preset_name, {})


def should_stop(message: str, stop_phrases: list[str]) -> bool:
    """Check if message contains stop phrases."""
    message_lower = message.lower()
    return any(phrase.lower() in message_lower for phrase in stop_phrases)


class SimulatedUserState(TypedDict):
    """State for simulated user with memory."""
    messages: Annotated[list[BaseMessage], add_messages]
    system_prompt: str


# Create checkpointer for simulated user memory
_simulated_user_checkpointer = InMemorySaver()


def create_simulated_user_agent(
    model_name: str,
    model_provider: str,
    temperature: float,
    system_prompt: str,
    debtor_profile: dict,
):
    """Create a simulated user agent graph with memory.

    Returns a compiled LangGraph with memory enabled.
    """
    # Build system prompt with debtor profile info
    profile_system_prompt = f"""{system_prompt}

Your profile information:
- Name: {debtor_profile.get('full_name', 'Unknown')}
- User ID: {debtor_profile.get('user_id', 'Unknown')}
- Username: {debtor_profile.get('username', 'Unknown')}
- ID number: {debtor_profile.get('id_number', 'Unknown')}
- Birthday: {debtor_profile.get('birth_date', 'Unknown')}
- Email: {debtor_profile.get('email', 'Unknown')}
- Contact number: {debtor_profile.get('contact_number', 'Unknown')}
- Residential address: {debtor_profile.get('residential_address', 'Unknown')}
- Vehicle registration: {debtor_profile.get('vehicle_registration', 'Unknown')}
- Vehicle make: {debtor_profile.get('vehicle_make', 'Unknown')}
- Vehicle model: {debtor_profile.get('vehicle_model', 'Unknown')}
- Vehicle color: {debtor_profile.get('vehicle_color', 'Unknown')}
- Outstanding amount: R{debtor_profile.get('outstanding_amount', 0)}
- Overdue days: {debtor_profile.get('overdue_days', 0)}
- Account status: {debtor_profile.get('account_status', 'Unknown')}
- Monthly subscription: R{debtor_profile.get('monthly_subscription', 0)}
- Cancellation fee: R{debtor_profile.get('cancellation_fee', 0)}
- Salary date: {debtor_profile.get('salary_date', 'Unknown')}
- Bank name: {debtor_profile.get('bank_name', 'Unknown')}
- Bank account number: {debtor_profile.get('bank_account_number', 'Unknown')}
"""

    # Create LLM for simulated user
    model = init_chat_model(
        model=model_name,
        model_provider=model_provider,
        temperature=temperature,
    )

    # Define the node that generates responses
    async def generate_response(state: SimulatedUserState) -> SimulatedUserState:
        """Generate a response based on the conversation history."""
        # Get the last message (should be from agent)
        messages = state["messages"]

        # Build message list with system prompt
        all_messages = [SystemMessage(content=state["system_prompt"])] + messages

        # Generate response
        response = await model.ainvoke(all_messages)

        return {"messages": [response]}

    # Build the graph
    builder = StateGraph(SimulatedUserState)
    builder.add_node("generate_response", generate_response)
    builder.add_edge(START, "generate_response")
    builder.add_edge("generate_response", END)

    # Compile with checkpointer for memory
    graph = builder.compile(checkpointer=_simulated_user_checkpointer)

    return graph, profile_system_prompt


@entrypoint(checkpointer=_simulated_user_checkpointer)
async def simulation_workflow(
    sim_config: dict,
) -> SimulationResult:
    """Run a simulated user conversation with memory.

    Args:
        sim_config: Config dict with model, max_turns, start_agent, system_prompt, etc.
            Runtime config from EvalRunner is included as _runtime_* keys.
    """
    start_time = time.time()
    writer = get_stream_writer()

    # Working config dict
    cfg = dict(sim_config)

    # Load base config if not provided
    base_config = load_simulation_config(cfg.get("config_path"))

    # Apply preset if specified
    preset_name = cfg.get("preset") or cfg.get("persona")
    if preset_name:
        preset = get_preset(base_config, preset_name)
        cfg = {**base_config, **preset, **cfg}
    else:
        cfg = {**base_config, **cfg}

    # Load eval config for defaults (strict - no silent fallbacks)
    eval_config = get_config()

    # Extract runtime config from EvalRunner (already resolved with version)
    runtime_model = cfg.get("_runtime_model")
    runtime_temperature = cfg.get("_runtime_temperature")
    runtime_version = cfg.get("_runtime_version")
    runtime_test_data = cfg.get("_runtime_test_data", {})

    # Extract simulation settings
    simulation_cfg = cfg.get("simulation", {})
    max_turns = cfg.get("max_turns") or simulation_cfg.get("max_turns", 20)
    stop_phrases = cfg.get("stop_phrases") or simulation_cfg.get(
        "stop_phrases", ["goodbye", "bye", "have a good day"]
    )

    # Agent settings
    agent_cfg = cfg.get("agent", simulation_cfg)
    start_agent = cfg.get("start_agent") or agent_cfg.get("start_agent") or eval_config.default_agent

    # Agent model - priority: runtime > sim_config > agent_cfg
    if runtime_model is not None:
        agent_model = runtime_model
    else:
        agent_model = cfg.get("agent_model") or agent_cfg.get("model")
        if not agent_model:
            agent_model = eval_config.resolve_model(version=runtime_version)

    # Agent temperature
    if runtime_temperature is not None:
        agent_temperature = runtime_temperature
    else:
        agent_temperature = cfg.get("agent_temperature") or agent_cfg.get("temperature")
        if agent_temperature is None:
            agent_temperature = eval_config.resolve_temperature(version=runtime_version)

    # Persona settings
    persona_cfg = cfg.get("persona", {})
    persona_name = cfg.get("persona_name") or cfg.get("name") or persona_cfg.get("name", "Simulated User")
    system_prompt = cfg.get("system_prompt") or persona_cfg.get(
        "system_prompt",
        "You are simulating a user in a phone call. Respond naturally and briefly.",
    )
    initial_message = cfg.get("initial_message") or persona_cfg.get("initial_message", "Hello?")

    # Simulated user LLM settings
    model_cfg = cfg.get("model", {})
    if isinstance(model_cfg, dict):
        model_name = model_cfg.get("name") or runtime_model or eval_config.resolve_model(version=runtime_version)
        model_provider = model_cfg.get("provider", "openai")
        model_temperature = model_cfg.get("temperature", 0.7)
    else:
        model_name = model_cfg or runtime_model or eval_config.resolve_model(version=runtime_version)
        model_provider = cfg.get("model_provider", "openai")
        model_temperature = cfg.get("temperature", 0.7)

    # Get debtor profile from test data
    debtor_profile = runtime_test_data.get("debtor", {})

    # Create simulated user agent graph with profile info
    user_graph, profile_system_prompt = create_simulated_user_agent(
        model_name=model_name,
        model_provider=model_provider,
        temperature=model_temperature,
        system_prompt=system_prompt,
        debtor_profile=debtor_profile,
    )

    # Create thread for this simulation (enables memory)
    thread_id = str(uuid.uuid4())
    thread_config: RunnableConfig = {"configurable": {"thread_id": thread_id}}

    # Initialize state with system prompt
    await user_graph.ainvoke(
        {"messages": [], "system_prompt": profile_system_prompt},
        thread_config
    )

    turns: list[Turn] = []
    stop_reason = "max_turns"
    error = None
    goal_achieved = False

    writer({
        "event": "simulation_started",
        "persona": persona_name,
        "max_turns": max_turns,
        "thread_id": thread_id,
        "agent_config": {
            "model": agent_model,
            "temperature": agent_temperature,
        },
        "simulated_user_config": {
            "model": model_name,
            "temperature": model_temperature,
        },
    })

    try:
        async with TestSession(
            start_agent=start_agent,
            model=agent_model,
            temperature=agent_temperature,
            test_data=runtime_test_data,
            version=runtime_version,
        ) as session:
            # Get initial greeting
            greeting = session.get_initial_greeting()

            if greeting:
                turns.append(
                    Turn(
                        turn_number=0,
                        user_input="[session_start]",
                        agent_response=greeting,
                        events=[],
                    )
                )
                writer({"event": "agent_response", "turn": 0, "content": greeting})

                # Check if greeting ends conversation
                if should_stop(greeting, stop_phrases):
                    stop_reason = "agent_ended"
                else:
                    # Generate first user response with memory
                    result = await user_graph.ainvoke(
                        {"messages": [HumanMessage(content=greeting)]},
                        thread_config
                    )
                    user_response = result["messages"][-1].content
            else:
                # No greeting - use initial message
                user_response = initial_message

            # Main conversation loop
            turn_num = 0
            while turn_num < max_turns and stop_reason == "max_turns":
                turn_num += 1

                # Check if user response ends conversation
                if should_stop(user_response, stop_phrases):
                    turns.append(
                        Turn(
                            turn_number=turn_num,
                            user_input=user_response,
                            agent_response="",
                            events=[],
                        )
                    )
                    stop_reason = "user_ended"
                    break

                # Stream user input
                writer({"event": "user_input", "turn": turn_num, "content": user_response})

                # Send to agent and stream events in real-time
                all_events = []
                agent_response_text = None

                async for event in session.send_message_stream(user_response):
                    # Stream each event immediately as it happens
                    writer({
                        "event": "turn_event",
                        "turn": turn_num,
                        "type": event.type.value,
                        "content": event.content
                    })
                    all_events.append(event)

                    # Track the agent response text
                    if event.type == EventType.AGENT_MESSAGE:
                        agent_response_text = event.content.get("text", "")

                # Extract response text from events if not already set
                if not agent_response_text:
                    agent_response_text = " ".join(
                        e.content.get("text", "")
                        for e in all_events
                        if e.type == EventType.AGENT_MESSAGE
                    )

                turns.append(
                    Turn(
                        turn_number=turn_num,
                        user_input=user_response,
                        agent_response=agent_response_text,
                        events=all_events,
                    )
                )

                # Stream agent response
                writer({"event": "agent_response", "turn": turn_num, "content": agent_response_text})

                # Check if agent ends conversation
                if should_stop(agent_response_text, stop_phrases):
                    stop_reason = "agent_ended"
                    break

                # Generate next user response (agent graph has memory of previous turns)
                result = await user_graph.ainvoke(
                    {"messages": [HumanMessage(content=agent_response_text)]},
                    thread_config
                )
                user_response = result["messages"][-1].content

    except Exception as e:
        error = str(e)
        stop_reason = "error"

    writer({"event": "simulation_completed", "turns": len(turns), "stop_reason": stop_reason})

    duration_ms = (time.time() - start_time) * 1000

    return SimulationResult(
        turns=turns,
        total_turns=len(turns),
        duration_ms=duration_ms,
        stop_reason=stop_reason,
        error=error,
        test_name=f"Simulation: {persona_name}",
        metadata={"config": cfg},
        persona=persona_name,
        goal_achieved=goal_achieved,
    )
