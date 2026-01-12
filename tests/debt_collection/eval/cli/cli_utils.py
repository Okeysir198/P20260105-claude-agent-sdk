"""Shared CLI utilities for run_test.py and run_eval.py."""

import sys
import asyncio
from typing import Callable, Optional, Any
import click


def parse_tags(tags_str: Optional[str]) -> Optional[list[str]]:
    """Parse comma-separated tags string into list."""
    return tags_str.split(",") if tags_str else None


def resolve_test_pattern(
    pattern: Optional[str],
    limit: Optional[int],
    tags: Optional[list[str]],
    load_tests_fn: Callable[[Optional[str], Optional[list[str]]], list[dict]],
) -> list[dict]:
    """Resolve pattern to list of test cases.

    Args:
        pattern: Test prefix, YAML filename, or None for all tests
        limit: Maximum number of tests to return
        tags: Filter by tags
        load_tests_fn: Function to load tests (file, tags) -> list[dict]

    Returns:
        List of test case dicts

    Raises:
        SystemExit: If no tests found
    """
    if pattern:
        if pattern.endswith(".yaml"):
            test_cases = load_tests_fn(pattern, tags)
            if not test_cases:
                click.echo(f"No test cases found in {pattern}", err=True)
                sys.exit(1)
        else:
            # Test code prefix mode
            all_tests = load_tests_fn(None, tags)
            test_cases = [tc for tc in all_tests if tc.get("name", "").startswith(pattern)]
            if not test_cases:
                click.echo(f"No tests found matching prefix: {pattern}", err=True)
                sys.exit(1)
    else:
        test_cases = load_tests_fn(None, tags)
        if not test_cases:
            click.echo("No test cases found", err=True)
            sys.exit(1)

    if limit:
        test_cases = test_cases[:limit]

    return test_cases


async def run_streaming_loop(
    stream_fn: Callable[[dict], Any],
    test_cases: list[dict],
    print_event_fn: Callable[[dict], None],
) -> None:
    """Run streaming execution for multiple test cases.

    Args:
        stream_fn: Async generator function that yields events
        test_cases: List of test cases to run
        print_event_fn: Function to print each event
    """
    for test_case in test_cases:
        async for event in stream_fn(test_case):
            print_event_fn(event)


def common_options(fn: Callable) -> Callable:
    """Apply common CLI options for test/eval commands.

    Note: model and temperature default to None so that config values are used.
    The EvalRunner will resolve: CLI > version config > agent.yaml llm defaults.
    """
    fn = click.option("--json", "-j", "as_json", is_flag=True, help="Output as JSON (concurrent execution)")(fn)
    fn = click.option("--version", "-V", "version", help="Prompt version from agent.yaml versions")(fn)
    fn = click.option("--temperature", "-T", default=None, type=float, help="LLM temperature (default: from config)")(fn)
    fn = click.option("--model", "-m", default=None, help="LLM model (default: from config)")(fn)
    fn = click.option("--tags", "-t", help="Filter by tags (comma-separated)")(fn)
    fn = click.argument("limit", required=False, type=int)(fn)
    fn = click.argument("pattern", required=False)(fn)
    return fn
