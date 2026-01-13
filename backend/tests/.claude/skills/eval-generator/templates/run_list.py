#!/usr/bin/env python3
"""List available test cases."""
import sys
from pathlib import Path

_eval_dir = Path(__file__).parent
_agent_dir = _eval_dir.parent
if str(_agent_dir) not in sys.path:
    sys.path.insert(0, str(_agent_dir))

import click
from eval import EvalRunner
from eval.console import print_test_list


@click.command()
@click.option("--file", "-f", help="Filter by test file")
@click.option("--tags", "-t", help="Filter by tags (comma-separated)")
def main(file, tags):
    """List available test cases.

    Examples:
        python run_list.py
        python run_list.py --file agent01_introduction.yaml
        python run_list.py --tags unit,introduction
    """
    runner = EvalRunner()
    tags_list = tags.split(",") if tags else None
    test_cases = runner.load_tests(file=file, tags=tags_list)
    print_test_list(test_cases)


if __name__ == "__main__":
    main()
