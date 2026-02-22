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

__all__ = [
    "create_agent_sdk_options",
    "get_project_root",
    "resolve_path",
    "set_email_tools_username",
    "set_media_tools_username",
    "set_media_tools_session_id",
    "CanUseToolCallback",
]

# Email MCP server - imported conditionally
try:
    from agent.tools.email.mcp_server import email_tools_server, set_username, initialize_email_tools
    EMAIL_TOOLS_AVAILABLE = True
except ImportError:
    logger.warning("Email tools MCP server not available - google-api-python-client may not be installed")
    EMAIL_TOOLS_AVAILABLE = False
    email_tools_server = None
    set_username = None
    initialize_email_tools = None

# Media tools MCP server - imported conditionally
try:
    from agent.tools.media.mcp_server import media_tools_server, set_username as set_media_username, set_session_id as set_media_session_id
    MEDIA_TOOLS_AVAILABLE = True
except ImportError:
    logger.warning("Media tools MCP server not available - httpx may not be installed")
    MEDIA_TOOLS_AVAILABLE = False
    media_tools_server = None
    set_media_username = None
    set_media_session_id = None

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


def set_email_tools_username(username: str) -> None:
    """Set the username context for email tools.

    This must be called before email tools are used to provide per-user credential lookup.

    Args:
        username: Username for credential isolation
    """
    if EMAIL_TOOLS_AVAILABLE and set_username is not None:
        set_username(username)
        logger.debug(f"Set email tools username: {username}")
    else:
        logger.debug("Email tools not available, skipping username setup")


def set_media_tools_username(username: str) -> None:
    """Set the username context for media tools.

    This must be called before media tools are used to provide per-user file lookup.

    Args:
        username: Username for file isolation
    """
    # Set environment variable for subprocess calls (SDK runs MCP tools in subprocess)
    os.environ["MEDIA_USERNAME"] = username

    if MEDIA_TOOLS_AVAILABLE and set_media_username is not None:
        set_media_username(username)
        logger.debug(f"Set media tools username: {username} (env + context)")
    else:
        logger.debug("Media tools not available, skipping username setup")


def set_media_tools_session_id(session_id: str) -> None:
    """Set the session_id context for media tools.

    This must be called before media tools are used to provide per-session file isolation.
    Sets both the context variable (for in-process) and environment variable (for subprocess).

    Args:
        session_id: Session ID for file grouping (typically the cwd_id from session data)
    """
    import os
    # Set environment variable for subprocess calls (SDK runs MCP tools in subprocess)
    os.environ["MEDIA_SESSION_ID"] = session_id

    if MEDIA_TOOLS_AVAILABLE and set_media_session_id is not None:
        set_media_session_id(session_id)
        logger.debug(f"Set media tools session_id: {session_id} (env + context)")
    else:
        logger.debug("Media tools not available, skipping session_id setup")


def _resolve_plugins(plugins_config: list) -> list[dict]:
    """Resolve plugin config entries to SDK plugin dicts.

    Supports two formats:
      - String identifier (e.g. "playwright@claude-plugins-official"):
        Looked up in ~/.claude/plugins/installed_plugins.json
      - Dict with "path" key (e.g. {"path": "./my-plugin"}):
        Resolved relative to agents.yaml directory.

    Returns:
        List of {"type": "local", "path": "<absolute_path>"} dicts.
    """
    if not plugins_config:
        return []

    plugins = []
    for entry in plugins_config:
        if isinstance(entry, str):
            # Plugin identifier — resolve from installed_plugins.json
            path = _get_installed_plugin_path(entry)
            if path:
                plugins.append({"type": "local", "path": path})
            else:
                logger.warning(f"Plugin '{entry}' not found — skipping")
        elif isinstance(entry, dict) and "path" in entry:
            # Local path — resolve relative to agents.yaml
            resolved = resolve_path(entry["path"])
            if resolved:
                plugins.append({"type": "local", "path": resolved})
        else:
            logger.warning(f"Invalid plugin config entry: {entry}")

    return plugins


def _get_installed_plugin_path(plugin_id: str) -> str | None:
    """Look up a plugin's install path from ~/.claude/plugins/installed_plugins.json.

    Args:
        plugin_id: Plugin identifier (e.g. "playwright@claude-plugins-official").

    Returns:
        Absolute install path, or None if not found.
    """
    installed_file = Path.home() / ".claude" / "plugins" / "installed_plugins.json"
    if not installed_file.exists():
        return None

    try:
        import json
        data = json.loads(installed_file.read_text())
        entries = data.get("plugins", {}).get(plugin_id, [])
        for entry in entries:
            install_path = entry.get("installPath")
            if install_path and Path(install_path).exists():
                return install_path
        return None
    except Exception as e:
        logger.warning(f"Failed to read installed plugins: {e}")
        return None


def _build_platform_context(platform: str) -> str:
    """Build system prompt context for chat platform users (Telegram, WhatsApp, etc.)."""
    return f"""

## Chat Platform Context

You are conversing with the user via **{platform}** messaging platform.

**Important behavioral rules for platform conversations:**
- Keep responses concise and mobile-friendly (shorter paragraphs, less verbose)
- When you generate files (audio, images, documents), use the `send_file_to_chat` tool to deliver them to the user — do NOT include download URLs in your text response
- Only send files the user actually needs (e.g. TTS audio). Do NOT send intermediate files like transcripts or OCR text — include that content directly in your text response instead
- Avoid markdown tables (they render poorly on mobile) — use simple lists instead
- Avoid very long code blocks — keep them short or summarize
- The user cannot see tool call details, so summarize what you did rather than showing raw tool output
- Do NOT use AskUserQuestion tool — just ask in plain text (the tool UI doesn't work on platforms)
"""


def _build_web_context() -> str:
    """Build system prompt context for web chat users."""
    return """

## Web Chat Context

You are conversing with the user via the **web chat** interface.

**Important behavioral rules for web conversations:**
- The user can see tool calls, tool results, and file previews in the UI
- When media tools generate files (audio, images), include the download URL in your response so the user can access them directly
- You can use rich markdown formatting including tables, code blocks, and headers
- You can use AskUserQuestion for structured multi-choice questions
- For file delivery to external platforms, use the `send_file_to_chat` tool
"""


def create_agent_sdk_options(
    agent_id: str | None = None,
    resume_session_id: str | None = None,
    can_use_tool: CanUseToolCallback | None = None,
    session_cwd: str | None = None,
    permission_folders: list[str] | None = None,
    client_type: str | None = None,
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
        session_cwd: Optional session working directory override.
            When provided, overrides the cwd from agents.yaml config.
            Typically set to the session's file storage directory so the
            agent operates within the session folder. Subdirectories (input/,
            output/) are accessible via the cwd.
        permission_folders: Optional list of allowed write directories for the session.
            When provided, overrides config-level allowed_directories for permission hooks.
            The session cwd is always auto-added on top of these.

    Returns:
        Configured ClaudeAgentOptions.

    Examples:
        # Basic usage with default agent
        options = create_agent_sdk_options()

        # With specific agent
        options = create_agent_sdk_options(agent_id="code-reviewer-x9y8z7w6")

        # Resume a session
        options = create_agent_sdk_options(resume_session_id="abc123")

        # With session cwd and permission folders
        options = create_agent_sdk_options(
            session_cwd="/path/to/data/user/files/cwd_id/",
            permission_folders=["/tmp"],
        )
    """
    config = load_agent_config(agent_id)
    project_root = get_project_root()

    # Resolve cwd: session_cwd > config cwd > project_root
    if session_cwd:
        effective_cwd = session_cwd
    else:
        effective_cwd = resolve_path(config.get("cwd")) or project_root

    # Resolve base directory list: permission_folders > config allowed_directories
    base_dirs = list(permission_folders) if permission_folders is not None else list(config.get("allowed_directories") or [])

    # Build MCP servers config - merge email tools if requested
    mcp_servers = config.get("mcp_servers") or {}

    # Check if agent needs email tools (by checking if any tool starts with "mcp__email_tools")
    needs_email_tools = any(
        tool.startswith("mcp__email_tools") for tool in (config.get("tools") or [])
    )

    if needs_email_tools and EMAIL_TOOLS_AVAILABLE:
        mcp_servers = {**mcp_servers, "email_tools": email_tools_server}
        logger.info("Registered email_tools MCP server for agent")
    elif needs_email_tools and not EMAIL_TOOLS_AVAILABLE:
        logger.warning("Agent requires email tools but MCP server is not available")

    # Check if agent needs media tools (by checking if any tool starts with "mcp__media_tools")
    needs_media_tools = any(
        tool.startswith("mcp__media_tools") for tool in (config.get("tools") or [])
    )

    if needs_media_tools and MEDIA_TOOLS_AVAILABLE:
        mcp_servers = {**mcp_servers, "media_tools": media_tools_server}
        logger.info("Registered media_tools MCP server for agent")
    elif needs_media_tools and not MEDIA_TOOLS_AVAILABLE:
        logger.warning("Agent requires media tools but MCP server is not available")

    # Build plugins list from agent config.
    # Entries can be:
    #   - Plugin identifier string (e.g. "playwright@claude-plugins-official")
    #     → resolved to install path from ~/.claude/plugins/installed_plugins.json
    #   - Dict with "path" key (e.g. {"path": "./my-local-plugin"})
    #     → resolved relative to agents.yaml directory
    plugins_config = config.get("plugins") or []
    plugins = _resolve_plugins(plugins_config)

    options = {
        "cwd": effective_cwd,
        "setting_sources": config.get("setting_sources"),
        "allowed_tools": config.get("tools"),
        "disallowed_tools": config.get("disallowed_tools"),
        "permission_mode": config.get("permission_mode"),
        "include_partial_messages": config.get("include_partial_messages"),
        "add_dirs": base_dirs if base_dirs else None,
        "mcp_servers": mcp_servers or None,
        "plugins": plugins or None,
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
    system_prompt = config.get("system_prompt") or ""

    # Append client/platform context so the agent knows how to interact
    if client_type and client_type != "web":
        system_prompt += _build_platform_context(client_type)
    else:
        system_prompt += _build_web_context()

    if system_prompt.strip():
        options["system_prompt"] = {
            "type": "preset",
            "preset": "claude_code",
            "append": system_prompt
        }

    # Always add AskUserQuestion normalization hook (fixes string-encoded questions from model)
    # This hook MUST come before the permission hook so input is normalized first
    ask_user_hook = create_ask_user_question_hook()

    # Build hooks list -- always includes AskUserQuestion normalization
    hooks = [ask_user_hook]

    if config.get("with_permissions"):
        # Resolve relative paths for permission directories
        allowed_dirs = [resolve_path(d) or d for d in base_dirs]

        # Always include cwd and /tmp as defaults
        if effective_cwd not in allowed_dirs:
            allowed_dirs = [effective_cwd] + allowed_dirs
        if "/tmp" not in allowed_dirs:
            allowed_dirs.append("/tmp")

        # Normalize with trailing / for safe startswith() matching
        allowed_dirs = [d.rstrip('/') + '/' for d in allowed_dirs]
        hooks.append(create_permission_hook(allowed_directories=allowed_dirs))

    options["hooks"] = {'PreToolUse': hooks}

    if resume_session_id:
        options["resume"] = resume_session_id

    # Add can_use_tool callback if provided
    if can_use_tool is not None:
        options["can_use_tool"] = can_use_tool

    # Log SDK subprocess errors, filtering known non-critical noise
    _IGNORED_ERROR_PATTERNS = ("MCP error -32601", "1P event logging", "Failed to export")

    def stderr_callback(line: str) -> None:
        if "[ERROR]" in line and not any(p in line for p in _IGNORED_ERROR_PATTERNS):
            logger.error(f"SDK subprocess: {line}")

    options["stderr"] = stderr_callback

    # Only enable debug mode if DEBUG env var is set
    if os.getenv("DEBUG"):
        options["extra_args"] = {"debug-to-stderr": None}

    # Filter out None and empty values
    return ClaudeAgentOptions(**{k: v for k, v in options.items() if v is not None})
