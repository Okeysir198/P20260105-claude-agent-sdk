"""SDK options builder for Claude Agent SDK.

Contains functions for creating enhanced SDK options with skills and subagents.
"""
from claude_agent_sdk import ClaudeAgentOptions

from agent import PROJECT_ROOT
from agent.core.agents import create_subagents
from agent.discovery.mcp import load_project_mcp_servers

INCLUDE_PARTIAL_MESSAGES = True


def get_project_root() -> str:
    """Get the project root directory (where .claude/skills/ is located)."""
    return str(PROJECT_ROOT)


def create_enhanced_options(resume_session_id: str | None = None) -> ClaudeAgentOptions:
    """Create SDK options with Skills and Subagents enabled.

    Args:
        resume_session_id: Optional session ID to resume.

    Returns:
        Configured ClaudeAgentOptions with skills and subagents.
    """
    project_root = get_project_root()

    # Load only project-level MCP servers (excludes user/global MCP servers)
    project_mcp_servers = load_project_mcp_servers()

    options_dict = {
        "cwd": project_root,
        "setting_sources": ["project"],  # Load Skills from .claude/skills/
        "mcp_servers": project_mcp_servers,  # Only project-level MCP servers
        "agents": create_subagents(),     # Enable Subagents
        "allowed_tools": [
            "Skill",      # Enable Skills (code-analyzer, doc-generator, issue-tracker)
            "Task",       # Enable Subagent invocation
            "Read",
            "Write",
            "Bash",
            "Grep",
            "Glob"
        ],
        "permission_mode": "acceptEdits",
        "include_partial_messages": INCLUDE_PARTIAL_MESSAGES
    }

    if resume_session_id:
        options_dict["resume"] = resume_session_id

    return ClaudeAgentOptions(**options_dict)
