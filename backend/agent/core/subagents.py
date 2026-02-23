"""Subagent definitions loader from subagents.yaml (used via the Task tool)."""
from pathlib import Path

from claude_agent_sdk import AgentDefinition

from agent.core.yaml_utils import load_yaml_config

SUBAGENTS_CONFIG_PATH = Path(__file__).parent.parent.parent / "subagents.yaml"


def load_subagents() -> dict[str, AgentDefinition]:
    """Load subagents from subagents.yaml as AgentDefinition instances."""
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
    """Get subagent name and focus for display/API responses."""
    config = load_yaml_config(SUBAGENTS_CONFIG_PATH)
    if not config:
        return []

    return [
        {"name": name, "focus": sub.get("focus", "")}
        for name, sub in config.get("subagents", {}).items()
    ]
