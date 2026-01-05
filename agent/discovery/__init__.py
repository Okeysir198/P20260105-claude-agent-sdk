"""Discovery services module.

Contains skill discovery and MCP server loading functionality.
"""
from .skills import discover_skills
from .mcp import load_project_mcp_servers

__all__ = [
    'discover_skills',
    'load_project_mcp_servers',
]
