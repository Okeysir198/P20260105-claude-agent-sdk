"""List commands for Claude Agent SDK CLI.

Contains commands for listing skills, agents, and sessions.
"""
import asyncio

from agent.display import print_error
from cli.clients import APIClient
from cli.commands.handlers import show_skills, show_agents, show_subagents, show_sessions


async def _run_with_client(show_func) -> None:
    """Run a show function with client and handle cleanup.

    Args:
        show_func: Async function to call with the client.
    """
    # Use default API URL
    client = APIClient()
    try:
        await show_func(client)
    finally:
        await client.disconnect()


def skills_command():
    """List available skills.

    Displays all skills discovered from .claude/skills/ directory.
    """
    async def _show():
        client = APIClient()
        try:
            await show_skills(client.list_skills)
        finally:
            await client.disconnect()

    try:
        asyncio.run(_show())
    except Exception as e:
        print_error(f"Error listing skills: {e}")


def agents_command():
    """List available top-level agents.

    Displays all registered agents that can be selected via agent_id.
    """
    async def _show():
        client = APIClient()
        try:
            await show_agents(client.list_agents)
        finally:
            await client.disconnect()

    try:
        asyncio.run(_show())
    except Exception as e:
        print_error(f"Error listing agents: {e}")


def subagents_command():
    """List available subagents.

    Displays all delegation subagents used within conversations.
    """
    async def _show():
        client = APIClient()
        try:
            await show_subagents(client.list_subagents)
        finally:
            await client.disconnect()

    try:
        asyncio.run(_show())
    except Exception as e:
        print_error(f"Error listing subagents: {e}")


def sessions_command():
    """List conversation sessions.

    Shows session history from storage.
    """
    async def _show():
        client = APIClient()
        try:
            await show_sessions(client.list_sessions)
        finally:
            await client.disconnect()

    try:
        asyncio.run(_show())
    except Exception as e:
        print_error(f"Error listing sessions: {e}")
