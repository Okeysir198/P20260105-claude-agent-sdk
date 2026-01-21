"""SDK options builder for Claude Agent SDK.

Simplified configuration that maps YAML config directly to SDK options.
"""
from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions

from agent import PROJECT_ROOT
from agent.core.agents import load_agent_config, AGENTS_CONFIG_PATH
from agent.core.subagents import load_subagents
from agent.core.hook import create_permission_hook


def get_project_root() -> str:
    """Get the project root directory (where .claude/skills/ is located)."""
    return str(PROJECT_ROOT)


def resolve_path(path: str | None) -> str | None:
    """Resolve a path, handling relative paths from agents.yaml location.

    Args:
        path: Path string. Can be:
            - None: Returns None
            - Absolute path: Returns as-is
            - Relative path: Resolved relative to agents.yaml directory

    Returns:
        Resolved absolute path string, or None if input was None.
    """
    if path is None:
        return None

    p = Path(path)
    if p.is_absolute():
        return str(p)

    # Resolve relative to agents.yaml directory
    yaml_dir = AGENTS_CONFIG_PATH.parent
    resolved = (yaml_dir / p).resolve()
    return str(resolved)


def create_agent_sdk_options(
    agent_id: str | None = None,
    resume_session_id: str | None = None,
) -> ClaudeAgentOptions:
    """Create SDK options from agents.yaml configuration.

    All configuration is loaded from agents.yaml. The agent's config is merged
    with _defaults, so agents only need to specify overrides.

    Path resolution:
        - cwd and allowed_directories support relative paths
        - Relative paths are resolved from agents.yaml location
        - Example: cwd: "../.." resolves to 2 levels up from agents.yaml

    Args:
        agent_id: Agent ID to load config from agents.yaml. Uses default if None.
        resume_session_id: Session ID to resume.

    Returns:
        Configured ClaudeAgentOptions.

    Examples:
        # Basic usage with default agent
        options = create_agent_sdk_options()

        # With specific agent
        options = create_agent_sdk_options(agent_id="code-reviewer-x9y8z7w6")

        # With sandboxed agent (permissions configured in YAML)
        options = create_agent_sdk_options(agent_id="sandbox-agent-s4ndb0x1")

        # Resume a session
        options = create_agent_sdk_options(resume_session_id="abc123")
    """
    config = load_agent_config(agent_id)
    project_root = get_project_root()

    # Resolve cwd (supports relative paths from agents.yaml)
    effective_cwd = resolve_path(config.get("cwd")) or project_root

    options = {
        "cwd": effective_cwd,
        "setting_sources": config.get("setting_sources"),
        "allowed_tools": config.get("tools"),
        "disallowed_tools": config.get("disallowed_tools"),
        "permission_mode": config.get("permission_mode"),
        "include_partial_messages": config.get("include_partial_messages"),
        "add_dirs": config.get("allowed_directories") or None,
        "mcp_servers": config.get("mcp_servers") or None,
    }

    # Build subagents from subagents.yaml, filtered by agent config
    all_subagents = load_subagents()
    if subagent_names := config.get("subagents"):
        options["agents"] = {
            name: defn for name, defn in all_subagents.items()
            if name in subagent_names
        }
    else:
        options["agents"] = all_subagents

    # System prompt append mode
    if system_prompt := config.get("system_prompt"):
        options["system_prompt"] = {
            "type": "preset",
            "preset": "claude_code",
            "append": system_prompt
        }

    # Add permission hooks if configured in YAML
    if config.get("with_permissions"):
        # Resolve allowed_directories (supports relative paths)
        allowed_dirs = [
            resolve_path(d) or d
            for d in (config.get("allowed_directories") or [])
        ]
        # Always include cwd and /tmp as defaults
        if effective_cwd not in allowed_dirs:
            allowed_dirs = [effective_cwd] + allowed_dirs
        if "/tmp" not in allowed_dirs:
            allowed_dirs = allowed_dirs + ["/tmp"]
        options["hooks"] = {
            'PreToolUse': [create_permission_hook(allowed_directories=allowed_dirs)]
        }

    if resume_session_id:
        options["resume"] = resume_session_id

    # Filter out None and empty values
    return ClaudeAgentOptions(**{k: v for k, v in options.items() if v is not None})
