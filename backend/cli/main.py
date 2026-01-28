"""Main CLI entry point for Claude Agent SDK.

Provides commands for resource listing, direct chat, and server management.
"""
import click
from pathlib import Path

# Load .env file from backend directory
from dotenv import load_dotenv
backend_dir = Path(__file__).parent.parent
load_dotenv(backend_dir / ".env")

from cli.commands.list import skills_command, agents_command, subagents_command, sessions_command
from cli.commands.chat import chat_command
from cli.commands.serve import serve_command
from core.settings import get_settings

# Get centralized settings
_settings = get_settings()


@click.group()
def cli():
    """Claude Agent SDK CLI.

    Manage sessions and list resources.
    """
    pass


@cli.command()
@click.option('--api-url', default=f'http://localhost:{_settings.api.port}', help='API server URL')
@click.option('--mode', type=click.Choice(['ws', 'sse']), default='ws', help='Connection mode: ws (WebSocket) or sse (HTTP SSE)')
@click.option('--agent', default=None, help='Agent ID to use')
def chat(api_url, mode, agent):
    """Start interactive chat.

    Opens an interactive conversation with Claude using WebSocket (default)
    or HTTP SSE mode.

    Examples:
        python main.py chat                     # WebSocket mode (default)
        python main.py chat --mode sse          # HTTP SSE mode
        python main.py chat --agent my-agent    # Use specific agent
    """
    chat_command(api_url=api_url, mode=mode, agent_id=agent)


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
@click.option('--host', default=_settings.api.host, help='Host to bind to')
@click.option('--port', default=_settings.api.port, type=int, help='Port to bind to')
@click.option('--reload', is_flag=True, help='Enable auto-reload for development')
def serve(host, port, reload):
    """Start the FastAPI server.

    Starts the Agent SDK API server for HTTP + SSE streaming.
    """
    serve_command(host=host, port=port, reload=reload)


if __name__ == "__main__":
    cli()
