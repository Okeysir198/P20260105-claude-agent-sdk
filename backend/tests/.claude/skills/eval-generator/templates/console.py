"""Rich console output utilities."""

from typing import Optional

from rich.console import Console
from rich.table import Table
from rich import box

from .schemas.models import (
    TestResult, EvalResult, SimulationResult, BatchResult,
    Turn, TurnEvent, EventType
)

# Shared console instance
console = Console()


def print_config_info(
    model: str,
    temperature: float,
    version: Optional[str] = None,
    start_agent: Optional[str] = None,
):
    """Print configuration info at startup."""
    parts = [f"Model: {model}", f"Temperature: {temperature}"]
    if version:
        parts.append(f"Version: {version}")
    if start_agent:
        parts.append(f"Agent: {start_agent}")
    console.print(f"[dim]{' | '.join(parts)}[/dim]")


def get_status_display(passed: int, failed: int, error: Optional[str] = None) -> str:
    """Generate Rich-formatted status text."""
    total = passed + failed
    if error:
        return f"[red]ERROR: {error[:50]}...[/red]" if len(error) > 50 else f"[red]ERROR: {error}[/red]"
    if failed > 0:
        return f"[red]FAIL {passed}/{total} passed[/red]"
    return f"[green]PASS {passed}/{total} passed[/green]"


def print_header(title: str, subtitle: str = None):
    """Print a section header."""
    if subtitle:
        console.print(f"\n[bold cyan]{title}[/bold cyan] [dim]{subtitle}[/dim]")
    else:
        console.print(f"\n[bold cyan]{title}[/bold cyan]")
    console.print("-" * 60)


def print_turn(turn: Turn, show_events: bool = True):
    """Print a single conversation turn."""
    if turn.user_input != "[session_start]":
        console.print(f"[bold blue]User:[/bold blue] {turn.user_input}")

    if turn.agent_response:
        console.print(f"[bold green]Agent:[/bold green] {turn.agent_response}")

    if show_events and turn.events:
        for event in turn.events:
            if event.type == EventType.TOOL_CALL:
                name = event.content.get("name", "unknown")
                args = event.content.get("arguments", {})
                console.print(f"  [dim]-> Tool: {name}({args})[/dim]")
            elif event.type == EventType.TOOL_OUTPUT:
                result = event.content.get("result", "")
                is_error = event.content.get("is_error", False)
                # Truncate long results
                display = result[:200] + "..." if len(result) > 200 else result
                if is_error:
                    console.print(f"  [red]<- Error: {display}[/red]")
                else:
                    console.print(f"  [dim]<- Result: {display}[/dim]")
            elif event.type == EventType.HANDOFF:
                from_agent = event.content.get("from_agent", "?")
                to_agent = event.content.get("to_agent", "?")
                console.print(f"  [yellow]-> Handoff: {from_agent} -> {to_agent}[/yellow]")


def print_result(result: TestResult, show_events: bool = True):
    """Print a test result."""
    # Header
    status = "[green]PASSED[/green]" if not result.error else "[red]FAILED[/red]"
    console.print(f"\n[bold]{result.test_name}[/bold] {status}")
    console.print(f"[dim]Duration: {result.duration_ms:.0f}ms | Turns: {result.total_turns}[/dim]")
    console.print()

    # Turns
    for turn in result.turns:
        print_turn(turn, show_events=show_events)
        console.print()

    # Error
    if result.error:
        console.print(f"[red]Error: {result.error}[/red]")


def print_eval_result(result: EvalResult, show_events: bool = True):
    """Print an evaluation result with assertions."""
    # Header
    status = get_status_display(result.passed_count, result.failed_count)
    console.print(f"\n[bold]{result.test_name}[/bold] {status}")
    console.print(f"[dim]Score: {result.score:.0%} | Duration: {result.duration_ms:.0f}ms[/dim]")
    console.print()

    # Turns
    for turn in result.turns:
        print_turn(turn, show_events=show_events)
        console.print()

    # Assertions
    if result.assertions:
        console.print("[bold]Assertions:[/bold]")
        for a in result.assertions:
            assertion = a.get("assertion", {})
            passed = a.get("passed", False)
            message = a.get("message")

            icon = "[green]PASS[/green]" if passed else "[red]FAIL[/red]"
            atype = assertion.get("type", "?")
            value = assertion.get("value", "?")

            text = f"  {icon} {atype}: {value}"
            if message and not passed:
                text += f" [dim]({message})[/dim]"
            console.print(text)

    # Error
    if result.error:
        console.print(f"\n[red]Error: {result.error}[/red]")


def print_simulation_result(result: SimulationResult, show_events: bool = True):
    """Print a simulation result."""
    # Header
    status = "[green]Completed[/green]" if not result.error else "[red]Failed[/red]"
    console.print(f"\n[bold]Simulation: {result.persona}[/bold] {status}")
    console.print(f"[dim]Turns: {result.total_turns} | Stop: {result.stop_reason} | Duration: {result.duration_ms:.0f}ms[/dim]")
    console.print()

    # Turns
    for turn in result.turns:
        print_turn(turn, show_events=show_events)
        console.print()

    # Error
    if result.error:
        console.print(f"[red]Error: {result.error}[/red]")


def print_batch_result(result: BatchResult):
    """Print batch results summary."""
    # Summary
    status = get_status_display(result.passed_count, result.failed_count)
    console.print(f"\n[bold]Batch Results[/bold] {status}")
    console.print(f"[dim]Duration: {result.duration_ms:.0f}ms[/dim]")
    console.print()

    # Table
    table = Table(box=box.SIMPLE)
    table.add_column("Test", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Duration", justify="right")

    for r in result.results:
        if r.error or r.stop_reason == "error":
            status = "[red]FAIL[/red]"
        elif isinstance(r, EvalResult) and r.failed_count > 0:
            status = f"[yellow]WARN {r.passed_count}/{r.passed_count + r.failed_count}[/yellow]"
        else:
            status = "[green]PASS[/green]"

        table.add_row(r.test_name, status, f"{r.duration_ms:.0f}ms")

    console.print(table)

    # Failed details
    failed = [r for r in result.results if r.error]
    if failed:
        console.print("\n[bold red]Failed Tests:[/bold red]")
        for r in failed:
            console.print(f"  - {r.test_name}: {r.error}")


def print_test_list(test_cases: list[dict]):
    """Print list of available tests."""
    if not test_cases:
        console.print("[dim]No test cases found[/dim]")
        return

    table = Table(title=f"Test Cases ({len(test_cases)})", box=box.ROUNDED, show_lines=True)
    table.add_column("Name", style="cyan")
    table.add_column("Agent")
    table.add_column("Type")
    table.add_column("Tags")
    table.add_column("File", style="dim")

    for tc in test_cases:
        table.add_row(
            tc.get("name", "?"),
            tc.get("_sub_agent_id", "?"),
            tc.get("test_type", "single_turn"),
            ", ".join(tc.get("tags", [])),
            tc.get("_source_file", "?")
        )

    console.print(table)


# =========================================================================
# Streaming Output Functions
# =========================================================================

def print_stream_event(event: dict):
    """Print a streaming event in real-time with full content."""
    event_type = event.get("event", "")

    if event_type == "started":
        test_name = event.get("test_name", "Unknown")
        console.print(f"\n[bold cyan]Test:[/bold cyan] {test_name}")
        console.print("-" * 60)

    elif event_type == "user_input":
        content = event.get("content", "")
        turn = event.get("turn", "?")
        console.print(f"\n[bold blue]User:[/bold blue] {content}")

    elif event_type == "agent_response":
        content = event.get("content", "")
        console.print(f"[bold green]Agent:[/bold green] {content}")

    elif event_type == "turn_event":
        # Handle tool calls, tool outputs, handoffs
        etype = event.get("type", "")
        content = event.get("content", {})

        if etype == "tool_call":
            name = content.get("name", "unknown")
            args = content.get("arguments", {})
            console.print(f"  [dim]-> Tool: {name}({args})[/dim]")

        elif etype == "tool_output":
            result = content.get("result", "")
            is_error = content.get("is_error", False)
            if is_error:
                console.print(f"  [red]<- Error: {result}[/red]")
            else:
                console.print(f"  [dim]<- Result: {result}[/dim]")

        elif etype == "handoff":
            from_agent = content.get("from_agent", "?")
            to_agent = content.get("to_agent", "?")
            console.print(f"  [yellow]-> Handoff: {from_agent} -> {to_agent}[/yellow]")

        elif etype == "agent_message":
            # Additional agent message (already handled above)
            pass

    elif event_type == "completed":
        total = event.get("total_turns", 0)
        console.print(f"\n[dim]Completed: {total} turns[/dim]")

    # Legacy events for backward compatibility
    elif event_type == "greeting":
        content = event.get("content", "")
        console.print(f"[bold green]Agent:[/bold green] {content}")

    elif event_type == "turn_complete":
        pass  # Handled by agent_response now

    # Eval events
    elif event_type == "eval_started":
        test_name = event.get("test_name", "Unknown")
        console.print(f"\n[bold cyan]Eval:[/bold cyan] {test_name}")
        console.print("-" * 60)

    elif event_type == "assertion_result":
        passed = event.get("passed", False)
        atype = event.get("type", "?")
        value = event.get("value", "?")
        message = event.get("message")
        icon = "[green]PASS[/green]" if passed else "[red]FAIL[/red]"
        text = f"  {icon} {atype}: {value}"
        if message and not passed:
            console.print(f"{text}")
            console.print(f"       [dim]{message}[/dim]")
        else:
            console.print(text)

    elif event_type == "eval_completed":
        score = event.get("score", 0)
        passed = event.get("passed", 0)
        failed = event.get("failed", 0)
        console.print(f"\n[bold]Score: {score:.0%}[/bold] ({passed} passed, {failed} failed)")

    # Simulation events
    elif event_type == "simulation_started":
        persona = event.get("persona", "Unknown")
        max_turns = event.get("max_turns", "?")
        console.print(f"\n[bold cyan]Simulation:[/bold cyan] {persona} (max {max_turns} turns)")
        console.print("-" * 60)
        # Display agent and simulated user configs
        agent_cfg = event.get("agent_config", {})
        user_cfg = event.get("simulated_user_config", {})
        if agent_cfg:
            console.print(f"[dim]Agent:          {agent_cfg.get('model', '?')} | temp: {agent_cfg.get('temperature', '?')}[/dim]")
        if user_cfg:
            console.print(f"[dim]Simulated User: {user_cfg.get('model', '?')} | temp: {user_cfg.get('temperature', '?')}[/dim]")

    elif event_type == "turn":
        num = event.get("number", "?")
        user = event.get("user", "")
        agent = event.get("agent", "")
        console.print(f"\n[bold blue]User:[/bold blue] {user}")
        console.print(f"[bold green]Agent:[/bold green] {agent}")

    elif event_type == "simulation_completed":
        turns = event.get("turns", 0)
        stop_reason = event.get("stop_reason", "?")
        console.print(f"\n[dim]Completed: {turns} turns ({stop_reason})[/dim]")
