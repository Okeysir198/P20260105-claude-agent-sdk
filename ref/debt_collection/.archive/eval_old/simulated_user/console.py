"""
Rich Console Output for Simulated User Testing

Provides formatted console output for simulation runs with consistent styling.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box

if TYPE_CHECKING:
    from .config import SimulatedUserConfig
    from .runner import SimulationResult

# Shared console instance
console = Console()


class SimulationConsole:
    """Console output handler for simulation runs."""

    def __init__(self, config: SimulatedUserConfig) -> None:
        """Initialize with configuration for output settings.

        Args:
            config: Configuration containing verbose and show_tool_calls settings.
        """
        self.verbose = config.verbose
        self.show_tool_calls = config.show_tool_calls

    def print_header(self, config: SimulatedUserConfig) -> None:
        """Print simulation header with configuration info.

        Args:
            config: Configuration to display in the header.
        """
        lines = [
            f"Agent: {config.agent_name}",
            f"Simulated User: {config.simulated_user_name}",
        ]
        if config.goal:
            lines.append(f"Goal: {config.goal}")

        text = Text()
        text.append("Simulation Info\n", style="bold cyan")
        for line in lines:
            text.append(f"{line}\n", style="dim")

        console.print(Panel(text, box=box.DOUBLE, border_style="cyan"))

    def print_turn_separator(self, turn: int) -> None:
        """Print a turn separator line.

        Args:
            turn: The turn number to display.
        """
        console.print(f"\n[bold]--- Turn {turn} ---[/bold]")

    def print_user_message(self, message: str, turn: int) -> None:
        """Print a simulated user message.

        Args:
            message: The user's message text.
            turn: The current turn number (prints separator if > 0).
        """
        if turn > 0:
            self.print_turn_separator(turn)
        console.print(f"[bold blue]SIMULATED USER:[/bold blue] {message}")

    def print_agent_message(self, message: str, turn: int = 0) -> None:
        """Print an agent response message.

        Args:
            message: The agent's message text.
            turn: The current turn number (unused, for API consistency).
        """
        console.print(f"[bold green]AGENT:[/bold green] {message}")

    def print_events(self, events: list) -> None:
        """Print events like tool calls, outputs, and handoffs.

        Only prints if show_tool_calls is enabled in config.

        Args:
            events: List of event objects/dicts to display.
        """
        if not self.show_tool_calls:
            return

        for event in events:
            event_type = event.type if hasattr(event, "type") else event.get("type", "")
            content = event.content if hasattr(event, "content") else event.get("content", {})

            if event_type == "tool_call":
                name = content.get("name", "")
                args = content.get("arguments", {})
                if isinstance(args, dict):
                    args_str = ", ".join(f"{k}={v}" for k, v in args.items())
                else:
                    args_str = str(args)
                console.print(f"[yellow][Tool: {name}({args_str})][/yellow]")

            elif event_type == "tool_output":
                result = str(content.get("result", ""))
                if len(result) > 60:
                    result = result[:60] + "..."
                console.print(f"[dim]Output: {result}[/dim]")

            elif event_type == "handoff":
                from_agent = content.get("from_agent", "unknown")
                to_agent = content.get("to_agent", "unknown")
                console.print(f"[magenta][Handoff: {from_agent} -> {to_agent}][/magenta]")

    def print_error(self, message: str) -> None:
        """Print an error message.

        Args:
            message: The error message to display.
        """
        console.print(f"[red][bold]ERROR:[/bold] {message}[/red]")

    def print_summary(self, result: SimulationResult) -> None:
        """Print simulation summary with final status.

        Args:
            result: The simulation result containing turns, stop_reason, and error.
        """
        console.print("\n" + "-" * 40)

        has_error = result.error is not None
        status_style = "red" if has_error else "green"

        console.print(f"[{status_style}]Simulation Complete[/{status_style}]")
        console.print(f"Total Turns: {len(result.turns)}")
        console.print(f"Stop Reason: {result.stop_reason}")

        if result.error:
            console.print(f"[red]Error: {result.error}[/red]")
