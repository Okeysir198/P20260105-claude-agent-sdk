#!/usr/bin/env python3
"""Subagent definitions loader.

Loads subagent definitions from subagents.yaml for delegation within conversations.
Different from top-level agents (agents.yaml) - these are used via the Task tool.
"""
from pathlib import Path

from claude_agent_sdk import AgentDefinition

from agent.core.yaml_utils import load_yaml_config

SUBAGENTS_CONFIG_PATH = Path(__file__).parent.parent.parent / "subagents.yaml"


def load_subagents() -> dict[str, AgentDefinition]:
    """Load subagents from subagents.yaml directly to AgentDefinition.

    Returns:
        Dictionary mapping subagent names to AgentDefinition instances.
    """
    config = load_yaml_config(SUBAGENTS_CONFIG_PATH)
    if not config:
        return {}

    return {
        name: AgentDefinition(
            description=sub.get("description", ""),
            prompt=sub.get("prompt", ""),
            tools=sub.get("tools"),
            model=sub.get("model", "sonnet"),
        )
        for name, sub in config.get("subagents", {}).items()
    }


def get_subagents_info() -> list[dict]:
    """Get subagent information for display.

    Returns:
        List of dictionaries with subagent name and focus description.
    """
    config = load_yaml_config(SUBAGENTS_CONFIG_PATH)
    if not config:
        return []

    return [
        {"name": name, "focus": sub.get("focus", "")}
        for name, sub in config.get("subagents", {}).items()
    ]
