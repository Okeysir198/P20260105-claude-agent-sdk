"""Main CLI entry point for Claude Agent SDK.

Provides commands for resource listing, direct chat, and server management.
"""
import click

from cli.commands.list import skills_command, agents_command, subagents_command, sessions_command
from cli.commands.chat import chat_command
from cli.commands.serve import serve_command


@click.group()
def cli():
    """Claude Agent SDK CLI.

    Manage sessions and list resources.
    """
    pass


@cli.command()
@click.option('--api-url', default='http://localhost:7001', help='API server URL')
def api(api_url):
    """Start interactive chat.

    Opens an interactive conversation with Claude.
    Note: API mode has been replaced. Use 'serve' command instead.
    """
    click.echo("API mode has been replaced. Use 'python main.py serve' to start the server.")


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


@cli.command()
@click.option('--host', default='0.0.0.0', help='Host to bind to')
@click.option('--port', default=7001, type=int, help='Port to bind to')
@click.option('--reload', is_flag=True, help='Enable auto-reload for development')
def serve(host, port, reload):
    """Start the FastAPI server.

    Starts the Agent SDK API server for HTTP + SSE streaming.
    """
    serve_command(host=host, port=port, reload=reload)


if __name__ == "__main__":
    cli()
