"""List commands for Claude Agent SDK CLI.

Contains commands for listing skills, agents, and sessions.
"""
import asyncio
from typing import Callable

from agent.display import print_error
from cli.clients import DirectClient, APIClient
from cli.commands.handlers import show_skills, show_agents, show_subagents, show_sessions


def _get_client(ctx) -> DirectClient | APIClient:
    """Create the appropriate client based on mode.

    Args:
        ctx: Click context with mode and api_url settings.

    Returns:
        DirectClient or APIClient based on the mode setting.
    """
    mode = ctx.obj['mode']
    if mode == 'direct':
        return DirectClient()
    else:  # api mode
        api_url = ctx.obj['api_url']
        return APIClient(api_url=api_url)


async def _run_with_client(client: DirectClient | APIClient, show_func: Callable) -> None:
    """Run a show function with client and handle cleanup.

    Args:
        client: The client instance to use.
        show_func: Async function to call with the client.
    """
    await show_func(client)
    await client.disconnect()


def skills_command(ctx):
    """List available skills.

    Displays all skills discovered from .claude/skills/ directory or
    from the API server (depending on mode).
    """
    client = _get_client(ctx)

    try:
        asyncio.run(_run_with_client(client, show_skills))
    except Exception as e:
        print_error(f"Error listing skills: {e}")


def agents_command(ctx):
    """List available top-level agents.

    Displays all registered agents that can be selected via agent_id.
    """
    client = _get_client(ctx)

    try:
        asyncio.run(_run_with_client(client, show_agents))
    except Exception as e:
        print_error(f"Error listing agents: {e}")


def subagents_command(ctx):
    """List available subagents.

    Displays all delegation subagents used within conversations.
    """
    client = _get_client(ctx)

    try:
        asyncio.run(_run_with_client(client, show_subagents))
    except Exception as e:
        print_error(f"Error listing subagents: {e}")


def sessions_command(ctx):
    """List conversation sessions.

    In direct mode: Shows local session history.
    In API mode: Shows active sessions on the server.
    """
    client = _get_client(ctx)

    try:
        asyncio.run(_run_with_client(client, show_sessions))
    except Exception as e:
        print_error(f"Error listing sessions: {e}")
