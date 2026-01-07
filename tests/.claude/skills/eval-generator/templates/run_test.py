#!/usr/bin/env python3
"""Run tests without assertions."""
import sys
import asyncio
from pathlib import Path

_eval_dir = Path(__file__).parent
_agent_dir = _eval_dir.parent
if str(_agent_dir) not in sys.path:
    sys.path.insert(0, str(_agent_dir))

import click
from eval import EvalRunner
from eval.console import print_header, print_config_info, print_stream_event
from eval.cli.cli_utils import common_options, parse_tags, resolve_test_pattern, run_streaming_loop


@click.command()
@common_options
def main(pattern, limit, tags, model, temperature, version, as_json):
    """Run test(s) with streaming output."""
    runner = EvalRunner(model=model, temperature=temperature, version=version)
    tags_list = parse_tags(tags)
    test_cases = resolve_test_pattern(pattern, limit, tags_list, runner.load_tests)

    if as_json:
        result = runner.run_batch(test_cases, workflow="test", max_concurrent=5)
        click.echo(result.to_json())
    else:
        print_header(f"Running {len(test_cases)} test(s)")
        print_config_info(runner.model, runner.temperature, runner.version)
        asyncio.run(run_streaming_loop(runner.astream_test, test_cases, print_stream_event))


if __name__ == "__main__":
    main()
