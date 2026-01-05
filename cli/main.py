"""Main CLI entry point for Claude Agent SDK.

Provides commands for interactive chat, server management, and resource listing.
"""
import click

from cli.commands.chat import chat_command
from cli.commands.serve import serve_command
from cli.commands.list import skills_command, agents_command, sessions_command


@click.group(invoke_without_command=True)
@click.option('--mode', type=click.Choice(['direct', 'api']), default='direct',
              help='Client mode: direct (Python SDK) or api (HTTP/SSE)')
@click.option('--api-url', default='http://localhost:19830',
              help='API server URL (for api mode)')
@click.option('--session-id', default=None,
              help='Session ID to resume')
@click.pass_context
def cli(ctx, mode, api_url, session_id):
    """Claude Agent SDK CLI.

    Start an interactive chat session with Claude using Skills and Subagents.
    """
    ctx.ensure_object(dict)
    ctx.obj['mode'] = mode
    ctx.obj['api_url'] = api_url
    ctx.obj['session_id'] = session_id

    if ctx.invoked_subcommand is None:
        # Default to chat command
        ctx.invoke(chat)


@cli.command()
@click.pass_context
def chat(ctx):
    """Start interactive chat session.

    Opens an interactive conversation with Claude. Supports both direct SDK
    mode and API mode via HTTP/SSE.
    """
    chat_command(ctx)


@cli.command()
@click.option('--host', default='0.0.0.0', help='Server host')
@click.option('--port', default=19830, help='Server port')
@click.option('--reload', is_flag=True, help='Enable auto-reload')
def serve(host, port, reload):
    """Start FastAPI server for API mode.

    Launches the FastAPI server that provides HTTP/SSE endpoints for
    remote clients to interact with Claude Agent SDK.
    """
    serve_command(host=host, port=port, reload=reload)


@cli.command()
@click.pass_context
def skills(ctx):
    """List available skills.

    Displays all skills discovered from .claude/skills/ directory or
    from the API server (depending on mode).
    """
    skills_command(ctx)


@cli.command()
@click.pass_context
def agents(ctx):
    """List available subagents.

    Displays all registered subagents with their descriptions.
    """
    agents_command(ctx)


@cli.command()
@click.pass_context
def sessions(ctx):
    """List conversation sessions.

    In direct mode: Shows local session history.
    In API mode: Shows active sessions on the server.
    """
    sessions_command(ctx)


if __name__ == "__main__":
    cli()
