"""Configuration loading for the simulated user.

Handles loading configuration from YAML files with fallback to defaults,
and merging runtime CLI overrides.
"""

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class SimulatedUserConfig:
    """Configuration for the simulated user.

    Attributes:
        model_provider: LLM provider (e.g., "openai", "anthropic").
        model: Model identifier for the simulated user.
        temperature: Sampling temperature for response generation.
        max_tokens: Maximum tokens per response.
        persona_name: Display name for the simulated user.
        system_prompt: System prompt defining user behavior.
        persona_traits: List of personality traits for the simulated user.
        initial_message: Optional first message to start the conversation.
        max_turns: Maximum conversation turns before stopping.
        stop_phrases: Phrases that indicate conversation should end.
        goal_description: Description of what the simulated user is trying to achieve.
        start_agent: Which agent to start the conversation with.
        agent_model: Optional model override for the agent being tested.
        verbose: Whether to print detailed output during simulation.
        show_tool_calls: Whether to display tool calls in output.
    """

    model_provider: str = "openai"
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 500
    persona_name: str = "Simulated User"
    system_prompt: str = ""
    persona_traits: list[str] = field(default_factory=list)
    initial_message: Optional[str] = None
    max_turns: int = 20
    stop_phrases: list[str] = field(
        default_factory=lambda: [
            "bye",
            "goodbye",
            "good bye",
            "have a good day",
            "thank you for your time",
        ]
    )
    goal_description: Optional[str] = None
    start_agent: str = "introduction"
    agent_model: Optional[str] = None
    verbose: bool = True
    show_tool_calls: bool = True


def _get_default_config_path() -> Path:
    """Get the default config file path in the eval/ directory."""
    return Path(__file__).parent.parent / "simulated_user_config.yaml"


def load_config(config_path: Path | str | None = None) -> SimulatedUserConfig:
    """Load configuration from a YAML file.

    Args:
        config_path: Path to YAML config file. If None, uses default location.
                    Falls back to defaults if file doesn't exist.

    Returns:
        SimulatedUserConfig with loaded or default values.

    The YAML structure supports nested sections that get flattened:
        model:
            provider: openai
            model: gpt-4o-mini
            temperature: 0.7
            max_tokens: 500
        persona:
            name: "Simulated User"
            system_prompt: "..."
            traits: [...]
            initial_message: "..."
            goal_description: "..."
        simulation:
            max_turns: 20
            stop_phrases: [...]
        agent:
            start_agent: introduction
            model: null
        output:
            verbose: true
            show_tool_calls: true
    """
    if config_path is None:
        config_path = _get_default_config_path()
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        return SimulatedUserConfig()

    with open(config_path) as f:
        raw = yaml.safe_load(f) or {}

    # Flatten nested structure into dataclass fields
    model_section = raw.get("model", {})
    persona_section = raw.get("persona", {})
    simulation_section = raw.get("simulation", {})
    agent_section = raw.get("agent", {})
    output_section = raw.get("output", {})

    config_dict = {}

    # Model section
    if "provider" in model_section:
        config_dict["model_provider"] = model_section["provider"]
    if "model" in model_section:
        config_dict["model"] = model_section["model"]
    if "temperature" in model_section:
        config_dict["temperature"] = model_section["temperature"]
    if "max_tokens" in model_section:
        config_dict["max_tokens"] = model_section["max_tokens"]

    # Persona section
    if "name" in persona_section:
        config_dict["persona_name"] = persona_section["name"]
    if "system_prompt" in persona_section:
        config_dict["system_prompt"] = persona_section["system_prompt"]
    if "traits" in persona_section:
        config_dict["persona_traits"] = persona_section["traits"]
    if "initial_message" in persona_section:
        config_dict["initial_message"] = persona_section["initial_message"]
    if "goal_description" in persona_section:
        config_dict["goal_description"] = persona_section["goal_description"]

    # Simulation section
    if "max_turns" in simulation_section:
        config_dict["max_turns"] = simulation_section["max_turns"]
    if "stop_phrases" in simulation_section:
        config_dict["stop_phrases"] = simulation_section["stop_phrases"]

    # Agent section
    if "start_agent" in agent_section:
        config_dict["start_agent"] = agent_section["start_agent"]
    if "model" in agent_section:
        config_dict["agent_model"] = agent_section["model"]

    # Output section
    if "verbose" in output_section:
        config_dict["verbose"] = output_section["verbose"]
    if "show_tool_calls" in output_section:
        config_dict["show_tool_calls"] = output_section["show_tool_calls"]

    return SimulatedUserConfig(**config_dict)


def merge_runtime_config(
    base: SimulatedUserConfig,
    overrides: dict,
) -> SimulatedUserConfig:
    """Merge runtime CLI overrides into base configuration.

    Args:
        base: Base configuration to start from.
        overrides: Dictionary of field names to override values.
                  Keys should match SimulatedUserConfig field names.
                  None values are ignored.

    Returns:
        New SimulatedUserConfig with overrides applied.
    """
    # Filter out None values - only apply explicit overrides
    filtered = {k: v for k, v in overrides.items() if v is not None}

    if not filtered:
        return base

    return replace(base, **filtered)
