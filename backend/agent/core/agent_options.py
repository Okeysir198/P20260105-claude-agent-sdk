"""SDK options builder for Claude Agent SDK.

Simplified configuration that maps YAML config directly to SDK options.
"""
import logging
import os
from pathlib import Path
from typing import Any, Callable, Awaitable

from claude_agent_sdk import ClaudeAgentOptions
from claude_agent_sdk.types import PermissionResultAllow, PermissionResultDeny, ToolPermissionContext

from agent import PROJECT_ROOT
from agent.core.agents import load_agent_config, AGENTS_CONFIG_PATH
from agent.core.subagents import load_subagents
from agent.core.hook import create_ask_user_question_hook, create_permission_hook

logger = logging.getLogger(__name__)

# Type alias for can_use_tool callback
# Takes tool_name, tool_input, and context
# Returns PermissionResultAllow or PermissionResultDeny
CanUseToolCallback = Callable[
    [str, dict[str, Any], ToolPermissionContext],
    Awaitable[PermissionResultAllow | PermissionResultDeny]
]


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
    can_use_tool: CanUseToolCallback | None = None,
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
        can_use_tool: Optional async callback invoked before tool execution.
            Signature: async (tool_name: str, tool_input: dict) -> dict | None
            - Return dict to override/provide tool result (e.g., for AskUserQuestion)
            - Return None to deny tool use
            - Return empty dict {} to allow normal tool execution

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

        # With can_use_tool callback for interactive tools
        async def my_callback(tool_name, tool_input):
            if tool_name == "AskUserQuestion":
                # Handle user interaction
                return {"questions": [...], "answers": {...}}
            return {}  # Allow other tools
        options = create_agent_sdk_options(can_use_tool=my_callback)
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

    # Always add AskUserQuestion normalization hook (fixes string-encoded questions from model)
    # This hook MUST come before the permission hook so input is normalized first
    ask_user_hook = create_ask_user_question_hook()

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
            'PreToolUse': [ask_user_hook, create_permission_hook(allowed_directories=allowed_dirs)]
        }
    else:
        # Even without permission hooks, add the AskUserQuestion normalization hook
        options["hooks"] = {
            'PreToolUse': [ask_user_hook]
        }

    if resume_session_id:
        options["resume"] = resume_session_id

    # Add can_use_tool callback if provided
    if can_use_tool is not None:
        options["can_use_tool"] = can_use_tool

    # Add stderr callback to capture subprocess errors for debugging
    def stderr_callback(line: str) -> None:
        # Only log actual errors, not debug/warning messages
        if "[ERROR]" in line:
            # Filter out known non-critical MCP errors
            if "Failed to fetch resources" in line and "MCP error -32601" in line:
                # MCP server doesn't support resources/list - this is expected for some servers
                return
            # Filter out 1P event logging errors (telemetry failures)
            if "1P event logging" in line or "Failed to export" in line:
                return
            logger.error(f"SDK subprocess: {line}")

    options["stderr"] = stderr_callback

    # Only enable debug mode if DEBUG env var is set
    if os.getenv("DEBUG"):
        options["extra_args"] = {"debug-to-stderr": None}

    # Filter out None and empty values
    return ClaudeAgentOptions(**{k: v for k, v in options.items() if v is not None})
