"""Main CLI entry point for Claude Agent SDK.

Provides commands for server management and resource listing.
"""
import click

from cli.commands.serve import serve_command
from cli.commands.list import skills_command, agents_command, subagents_command, sessions_command
from cli.commands.chat import chat_command


@click.group()
def cli():
    """Claude Agent SDK CLI.

    Manage the FastAPI server, interact with the API, and list resources.
    """
    pass


@cli.command()
@click.option('--api-url', default='http://localhost:7001', help='API server URL')
def api(api_url):
    """Start interactive chat via API.

    Opens an interactive conversation with Claude using the API server.
    Make sure the server is running first (use: python main.py serve)
    """
    chat_command(api_url)


@cli.command()
@click.option('--host', default='0.0.0.0', help='Server host')
@click.option('--port', default=7001, help='Server port')
@click.option('--reload', is_flag=True, help='Enable auto-reload')
def serve(host, port, reload):
    """Start FastAPI server.

    Launches the FastAPI server that provides HTTP/SSE endpoints for
    clients to interact with Claude Agent SDK.
    """
    serve_command(host=host, port=port, reload=reload)


@cli.command()
def skills():
    """List available skills.

    Displays all skills discovered from .claude/skills/ directory.
    """
    skills_command()


@cli.command()
def agents():
    """List available top-level agents.

    Displays all registered agents that can be selected via agent_id.
    """
    agents_command()


@cli.command()
def subagents():
    """List available subagents.

    Displays all delegation subagents used within conversations.
    """
    subagents_command()


@cli.command()
def sessions():
    """List conversation sessions.

    Shows session history from storage.
    """
    sessions_command()


if __name__ == "__main__":
    cli()
