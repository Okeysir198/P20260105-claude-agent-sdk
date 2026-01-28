"""Top-level agent definitions loader.

Loads agent configurations from agents.yaml with defaults merging.
"""
import logging
from pathlib import Path

from agent.core.yaml_utils import load_yaml_config

logger = logging.getLogger(__name__)
AGENTS_CONFIG_PATH = Path(__file__).parent.parent.parent / "agents.yaml"


def get_defaults() -> dict:
    """Return the _defaults section from agents.yaml."""
    config = load_yaml_config(AGENTS_CONFIG_PATH)
    if not config:
        return {}
    return config.get("_defaults", {})


def load_agent_config(agent_id: str | None = None) -> dict:
    """Load agent config with defaults merged.

    Args:
        agent_id: Agent ID to load. If None or invalid, uses default_agent from config.

    Returns:
        Dict with all config options (defaults + agent overrides)
    """
    config = load_yaml_config(AGENTS_CONFIG_PATH)
    if not config:
        raise ValueError("No agents.yaml configuration found")

    defaults = config.get("_defaults", {})
    agents = config.get("agents", {})

    if agent_id is None:
        agent_id = config.get("default_agent")

    # If agent_id is invalid, fall back to default agent
    if agent_id not in agents:
        default_id = config.get("default_agent")
        if default_id and default_id in agents:
            logger.warning(
                f"Agent '{agent_id}' not found. Falling back to default agent '{default_id}'. "
                f"Available agents: {list(agents.keys())}"
            )
            agent_id = default_id
        else:
            # No valid agent found - raise error
            raise ValueError(f"Agent '{agent_id}' not found. Available: {list(agents.keys())}")

    # Merge defaults with agent-specific config
    agent = agents[agent_id]
    merged = {**defaults, **agent}
    merged["agent_id"] = agent_id
    return merged


def get_default_agent_id() -> str:
    """Get the default agent ID from config."""
    config = load_yaml_config(AGENTS_CONFIG_PATH)
    if not config:
        return "general-agent-default"
    return config.get("default_agent", "general-agent-default")


def get_agents_info() -> list[dict]:
    """Get agent information for display/API responses."""
    config = load_yaml_config(AGENTS_CONFIG_PATH)
    if not config:
        return []

    default_id = config.get("default_agent")
    defaults = config.get("_defaults", {})
    agents = config.get("agents", {})

    return [
        {
            "agent_id": agent_id,
            "name": agent.get("name", agent_id),
            "description": agent.get("description", ""),
            "model": agent.get("model", defaults.get("model", "sonnet")),
            "is_default": agent_id == default_id
        }
        for agent_id, agent in agents.items()
    ]
