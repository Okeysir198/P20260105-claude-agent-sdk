"""SDK options builder for Claude Agent SDK.

Contains functions for creating enhanced SDK options with skills and subagents.
"""
from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions

from agent import PROJECT_ROOT
from agent.core.subagents import create_subagents
from agent.core.agents import get_agent, TopLevelAgent
from agent.core.hook import create_permission_hook
from agent.discovery.mcp import load_project_mcp_servers

# Default for SDK options. Session-level override available via ConversationSession(include_partial_messages=...)
INCLUDE_PARTIAL_MESSAGES = True


def get_project_root() -> str:
    """Get the project root directory (where .claude/skills/ is located)."""
    return str(PROJECT_ROOT)


def create_enhanced_options(
    agent_id: str | None = None,
    resume_session_id: str | None = None,
    with_permissions: bool = False,
    allowed_directories: list[str] | None = None
) -> ClaudeAgentOptions:
    """Create SDK options with Skills and Subagents enabled.

    Args:
        agent_id: Optional agent ID to load a specific agent configuration.
            When provided, loads the agent config from definitions and applies
            its tools, subagents, and read_only settings.
        resume_session_id: Optional session ID to resume.
        with_permissions: Whether to add permission hooks for controlling file access.
            When enabled, restricts Write/Edit operations to the current working
            directory (cwd) and /tmp by default for safety.
        allowed_directories: List of directories where file operations are allowed.
            Only used when with_permissions=True. Defaults to [cwd, "/tmp"].

    Returns:
        Configured ClaudeAgentOptions with skills and subagents.

    Example:
        ```python
        # No permissions (default behavior - full access)
        options = create_enhanced_options()

        # With a specific agent configuration
        options = create_enhanced_options(agent_id="researcher")

        # With permission hooks (allows cwd + /tmp only)
        options = create_enhanced_options(with_permissions=True)

        # Custom allowed directories
        options = create_enhanced_options(
            with_permissions=True,
            allowed_directories=["/custom/path", "/tmp"]
        )
        ```
    """
    project_root = get_project_root()

    # Load only project-level MCP servers (excludes user/global MCP servers)
    project_mcp_servers = load_project_mcp_servers()

    # Get agent configuration if agent_id is provided
    agent_config: TopLevelAgent | None = None
    if agent_id:
        agent_config = get_agent(agent_id)

    # Build allowed_tools list
    default_tools = [
        "Skill",      # Enable Skills (code-analyzer, doc-generator, issue-tracker)
        "Task",       # Enable Subagent invocation
        "Read",
        "Write",
        "Bash",
        "Grep",
        "Glob"
    ]

    if agent_config:
        # Use agent's tools if specified, otherwise use defaults
        if agent_config.tools:
            allowed_tools = list(agent_config.tools)
        else:
            allowed_tools = default_tools.copy()

        # Remove Write tool if agent is read_only
        if agent_config.read_only:
            allowed_tools = [t for t in allowed_tools if t != "Write"]
    else:
        allowed_tools = default_tools

    # Build subagents dictionary
    all_subagents = create_subagents()
    if agent_config and agent_config.subagents:
        # Filter subagents based on agent config
        subagents = {
            name: defn for name, defn in all_subagents.items()
            if name in agent_config.subagents
        }
    else:
        subagents = all_subagents

    options_dict = {
        "cwd": project_root,
        "setting_sources": ["project"],  # Load Skills from .claude/skills/
        "mcp_servers": project_mcp_servers,  # Only project-level MCP servers
        "agents": subagents,     # Enable Subagents (filtered if agent_config provided)
        "allowed_tools": allowed_tools,
        "permission_mode": "acceptEdits",
        "include_partial_messages": INCLUDE_PARTIAL_MESSAGES
    }

    # Add system_prompt if agent has one defined
    # Use append mode to preserve the default claude_code prompt
    if agent_config and agent_config.system_prompt:
        options_dict["system_prompt"] = {
            "type": "preset",
            "preset": "claude_code",
            "append": agent_config.system_prompt
        }

    # Add permission hooks if requested
    if with_permissions:
        if allowed_directories is None:
            # Default: allow current working directory (project_root) and /tmp
            # This provides safe defaults while allowing normal project work
            allowed_directories = [project_root, "/tmp"]

        options_dict["hooks"] = {
            'PreToolUse': [create_permission_hook(allowed_directories=allowed_directories)]
        }

    if resume_session_id:
        options_dict["resume"] = resume_session_id

    return ClaudeAgentOptions(**options_dict)


def create_sandbox_options(
    sandbox_dir: str,
    additional_allowed_dirs: list[str] | None = None,
    resume_session_id: str | None = None
) -> ClaudeAgentOptions:
    """Create SDK options with strict sandbox permissions.

    This creates options with maximum security by restricting all file
    operations to the specified sandbox directory.

    Args:
        sandbox_dir: The primary sandbox directory for all operations.
        additional_allowed_dirs: Optional list of additional directories to allow.
        resume_session_id: Optional session ID to resume.

    Returns:
        Configured ClaudeAgentOptions with sandbox restrictions.

    Example:
        ```python
        from agent.core.agent_options import create_sandbox_options
        from agent import PROJECT_ROOT

        options = create_sandbox_options(
            sandbox_dir=str(PROJECT_ROOT / "tests"),
            additional_allowed_dirs=["/tmp"]
        )
        ```
    """
    # Load only project-level MCP servers
    project_mcp_servers = load_project_mcp_servers()

    allowed_dirs = [sandbox_dir]
    if additional_allowed_dirs:
        allowed_dirs.extend(additional_allowed_dirs)

    options_dict = {
        "cwd": sandbox_dir,
        "setting_sources": ["project"],
        "mcp_servers": project_mcp_servers,
        "agents": create_subagents(),
        "allowed_tools": [
            "Skill",
            "Task",
            "Read",
            "Write",
            "Edit",
            "Bash",
            "Grep",
            "Glob"
        ],
        "hooks": {
            'PreToolUse': [create_permission_hook(allowed_directories=allowed_dirs)]
        },
        "include_partial_messages": INCLUDE_PARTIAL_MESSAGES
    }

    if resume_session_id:
        options_dict["resume"] = resume_session_id

    return ClaudeAgentOptions(**options_dict)
