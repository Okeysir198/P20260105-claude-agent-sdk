#!/usr/bin/env python3
"""Promptfoo integration for running evaluations with web UI."""
import sys
from pathlib import Path

_eval_dir = Path(__file__).parent
_agent_dir = _eval_dir.parent
if str(_agent_dir) not in sys.path:
    sys.path.insert(0, str(_agent_dir))

import click


@click.command()
@click.argument("pattern", required=False)
@click.argument("limit", required=False, type=int)
@click.option("--tags", "-t", help="Filter tests by tags (comma-separated)")
@click.option("--model", "-m", default=None, help="LLM model (default: from config)")
@click.option("--temperature", "-T", default=None, type=float, help="LLM temperature (default: from config)")
@click.option("--versions", "-V", multiple=True, help="Prompt versions to compare (e.g., -V v1 -V v2, default: active_version from agent.yaml)")
@click.option("--view/--no-view", default=True, help="Open web UI after evaluation (default: True)")
@click.option("--generate-only", is_flag=True, help="Only generate config, don't run")
@click.option("--view-only", is_flag=True, help="Only open web UI to browse previous results")
@click.option("--stats-only", is_flag=True, help="Only show test case statistics")
@click.option("--verbose", is_flag=True, help="Verbose output")
def main(pattern, limit, tags, model, temperature, versions, view, generate_only, view_only, stats_only, verbose):
    """Run promptfoo evaluation.

    PATTERN can be:
      - Test code prefix: "INT" (runs all tests starting with "INT")
      - YAML file: agent01_introduction.yaml
      - Number: 5 (runs first 5 tests)
      - Empty: runs all tests (or filtered by --tags)

    LIMIT (optional): Number of test cases to run

    Examples:
        python run_promptfoo.py INT 2          # Run 2 tests starting with "INT"
        python run_promptfoo.py INT            # Run all tests starting with "INT"
        python run_promptfoo.py agent01.yaml 2 # Run 2 tests from file
        python run_promptfoo.py 5              # Run first 5 tests
        python run_promptfoo.py --tags unit
        python run_promptfoo.py -V v2          # Use specific version
        python run_promptfoo.py -T 0.5         # Use temperature 0.5
        python run_promptfoo.py -V v1 -V v2    # Compare versions
        python run_promptfoo.py --generate-only
        python run_promptfoo.py --view-only
        python run_promptfoo.py --stats-only
    """
    # Handle view-only mode
    if view_only:
        from eval.promptfoo.runner import view_results
        sys.exit(view_results())

    # Handle stats-only mode
    if stats_only:
        from eval.promptfoo.config_generator import get_test_stats
        tags_list = [t.strip() for t in tags.split(",")] if tags else None
        stats = get_test_stats(tags=tags_list)
        click.echo(f"\nTotal test cases: {stats['total']}")
        click.echo("\nBy file:")
        for file, count in stats['by_file'].items():
            click.echo(f"  {file}: {count}")
        click.echo(f"\nAvailable tags: {', '.join(stats['all_tags'])}")
        sys.exit(0)

    from eval.promptfoo.runner import run_eval

    # Handle number-only pattern (e.g., "5" means first 5 tests)
    if pattern and pattern.isdigit():
        limit = int(pattern)
        pattern = None

    tags_list = [t.strip() for t in tags.split(",")] if tags else None

    # Build versions list: explicit -V > None (use active_version)
    versions_list = list(versions) if versions else None

    sys.exit(run_eval(
        pattern=pattern,
        limit=limit,
        tags=tags_list,
        versions=versions_list,
        model=model,
        temperature=temperature,
        view=view,
        generate_only=generate_only,
        verbose=verbose,
    ))


if __name__ == "__main__":
    main()
