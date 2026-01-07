"""
Generic LiveKit Voice Agent Test Runner

Loads and runs tests from testcases/*.yaml files with rich output.
Works with any agent configured via agent.yaml.

Usage:
    cd agent_folder/eval
    python run_tests.py --list          # List all tests
    python run_tests.py                 # Run all tests
    python run_tests.py --file agent01_introduction.yaml
    python run_tests.py --test "Person confirms identity"
    python run_tests.py --tags unit,introduction
    python run_tests.py --interactive
    python run_tests.py --version v2    # Test v2 prompts
"""

from __future__ import annotations

import argparse
import asyncio
from rich.prompt import Prompt

from _console import (
    console, print_header, print_info, print_error,
    print_conversation_result, create_test_table, print_summary
)
from _provider import (
    load_test_cases, get_test_case, run_test_case,
    run_single_turn, run_conversation, ConversationResult,
    interactive_session, get_agent_ids, get_default_agent,
    set_version
)


# =============================================================================
# Test Listing
# =============================================================================

def list_tests(file: str | None = None, tags: list[str] | None = None) -> None:
    """List all tests from YAML files."""
    tests = load_test_cases(file=file)
    default_agent = get_default_agent()

    if tags:
        tests = [tc for tc in tests if any(t in tc.get("tags", []) for t in tags)]

    by_file = {}
    for tc in tests:
        f = tc["_source_file"]
        by_file.setdefault(f, []).append(tc)

    for filename, cases in sorted(by_file.items()):
        table = create_test_table(f"[cyan]{filename}[/cyan]")
        for tc in cases:
            table.add_row(
                tc["name"],
                tc.get("_sub_agent_id", default_agent),
                tc.get("test_type", "unknown"),
                ", ".join(tc.get("tags", []))
            )
        console.print(table)
        console.print()


# =============================================================================
# Test Running
# =============================================================================

def run_single_test(name: str, json_output: bool = False) -> ConversationResult | None:
    """Run a test by name."""
    tc = get_test_case(name)
    if not tc:
        print_error(f"Test not found: {name}")
        return None

    with console.status(f"[bold blue]Running: {name}...[/bold blue]"):
        result = run_test_case(tc)

    if json_output:
        console.print(result.to_json())
    else:
        print_conversation_result(result, tc["name"])

    return result


def run_tests(tests: list[dict], json_output: bool = False) -> tuple[int, int]:
    """Run multiple tests, return (passed, failed) counts."""
    passed = 0
    failed = 0

    for tc in tests:
        with console.status(f"[bold blue]Running: {tc['name']}...[/bold blue]"):
            result = run_test_case(tc)

        if json_output:
            console.print(f"--- {tc['name']} ---")
            console.print(result.to_json())
        else:
            print_conversation_result(result, tc["name"])

        if result.error:
            failed += 1
        else:
            passed += 1

    return passed, failed


def run_by_file(filename: str, json_output: bool = False) -> None:
    """Run all tests from a specific YAML file."""
    tests = load_test_cases(file=filename)
    if not tests:
        print_error(f"No tests found in: {filename}")
        return

    print_header(f"Running tests from {filename}", f"{len(tests)} test cases")
    passed, failed = run_tests(tests, json_output)
    print_summary(passed, failed, len(tests))


def run_by_tags(tags: list[str], json_output: bool = False) -> None:
    """Run tests matching tags."""
    tests = load_test_cases()
    matching = [tc for tc in tests if any(t in tc.get("tags", []) for t in tags)]

    if not matching:
        print_error(f"No tests found with tags: {tags}")
        return

    print_header(f"Running tests with tags: {', '.join(tags)}", f"{len(matching)} test cases")
    passed, failed = run_tests(matching, json_output)
    print_summary(passed, failed, len(matching))


def run_all_tests(json_output: bool = False) -> None:
    """Run all tests from all YAML files."""
    tests = load_test_cases()

    if not tests:
        print_error("No tests found in testcases/*.yaml")
        return

    print_header("Running All Tests", f"{len(tests)} test cases")
    passed, failed = run_tests(tests, json_output)
    print_summary(passed, failed, len(tests))


# =============================================================================
# Interactive Mode
# =============================================================================

def interactive_mode() -> None:
    """Interactive chat mode with persistent session."""
    default_agent = get_default_agent()
    print_header("Interactive Mode", "Type 'quit' to exit, 'reset' to start over")

    # Status spinner for thinking indicator
    status = None

    async def get_input():
        """Get user input (runs in executor to avoid blocking)."""
        try:
            loop = asyncio.get_event_loop()
            user_input = await loop.run_in_executor(
                None, lambda: Prompt.ask("\n[bold blue]You[/bold blue]")
            )
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Exiting...[/dim]")
            return None

        if user_input.lower() == 'quit':
            return None
        elif user_input.lower() == 'reset':
            print_info("Conversation reset")
            return "reset"
        return user_input

    async def on_output(turn_result):
        """Handle output from a turn."""
        for event in turn_result.events:
            if event.type == "assistant_message":
                console.print(f"[bold green]Agent:[/bold green] {event.content['text']}")
            elif event.type == "tool_call":
                console.print(f"  [dim][Tool: {event.content['name']}][/dim]")
            elif event.type == "error":
                print_error(event.content.get("message", "Unknown error"))

    def on_thinking_start():
        nonlocal status
        status = console.status("[bold blue]Thinking...[/bold blue]")
        status.start()

    def on_thinking_end():
        nonlocal status
        if status:
            status.stop()
            status = None

    asyncio.run(interactive_session(
        start_agent=default_agent,
        get_input=get_input,
        on_output=on_output,
        on_thinking_start=on_thinking_start,
        on_thinking_end=on_thinking_end
    ))


# =============================================================================
# Main
# =============================================================================

def main() -> None:
    # Get dynamic agent list from config
    agent_ids = get_agent_ids()
    default_agent = get_default_agent()

    parser = argparse.ArgumentParser(
        description="LiveKit Voice Agent Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  python run_tests.py --list
  python run_tests.py --file agent01_introduction.yaml
  python run_tests.py --test "Person confirms identity"
  python run_tests.py --tags unit,introduction
  python run_tests.py --interactive
  python run_tests.py --version v2
  python run_tests.py --version v1 --file agent01_introduction.yaml

Available agents: {', '.join(agent_ids)}
Default agent: {default_agent}
        """
    )

    parser.add_argument("--list", "-l", action="store_true", help="List all tests")
    parser.add_argument("--file", "-f", type=str, help="Run tests from YAML file")
    parser.add_argument("--test", "-t", type=str, help="Run specific test by name")
    parser.add_argument("--tags", type=str, help="Filter by tags (comma-separated)")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    parser.add_argument("--input", type=str, help="Run custom input")
    parser.add_argument("--agent", "-a",
                        choices=agent_ids if agent_ids else None,
                        default=default_agent,
                        help=f"Target agent for custom input (default: {default_agent})")
    parser.add_argument("--version", "-v", type=str, default=None,
                        help="Prompt version to use (e.g., v1, v2)")

    args = parser.parse_args()
    tags = [t.strip() for t in args.tags.split(",")] if args.tags else None

    # Set version globally if specified
    if args.version:
        set_version(args.version)
        print_info(f"Using prompt version: {args.version}")

    if args.list:
        print_header("Available Tests")
        list_tests(file=args.file, tags=tags)

    elif args.interactive:
        interactive_mode()

    elif args.input:
        with console.status("[bold blue]Running...[/bold blue]"):
            result = run_single_turn(args.input, target_agent=args.agent)
        if args.json:
            console.print(result.to_json())
        else:
            print_conversation_result(result, f"Custom Input ({args.agent})")

    elif args.test:
        run_single_test(args.test, json_output=args.json)

    elif args.file:
        run_by_file(args.file, json_output=args.json)

    elif tags:
        run_by_tags(tags, json_output=args.json)

    else:
        run_all_tests(json_output=args.json)


if __name__ == "__main__":
    main()
