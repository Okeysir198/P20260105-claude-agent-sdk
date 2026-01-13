"""MCP server loader for Claude Agent SDK.

Loads MCP server configuration from project's .mcp.json file.
"""
import json
from pathlib import Path

from agent import PROJECT_ROOT


def load_project_mcp_servers() -> dict:
    """Load MCP server configuration from project's .mcp.json only.

    Returns:
        Dictionary of MCP server configurations.
    """
    mcp_config_path = PROJECT_ROOT / ".mcp.json"
    if mcp_config_path.exists():
        with open(mcp_config_path) as f:
            mcp_config = json.load(f)
            return mcp_config.get("mcpServers", {})
    return {}
