"""Top-level agent definitions loader.

Different from subagents - these are complete agent configurations
that can be selected via agent_id when creating a session.
"""
import secrets
import yaml
from pathlib import Path
from dataclasses import dataclass, field

AGENTS_CONFIG_PATH = Path(__file__).parent.parent / "agents.yaml"

@dataclass
class TopLevelAgent:
    """Definition for a top-level agent configuration."""
    agent_id: str
    name: str
    type: str
    description: str
    system_prompt: str
    tools: list[str] = field(default_factory=list)
    subagents: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    model: str = "sonnet"
    read_only: bool = False


def generate_agent_id(agent_type: str) -> str:
    """Generate a unique agent ID.

    Args:
        agent_type: The type/category of agent (e.g., 'researcher', 'reviewer')

    Returns:
        Unique agent ID like 'research-agent-bvdrgh234'
    """
    suffix = secrets.token_hex(4)
    return f"{agent_type}-agent-{suffix}"


def _create_default_agent() -> TopLevelAgent:
    """Create a default agent when no config exists."""
    return TopLevelAgent(
        agent_id="general-agent-default",
        name="General Assistant",
        type="general",
        description="General-purpose coding assistant",
        system_prompt="You are a helpful coding assistant.",
        tools=["Skill", "Task", "Read", "Write", "Bash", "Grep", "Glob"],
        subagents=["researcher", "reviewer", "file_assistant"],
        skills=["code-analyzer", "doc-generator", "issue-tracker"],
        model="sonnet",
        read_only=False
    )


def load_agent_definitions() -> dict[str, TopLevelAgent]:
    """Load all agent definitions from agents.yaml."""
    if not AGENTS_CONFIG_PATH.exists():
        default = _create_default_agent()
        return {default.agent_id: default}

    with open(AGENTS_CONFIG_PATH) as f:
        config = yaml.safe_load(f)

    agents = {}
    for agent_id, agent_config in config.get("agents", {}).items():
        agents[agent_id] = TopLevelAgent(
            agent_id=agent_id,
            name=agent_config.get("name", agent_id),
            type=agent_config.get("type", "general"),
            description=agent_config.get("description", ""),
            system_prompt=agent_config.get("system_prompt", ""),
            tools=agent_config.get("tools", []),
            subagents=agent_config.get("subagents", []),
            skills=agent_config.get("skills", []),
            model=agent_config.get("model", "sonnet"),
            read_only=agent_config.get("read_only", False)
        )
    return agents


def get_default_agent_id() -> str:
    """Get the default agent ID from config."""
    if not AGENTS_CONFIG_PATH.exists():
        return "general-agent-default"

    with open(AGENTS_CONFIG_PATH) as f:
        config = yaml.safe_load(f)

    return config.get("default_agent", "general-agent-default")


def get_agent(agent_id: str | None = None) -> TopLevelAgent:
    """Get a specific agent by ID, or the default agent.

    Args:
        agent_id: The agent ID to retrieve. If None, returns default agent.

    Returns:
        The TopLevelAgent configuration.

    Raises:
        ValueError: If agent_id is not found.
    """
    agents = load_agent_definitions()

    if agent_id is None:
        agent_id = get_default_agent_id()

    if agent_id not in agents:
        raise ValueError(f"Agent '{agent_id}' not found. Available: {list(agents.keys())}")

    return agents[agent_id]


def get_agents_info() -> list[dict]:
    """Get agent information for display/API responses.

    Returns:
        List of dictionaries with agent info.
    """
    agents = load_agent_definitions()
    default_id = get_default_agent_id()

    return [
        {
            "agent_id": agent.agent_id,
            "name": agent.name,
            "type": agent.type,
            "description": agent.description,
            "model": agent.model,
            "read_only": agent.read_only,
            "is_default": agent.agent_id == default_id
        }
        for agent in agents.values()
    ]
