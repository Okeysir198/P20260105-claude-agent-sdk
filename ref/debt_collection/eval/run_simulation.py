#!/usr/bin/env python3
"""Run simulated user conversations."""
import sys
import asyncio
from pathlib import Path

_eval_dir = Path(__file__).parent
_agent_dir = _eval_dir.parent
if str(_agent_dir) not in sys.path:
    sys.path.insert(0, str(_agent_dir))

import click
from eval import EvalRunner
from eval.console import print_simulation_result, print_config_info, print_stream_event


async def run_with_streaming(runner: EvalRunner, overrides: dict):
    """Run simulation with real-time streaming output."""
    async for event in runner.astream_simulation({}, **overrides):
        print_stream_event(event)


@click.command()
@click.option("--persona", "-p", default="cooperative",
              help="Persona: cooperative, difficult, confused")
@click.option("--max-turns", "-n", type=int, default=20, help="Max turns")
@click.option("--agent", "-a", help="Starting agent")
@click.option("--goal", "-g", help="Goal description")
@click.option("--model", "-m", default=None, help="LLM model (default: from config)")
@click.option("--temperature", "-T", default=None, type=float, help="LLM temperature (default: from config)")
@click.option("--version", "-V", "version", help="Prompt version from agent.yaml versions")
@click.option("--json", "-j", "as_json", is_flag=True, help="Output as JSON (disables streaming)")
def main(persona, max_turns, agent, goal, model, temperature, version, as_json):
    """Run simulated user conversation with streaming output.

    Examples:
        python run_simulation.py
        python run_simulation.py --persona difficult --max-turns 10
        python run_simulation.py --goal "Refuse to make payment"
        python run_simulation.py -V v2            # Use prompt version v2
        python run_simulation.py -T 0.5           # Use temperature 0.5
        python run_simulation.py --json
    """
    runner = EvalRunner(model=model, temperature=temperature, version=version)

    overrides = {"max_turns": max_turns, "preset": persona}
    if agent:
        overrides["start_agent"] = agent
    if goal:
        overrides["goal_description"] = goal

    if as_json:
        result = runner.run_simulation({}, **overrides)
        click.echo(result.to_json())
    else:
        # Print config info before streaming
        print_config_info(runner.model, runner.temperature, runner.version, agent)
        # Default: streaming
        asyncio.run(run_with_streaming(runner, overrides))


if __name__ == "__main__":
    main()
