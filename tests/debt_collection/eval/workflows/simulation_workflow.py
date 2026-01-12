"""Simulation workflow - LLM-powered user conversations."""

import asyncio
import time
from pathlib import Path
from typing import Optional

import yaml
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.func import entrypoint, task
from langgraph.config import get_stream_writer

from ..core.config import get_eval_dir, get_config, ConfigurationError
from ..core.session import TestSession
from ..schemas.models import SimulationResult, Turn

# Import shared checkpointer and thread_config from test_workflow
from .test_workflow import checkpointer, thread_config


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


@task
async def generate_user_response(
    model,
    history: list[dict],
    agent_message: str,
    system_prompt: str,
) -> str:
    """Generate simulated user response using LLM."""
    messages = [SystemMessage(content=system_prompt)]

    for msg in history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))

    # Add the latest agent message
    messages.append(AIMessage(content=agent_message))

    response = await model.ainvoke(messages)
    return response.content


@entrypoint(checkpointer=checkpointer)
async def simulation_workflow(
    sim_config: dict,
) -> SimulationResult:
    """Run a simulated user conversation.

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
    # These have priority over sim_config settings
    runtime_model = cfg.get("_runtime_model")
    runtime_temperature = cfg.get("_runtime_temperature")
    runtime_version = cfg.get("_runtime_version")

    # Extract settings - handle both flat and nested config structures
    # Simulation settings
    simulation_cfg = cfg.get("simulation", {})
    max_turns = cfg.get("max_turns") or simulation_cfg.get("max_turns", 20)
    stop_phrases = cfg.get("stop_phrases") or simulation_cfg.get(
        "stop_phrases", ["goodbye", "bye", "have a good day"]
    )

    # Agent settings - use eval_config defaults (strict)
    agent_cfg = cfg.get("agent", {})
    start_agent = cfg.get("start_agent") or agent_cfg.get("start_agent") or eval_config.default_agent

    # Agent model - priority: runtime (from EvalRunner) > sim_config > agent_cfg
    # Runtime values are already resolved with version by EvalRunner
    if runtime_model is not None:
        agent_model = runtime_model
    else:
        agent_model = cfg.get("agent_model") or agent_cfg.get("model")
        if not agent_model:
            # Use eval_config.resolve_model with version for strict resolution
            agent_model = eval_config.resolve_model(version=runtime_version)

    # Agent temperature - same priority
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
    initial_message = cfg.get("initial_message") or persona_cfg.get("initial_message")

    # Simulated user LLM settings - handle nested model config
    # Use runtime model as default for simulated user too (same model for agent and user)
    model_cfg = cfg.get("model", {})
    if isinstance(model_cfg, dict):
        # Use runtime model if available, otherwise resolve with version
        model_name = model_cfg.get("name") or runtime_model or eval_config.resolve_model(version=runtime_version)
        model_provider = model_cfg.get("provider", "openai")
        model_temperature = model_cfg.get("temperature", 0.7)
    else:
        model_name = model_cfg or runtime_model or eval_config.resolve_model(version=runtime_version)
        model_provider = cfg.get("model_provider", "openai")
        model_temperature = cfg.get("temperature", 0.7)

    # Create LLM for simulated user
    model = init_chat_model(
        model=model_name,
        model_provider=model_provider,
        temperature=model_temperature,
    )

    turns: list[Turn] = []
    history: list[dict] = []
    stop_reason = "max_turns"
    error = None
    goal_achieved = False

    writer({
        "event": "simulation_started",
        "persona": persona_name,
        "max_turns": max_turns,
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
                history.append({"role": "assistant", "content": greeting})
                writer({"event": "agent_response", "turn": 0, "content": greeting})

                # Check if greeting ends conversation
                if should_stop(greeting, stop_phrases):
                    stop_reason = "agent_ended"
                else:
                    # Generate first user response
                    user_response = await generate_user_response(
                        model, history, greeting, system_prompt
                    )
            else:
                # No greeting - use initial message
                user_response = initial_message or "Hello"

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

                # Send to agent
                agent_response, events = await session.send_message(user_response)

                turns.append(
                    Turn(
                        turn_number=turn_num,
                        user_input=user_response,
                        agent_response=agent_response,
                        events=events,
                    )
                )

                # Stream events (tool calls, outputs, handoffs)
                for event in events:
                    writer({
                        "event": "turn_event",
                        "turn": turn_num,
                        "type": event.type.value,
                        "content": event.content
                    })

                # Stream agent response
                writer({"event": "agent_response", "turn": turn_num, "content": agent_response})

                history.append({"role": "user", "content": user_response})
                history.append({"role": "assistant", "content": agent_response})

                # Check if agent ends conversation
                if should_stop(agent_response, stop_phrases):
                    stop_reason = "agent_ended"
                    break

                # Generate next user response
                user_response = await generate_user_response(
                    model, history, agent_response, system_prompt
                )

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
