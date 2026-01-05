"""Console helper functions for Claude Agent SDK.

Contains Rich console utilities for formatted output.
"""
from rich.console import Console

# Global console instance for Rich output
console = Console()


def print_header(text: str, style: str = "bold white") -> None:
    """Print a section header."""
    console.print(f"\n[{style}]=== {text} ===[/{style}]")


def print_success(text: str) -> None:
    """Print a success message."""
    console.print(f"[green]{text}[/green]")


def print_warning(text: str) -> None:
    """Print a warning message."""
    console.print(f"[yellow]{text}[/yellow]")


def print_error(text: str) -> None:
    """Print an error message."""
    console.print(f"[red]{text}[/red]")


def print_info(text: str) -> None:
    """Print an info message."""
    console.print(f"[dim]{text}[/dim]")


def print_list_item(name: str, description: str, bullet: str = "•") -> None:
    """Print a list item with name and description."""
    console.print(f"  [yellow]{bullet}[/yellow] [bold]{name}[/bold]: {description}")


def print_command(cmd: str, description: str) -> None:
    """Print a command with description."""
    console.print(f"  [cyan]{cmd}[/cyan] - {description}")


def print_session_item(index: int, session_id: str, is_current: bool = False) -> None:
    """Print a session list item."""
    if is_current:
        console.print(f"  [green]{index}. {session_id} (current)[/green]")
    else:
        console.print(f"  [dim]{index}.[/dim] {session_id}")
