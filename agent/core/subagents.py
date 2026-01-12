#!/usr/bin/env python3
"""Subagent definitions loader.

Loads subagent definitions from subagents.yaml for delegation within conversations.
Different from top-level agents (agents.yaml) - these are used via the Task tool.
"""
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from claude_agent_sdk import AgentDefinition

# Path to subagents.yaml (in agent/ folder)
SUBAGENTS_CONFIG_PATH = Path(__file__).parent.parent / "subagents.yaml"


@dataclass
class SubagentConfig:
    """Configuration for a subagent."""
    name: str
    description: str
    focus: str
    prompt: str
    tools: list[str] = field(default_factory=list)
    model: str = "sonnet"


def load_subagent_configs() -> dict[str, SubagentConfig]:
    """Load subagent configurations from subagents.yaml.

    Returns:
        Dictionary mapping subagent names to SubagentConfig instances.
    """
    if not SUBAGENTS_CONFIG_PATH.exists():
        return {}

    with open(SUBAGENTS_CONFIG_PATH) as f:
        config = yaml.safe_load(f)

    subagents = {}
    for subagent_id, subagent_config in config.get("subagents", {}).items():
        subagents[subagent_id] = SubagentConfig(
            name=subagent_config.get("name", subagent_id),
            description=subagent_config.get("description", ""),
            focus=subagent_config.get("focus", ""),
            prompt=subagent_config.get("prompt", ""),
            tools=subagent_config.get("tools", []),
            model=subagent_config.get("model", "sonnet")
        )
    return subagents


def create_subagents() -> dict[str, AgentDefinition]:
    """Create specialized subagents for development tasks.

    Loads subagent definitions from subagents.yaml and creates
    AgentDefinition instances for the SDK.

    Returns:
        Dictionary mapping agent names to AgentDefinition instances.
    """
    configs = load_subagent_configs()

    subagents = {}
    for subagent_id, config in configs.items():
        subagents[subagent_id] = AgentDefinition(
            description=config.description,
            prompt=config.prompt,
            tools=config.tools,
            model=config.model
        )

    return subagents


def get_agents_info() -> list[dict]:
    """Get subagent information for display.

    Returns:
        List of dictionaries with subagent name and focus description.
    """
    configs = load_subagent_configs()

    return [
        {"name": subagent_id, "focus": config.focus}
        for subagent_id, config in configs.items()
    ]
