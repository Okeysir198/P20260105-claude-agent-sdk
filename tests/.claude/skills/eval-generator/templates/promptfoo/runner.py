"""
Promptfoo runner - wraps promptfoo CLI commands.

This module provides Python wrappers for running promptfoo evaluations,
viewing results, and managing the evaluation workflow.

Usage:
    from eval.promptfoo.runner import run_eval, view_results

    # Run evaluation
    exit_code = run_eval(tags=["unit"], view=True)

    # View previous results
    view_results()
"""

import subprocess
import shutil
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console

console = Console()


def check_promptfoo_installed() -> bool:
    """
    Check if promptfoo/npx is available.

    Returns:
        True if npx is installed and available
    """
    return shutil.which("npx") is not None


def run_eval(
    pattern: Optional[str] = None,
    limit: Optional[int] = None,
    tags: Optional[list[str]] = None,
    versions: Optional[list[str]] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    view: bool = False,
    generate_only: bool = False,
    verbose: bool = False,
) -> int:
    """
    Run promptfoo evaluation.

    This function:
    1. Generates promptfooconfig.yaml from test cases
    2. Runs promptfoo eval command
    3. Optionally opens the web UI

    Args:
        pattern: Test code prefix or YAML filename to filter tests
        limit: Maximum number of tests to run
        tags: Filter tests by tags
        versions: Prompt versions to compare side-by-side
        model: LLM model to use
        temperature: LLM temperature (0.0-2.0)
        view: Open web UI after evaluation
        generate_only: Only generate config, don't run
        verbose: Show detailed output

    Returns:
        Exit code (0 for success)
    """
    if not check_promptfoo_installed():
        console.print("[red]Error: npx not found. Install Node.js and run:[/red]")
        console.print("  npm install -g promptfoo")
        console.print("  # or use npx (no install needed)")
        return 1

    # Import here to avoid circular imports
    from .config_generator import generate_promptfoo_config, get_test_stats
    from ..core.config import get_config

    # Determine effective versions
    eval_cfg = get_config()
    if versions:
        effective_versions = list(versions)
    else:
        active = eval_cfg.get_active_version()
        effective_versions = [active] if active else ["default"]

    # Show test stats
    stats = get_test_stats(pattern=pattern, limit=limit, tags=tags)
    console.print(f"\n[bold]Found {stats['total']} test cases[/bold]")
    console.print(f"[dim]Versions: {', '.join(effective_versions)}[/dim]")
    if pattern:
        console.print(f"[dim]Filtered by pattern: {pattern}[/dim]")
    if tags:
        console.print(f"[dim]Filtered by tags: {', '.join(tags)}[/dim]")
    if limit:
        console.print(f"[dim]Limited to: {limit} tests[/dim]")

    if stats['total'] == 0:
        console.print("[yellow]No test cases found. Check your filters.[/yellow]")
        return 1

    # Generate config
    try:
        config_path = generate_promptfoo_config(
            pattern=pattern,
            limit=limit,
            versions=versions,
            tags=tags,
            model=model,
            temperature=temperature,
        )
        console.print(f"[green]Generated:[/green] {config_path}")
    except Exception as e:
        console.print(f"[red]Failed to generate config: {e}[/red]")
        return 1

    if generate_only:
        console.print("\n[dim]Config generated. Run without --generate-only to execute.[/dim]")
        return 0

    # Run promptfoo
    console.print("\n[bold]Running promptfoo evaluation...[/bold]")
    cmd = ["npx", "promptfoo", "eval", "-c", str(config_path)]

    if verbose:
        cmd.append("--verbose")

    try:
        result = subprocess.run(
            cmd,
            cwd=config_path.parent,
            check=False,
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]Evaluation interrupted[/yellow]")
        return 130

    # Show results location
    results_path = config_path.parent / "results.json"
    if results_path.exists():
        console.print(f"[dim]Results saved to: {results_path}[/dim]")

    # Check result status
    if result.returncode == 0:
        console.print("[green]Evaluation complete - all tests passed![/green]")
    else:
        console.print(f"[yellow]Evaluation complete with failures (code {result.returncode})[/yellow]")

    # Open web UI if requested (even if some tests failed)
    if view:
        console.print("\n[bold]Opening web UI...[/bold]")
        view_results(cwd=config_path.parent)

    return result.returncode


def view_results(cwd: Optional[Path] = None) -> int:
    """
    Open promptfoo web UI to browse results.

    Args:
        cwd: Working directory (default: eval folder)

    Returns:
        Exit code
    """
    if not check_promptfoo_installed():
        console.print("[red]Error: npx not found[/red]")
        return 1

    if cwd is None:
        from ..core.config import get_eval_dir
        cwd = get_eval_dir()

    console.print("[dim]Starting promptfoo web UI at http://localhost:15500[/dim]")
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")

    try:
        return subprocess.run(
            ["npx", "promptfoo", "view"],
            cwd=cwd,
        ).returncode
    except KeyboardInterrupt:
        console.print("\n[dim]Web UI stopped[/dim]")
        return 0


def list_results(cwd: Optional[Path] = None) -> int:
    """
    List previous evaluation results.

    Args:
        cwd: Working directory

    Returns:
        Exit code
    """
    if cwd is None:
        from ..core.config import get_eval_dir
        cwd = get_eval_dir()

    results_path = cwd / "results.json"
    if not results_path.exists():
        console.print("[yellow]No results found. Run an evaluation first.[/yellow]")
        return 1

    # Parse and display summary
    import json
    try:
        data = json.loads(results_path.read_text())
        results = data.get("results", [])
        console.print(f"\n[bold]Last evaluation: {len(results)} tests[/bold]")

        # Count pass/fail
        passed = sum(1 for r in results if r.get("success", False))
        failed = len(results) - passed

        if failed == 0:
            console.print(f"[green]All {passed} tests passed[/green]")
        else:
            console.print(f"[yellow]{passed} passed, {failed} failed[/yellow]")

    except Exception as e:
        console.print(f"[red]Failed to parse results: {e}[/red]")
        return 1

    return 0
