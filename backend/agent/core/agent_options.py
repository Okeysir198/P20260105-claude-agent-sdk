"""SDK options builder that maps agents.yaml config to ClaudeAgentOptions."""
import logging
import os
import sys
from pathlib import Path
from typing import Any, Callable, Awaitable

from claude_agent_sdk import ClaudeAgentOptions
from claude_agent_sdk.types import PermissionResultAllow, PermissionResultDeny, ToolPermissionContext

from agent import PROJECT_ROOT
from agent.core.agents import load_agent_config, AGENTS_CONFIG_PATH

_CUSTOM_PLUGIN_DIRS = ["plugins/media-tools", "plugins/email-tools"]
for _pdir in _CUSTOM_PLUGIN_DIRS:
    _abs = str((PROJECT_ROOT / _pdir).resolve())
    if _abs not in sys.path:
        sys.path.insert(0, _abs)
    _pypath = os.environ.get("PYTHONPATH", "")
    if _abs not in _pypath:
        os.environ["PYTHONPATH"] = f"{_abs}:{_pypath}" if _pypath else _abs
from agent.core.subagents import load_subagents
from agent.core.hook import create_ask_user_question_hook, create_expanded_hook, create_permission_hook

logger = logging.getLogger(__name__)

__all__ = [
    "create_agent_sdk_options",
    "get_project_root",
    "resolve_path",
    "set_email_tools_username",
    "set_email_tools_session_id",
    "set_media_tools_username",
    "set_media_tools_session_id",
    "CanUseToolCallback",
]

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


def _ensure_data_dir_env() -> None:
    """Ensure DATA_DIR env var is set for plugin subprocesses."""
    if "DATA_DIR" not in os.environ:
        os.environ["DATA_DIR"] = str(PROJECT_ROOT / "data")


def set_email_tools_username(username: str) -> None:
    """Set EMAIL_USERNAME env var for MCP subprocess inheritance."""
    _ensure_data_dir_env()
    os.environ["EMAIL_USERNAME"] = username
    logger.debug(f"Set EMAIL_USERNAME={username}")


def set_email_tools_session_id(session_id: str) -> None:
    """Set EMAIL_SESSION_ID env var for MCP subprocess inheritance."""
    os.environ["EMAIL_SESSION_ID"] = session_id
    logger.debug(f"Set EMAIL_SESSION_ID={session_id}")


def set_media_tools_username(username: str) -> None:
    """Set MEDIA_USERNAME env var for MCP subprocess inheritance."""
    _ensure_data_dir_env()
    os.environ["MEDIA_USERNAME"] = username
    logger.debug(f"Set MEDIA_USERNAME={username}")


def set_media_tools_session_id(session_id: str) -> None:
    """Set MEDIA_SESSION_ID env var for MCP subprocess inheritance."""
    os.environ["MEDIA_SESSION_ID"] = session_id
    logger.debug(f"Set MEDIA_SESSION_ID={session_id}")


def _resolve_plugins(plugins_config: list) -> list[dict]:
    """Resolve plugin config entries (string IDs or path dicts) to SDK plugin dicts."""
    if not plugins_config:
        return []

    plugins = []
    for entry in plugins_config:
        if isinstance(entry, str):
            path = _get_installed_plugin_path(entry)
            if path:
                plugins.append({"type": "local", "path": path})
            else:
                logger.warning(f"Plugin '{entry}' not found — skipping")
        elif isinstance(entry, dict) and "path" in entry:
            resolved = resolve_path(entry["path"])
            if resolved:
                plugins.append({"type": "local", "path": resolved})
        else:
            logger.warning(f"Invalid plugin config entry: {entry}")

    return plugins


def _get_installed_plugin_path(plugin_id: str) -> str | None:
    """Look up a plugin's install path from ~/.claude/plugins/installed_plugins.json."""
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


def _build_expanded_workspace_context() -> str:
    """Build system prompt context for Docker expanded permission mode."""
    return """

## Docker Workspace

You are running inside a Docker container with expanded permissions.

- **Persistent workspace**: `/home/appuser/workspace/` — files here survive container restarts and redeployments.
- **Persistent venv**: To install Python packages that persist across redeployments, activate the workspace venv first:
  ```
  source /home/appuser/workspace/.venv/bin/activate && pip install <package>
  ```
  Packages installed without the venv (plain `pip install`) will be lost on the next redeployment.
- **Temp files**: `/tmp/` is available but does not persist.
- **Protected**: You cannot modify app source code under `/app/` (except `/app/data/`).
"""


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

    Loads agent config merged with _defaults. Relative paths resolved from
    agents.yaml location.

    Args:
        agent_id: Agent ID from agents.yaml. Uses default if None.
        resume_session_id: Session ID to resume.
        can_use_tool: Async callback invoked before tool execution.
        session_cwd: Override working directory (e.g. session file storage dir).
        permission_folders: Override allowed write directories for permission hooks.
        client_type: Client platform type (e.g. "web", "telegram").
    """
    config = load_agent_config(agent_id)
    project_root = get_project_root()

    effective_cwd = session_cwd or resolve_path(config.get("cwd")) or project_root
    base_dirs = list(permission_folders) if permission_folders is not None else list(config.get("allowed_directories") or [])
    mcp_servers = config.get("mcp_servers") or {}
    plugins = _resolve_plugins(config.get("plugins") or [])

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

    all_subagents = load_subagents()
    if subagent_names := config.get("subagents"):
        options["agents"] = {
            name: defn for name, defn in all_subagents.items()
            if name in subagent_names
        }
    else:
        options["agents"] = all_subagents

    system_prompt = config.get("system_prompt") or ""

    if os.getenv("AGENT_PERMISSION_PROFILE") == "expanded":
        system_prompt += _build_expanded_workspace_context()

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

    # AskUserQuestion normalization must come before the permission hook
    hooks = [create_ask_user_question_hook()]

    if config.get("with_permissions"):
        permission_profile = os.getenv("AGENT_PERMISSION_PROFILE", "")
        if permission_profile == "expanded":
            hooks.append(create_expanded_hook())
        else:
            allowed_dirs = [resolve_path(d) or d for d in base_dirs]
            if effective_cwd not in allowed_dirs:
                allowed_dirs = [effective_cwd] + allowed_dirs
            if "/tmp" not in allowed_dirs:
                allowed_dirs.append("/tmp")
            allowed_dirs = [d.rstrip('/') + '/' for d in allowed_dirs]
            hooks.append(create_permission_hook(allowed_directories=allowed_dirs))

    options["hooks"] = {'PreToolUse': hooks}

    if resume_session_id:
        options["resume"] = resume_session_id

    if can_use_tool is not None:
        options["can_use_tool"] = can_use_tool

    _IGNORED_ERROR_PATTERNS = ("MCP error -32601", "1P event logging", "Failed to export")

    def stderr_callback(line: str) -> None:
        if "[ERROR]" in line and not any(p in line for p in _IGNORED_ERROR_PATTERNS):
            logger.error(f"SDK subprocess: {line}")

    options["stderr"] = stderr_callback

    if os.getenv("DEBUG"):
        options["extra_args"] = {"debug-to-stderr": None}

    return ClaudeAgentOptions(**{k: v for k, v in options.items() if v is not None})
