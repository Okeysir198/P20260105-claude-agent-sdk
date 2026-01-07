#!/usr/bin/env python3
"""Interactive testing with persistent session."""
import sys
import asyncio
from pathlib import Path

_eval_dir = Path(__file__).parent
_agent_dir = _eval_dir.parent
if str(_agent_dir) not in sys.path:
    sys.path.insert(0, str(_agent_dir))

import click
from rich.console import Console
from rich.prompt import Prompt

from eval.core.config import get_config, ConfigurationError
from eval.core.session import TestSession
from eval.schemas import EventType

console = Console()


def print_events(events):
    """Print events from a turn."""
    for event in events:
        if event.type == EventType.TOOL_CALL:
            name = event.content.get("name", "unknown")
            args = event.content.get("arguments", {})
            console.print(f"  [dim]-> Tool: {name}({args})[/dim]")
        elif event.type == EventType.TOOL_OUTPUT:
            result = event.content.get("result", "")
            is_error = event.content.get("is_error", False)
            display = result
            if is_error:
                console.print(f"  [red]<- Error: {display}[/red]")
            else:
                console.print(f"  [dim]<- Result: {display}[/dim]")
        elif event.type == EventType.HANDOFF:
            from_agent = event.content.get("from_agent", "?")
            to_agent = event.content.get("to_agent", "?")
            console.print(f"  [yellow]-> Handoff: {from_agent} -> {to_agent}[/yellow]")


def print_test_data(userdata):
    """Print test data dynamically showing all profile fields."""
    if userdata is None:
        return

    from dataclasses import fields as dataclass_fields

    console.print("[bold cyan]Test Data[/bold cyan]")
    console.print("-" * 40)

    # Print debtor profile fields dynamically
    if hasattr(userdata, 'debtor') and userdata.debtor:
        console.print("[bold]Debtor Profile:[/bold]")
        debtor = userdata.debtor
        if hasattr(debtor, '__dataclass_fields__'):
            for field in dataclass_fields(debtor):
                value = getattr(debtor, field.name, None)
                if value is not None:
                    console.print(f"  [dim]{field.name}:[/dim] {value}")
        console.print()

    # Print call state fields dynamically
    if hasattr(userdata, 'call') and userdata.call:
        console.print("[bold]Call State:[/bold]")
        call = userdata.call
        if hasattr(call, '__dataclass_fields__'):
            for field in dataclass_fields(call):
                value = getattr(call, field.name, None)
                # Skip empty collections and None values
                if value is None:
                    continue
                if isinstance(value, (set, list, dict)) and not value:
                    continue
                console.print(f"  [dim]{field.name}:[/dim] {value}")

    console.print("-" * 40)
    console.print()


async def interactive_session(
    start_agent: str | None = None,
    model: str | None = None,
    temperature: float | None = None,
    version: str | None = None,
):
    """Run interactive session with persistent conversation.

    Config priority (NO silent fallbacks):
        CLI override > version config > agent.yaml llm defaults
    """
    # Resolve config with strict validation
    config = get_config()

    # Resolve version: CLI > active_version
    effective_version = version or config.get_active_version()
    if effective_version:
        config.validate_version(effective_version)

    # Resolve model and temperature (strict - raises if not configured)
    effective_model = config.resolve_model(cli_override=model, version=effective_version)
    effective_temp = config.resolve_temperature(cli_override=temperature, version=effective_version)

    console.print("\n[bold cyan]Interactive Mode[/bold cyan]")
    console.print(f"[dim]Model: {effective_model} | Temperature: {effective_temp}[/dim]")
    if effective_version:
        console.print(f"[dim]Version: {effective_version}[/dim]")
    console.print("[dim]Commands: quit, reset, clear, data[/dim]\n")

    while True:
        try:
            async with TestSession(
                start_agent=start_agent,
                model=effective_model,
                temperature=effective_temp,
                version=effective_version,
            ) as session:
                # Show test data
                print_test_data(session._userdata)

                # Show initial greeting with thinking animation
                with console.status("[bold blue]Agent thinking...[/bold blue]", spinner="dots"):
                    greeting = session.get_initial_greeting()

                if greeting:
                    console.print(f"[bold green]Agent:[/bold green] {greeting}\n")

                # Conversation loop
                while True:
                    try:
                        user_input = Prompt.ask("[bold blue]You[/bold blue]")
                    except (EOFError, KeyboardInterrupt):
                        console.print("\n[dim]Goodbye![/dim]")
                        return

                    if not user_input.strip():
                        continue

                    cmd = user_input.lower().strip()
                    if cmd == "quit" or cmd == "exit":
                        console.print("[dim]Goodbye![/dim]")
                        return
                    elif cmd == "reset":
                        console.print("[dim]Resetting session...[/dim]\n")
                        break  # Break inner loop to restart session
                    elif cmd == "clear":
                        console.clear()
                        continue
                    elif cmd == "data":
                        print_test_data(session._userdata)
                        continue

                    # Send message with thinking animation
                    try:
                        with console.status("[bold blue]Agent thinking...[/bold blue]", spinner="dots"):
                            response, events = await session.send_message(user_input)

                        # Print response
                        if response:
                            console.print(f"[bold green]Agent:[/bold green] {response}")

                        # Print events
                        if events:
                            print_events(events)

                        console.print()

                    except Exception as e:
                        console.print(f"[red]Error: {e}[/red]\n")

        except Exception as e:
            console.print(f"[red]Session error: {e}[/red]")
            console.print("[dim]Restarting session...[/dim]\n")


@click.command()
@click.option("--agent", "-a", help="Starting agent")
@click.option("--model", "-m", default=None, help="LLM model (default: from config)")
@click.option("--temperature", "-T", default=None, type=float, help="LLM temperature (default: from config)")
@click.option("--version", "-V", "version", help="Prompt version from agent.yaml versions")
def main(agent, model, temperature, version):
    """Interactive testing with persistent session.

    Start an interactive conversation with the agent. The session
    persists across messages, maintaining conversation context.
    Shows test data at session start.

    Commands:
        quit/exit - End the session
        reset     - Start a new session
        clear     - Clear the screen
        data      - Show test data again

    Examples:
        python run_interactive.py
        python run_interactive.py --agent introduction
        python run_interactive.py -V v2            # Use prompt version v2
        python run_interactive.py -T 0.5           # Use temperature 0.5
    """
    try:
        asyncio.run(interactive_session(
            start_agent=agent,
            model=model,
            temperature=temperature,
            version=version,
        ))
    except KeyboardInterrupt:
        console.print("\n[dim]Goodbye![/dim]")


if __name__ == "__main__":
    main()
