"""
Rich Console Utilities for Debt Collection Agent Testing

Provides consistent, beautiful output across all test scripts.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

# Shared console instance
console = Console()


def print_header(title: str, subtitle: str | None = None) -> None:
    """Print a styled header."""
    text = Text(title, style="bold cyan")
    if subtitle:
        text.append(f"\n{subtitle}", style="dim")
    console.print(Panel(text, box=box.DOUBLE, border_style="cyan"))


def print_success(message: str) -> None:
    """Print success message."""
    console.print(f"[green][bold]>[/bold] {message}[/green]")


def print_error(message: str) -> None:
    """Print error message."""
    console.print(f"[red][bold]>[/bold] {message}[/red]")


def print_warning(message: str) -> None:
    """Print warning message."""
    console.print(f"[yellow][bold]>[/bold] {message}[/yellow]")


def print_info(message: str) -> None:
    """Print info message."""
    console.print(f"[blue][bold]>[/bold] {message}[/blue]")


def print_test_result(name: str, passed: bool, reason: str | None = None) -> None:
    """Print a single test result."""
    if passed:
        status = "[green][bold]PASS[/bold][/green]"
    else:
        status = "[red][bold]FAIL[/bold][/red]"

    console.print(f"  {status} {name}")
    if reason and not passed:
        console.print(f"        [dim]{reason}[/dim]")


def create_test_table(title: str = "Test Cases") -> Table:
    """Create a table for test listing."""
    table = Table(title=title, box=box.ROUNDED, show_lines=True)
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Agent", style="green")
    table.add_column("Type", style="yellow")
    table.add_column("Tags", style="dim")
    return table


def create_results_table(title: str = "Results") -> Table:
    """Create a table for results."""
    table = Table(title=title, box=box.ROUNDED)
    table.add_column("Test", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Details", style="dim")
    return table


def print_conversation_turn(turn_num: int, events: list, user_input: str = "") -> None:
    """Print a single conversation turn with rich formatting."""
    if user_input == "[session_start]":
        console.print(f"\n[bold]--- Agent Start ---[/bold]")
    else:
        console.print(f"\n[bold]--- Turn {turn_num} ---[/bold]")

    for event in events:
        event_type = event.type if hasattr(event, 'type') else event.get('type', '')
        content = event.content if hasattr(event, 'content') else event.get('content', {})

        if event_type == "user_input":
            text = content.get('text', '')
            if text and text != "[session_start]":
                console.print(f"  [bold blue]USER:[/bold blue] {text}")

        elif event_type == "assistant_message":
            text = content.get('text', '')
            console.print(f"  [bold green]ASSISTANT:[/bold green] {text}")

        elif event_type == "tool_call":
            name = content.get('name', '')
            args = content.get('arguments', {})
            if isinstance(args, dict):
                args_str = ", ".join(f"{k}={v}" for k, v in args.items())
            else:
                args_str = str(args)
            console.print(f"  [bold yellow]TOOL:[/bold yellow] {name}({args_str})")

        elif event_type == "tool_output":
            result = content.get('result', '')
            if len(result) > 60:
                result = result[:60] + "..."
            console.print(f"  [dim]TOOL OUTPUT: {result}[/dim]")

        elif event_type == "handoff":
            from_agent = content.get('from_agent', 'unknown')
            to_agent = content.get('to_agent', 'unknown')
            if from_agent == "unknown":
                console.print(f"  [bold magenta]STARTED:[/bold magenta] {to_agent}")
            else:
                console.print(f"  [bold magenta]HANDOFF:[/bold magenta] {from_agent} → {to_agent}")


def print_conversation_result(result, title: str = "") -> None:
    """Print full conversation result with rich formatting."""
    # Note: Title is not printed here to avoid duplication with print_test_separator()

    if hasattr(result, 'error') and result.error:
        print_error(f"Error: {result.error}")
        return

    turns = result.turns if hasattr(result, 'turns') else result.get('turns', [])

    turn_num = 0
    for turn in turns:
        events = turn.events if hasattr(turn, 'events') else turn.get('events', [])
        user_input = turn.user_input if hasattr(turn, 'user_input') else turn.get('user_input', '')

        if user_input != "[session_start]":
            turn_num += 1

        print_conversation_turn(turn_num, events, user_input)

    console.print()


def print_summary(passed: int, failed: int, total: int) -> None:
    """Print test summary."""
    console.print()

    if failed == 0:
        style = "bold green"
        icon = "[green][bold]>[/bold][/green]"
    else:
        style = "bold yellow" if passed > 0 else "bold red"
        icon = "[yellow][bold]>[/bold][/yellow]" if passed > 0 else "[red][bold]>[/bold][/red]"

    pct = (passed / total * 100) if total > 0 else 0
    console.print(f"{icon} [{style}]{passed}/{total} passed ({pct:.0f}%)[/{style}]")
