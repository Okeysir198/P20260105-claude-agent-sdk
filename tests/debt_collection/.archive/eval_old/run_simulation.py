#!/usr/bin/env python3
"""
Simulated User CLI for LiveKit Voice Agent Testing

Usage:
    python run_simulation.py
    python run_simulation.py --config custom.yaml
    python run_simulation.py --persona difficult --max-turns 10
    python run_simulation.py --goal "Negotiate a payment plan"
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add parent directories to path for imports
_script_dir = Path(__file__).parent
sys.path.insert(0, str(_script_dir))

from simulated_user.config import SimulatedUserConfig, load_config, merge_runtime_config
from simulated_user.console import console, SimulationConsole
from simulated_user.session_runner import AgentSessionRunner
from simulated_user.types import SimulationResult, SimulationTurn
from simulated_user.user_agent import SimulatedUserAgent

# Load presets from YAML config
import yaml


def load_presets(config_path: Path | str | None = None) -> dict:
    """Load preset personas from the config file.

    Args:
        config_path: Path to YAML config file. Uses default if None.

    Returns:
        Dictionary of preset name to preset configuration.
    """
    if config_path is None:
        config_path = _script_dir / "simulated_user_config.yaml"
    else:
        config_path = Path(config_path)

    if not config_path.exists():
        return {}

    with open(config_path) as f:
        raw = yaml.safe_load(f) or {}

    return raw.get("presets", {})


async def simulate(
    config_path: str | None = None,
    **overrides,
) -> SimulationResult:
    """Run a simulated conversation between a user and agent.

    Args:
        config_path: Optional path to YAML configuration file.
        **overrides: Configuration overrides from CLI arguments.
            Supported keys:
            - model: LLM model name
            - model_provider: Model provider (openai, anthropic)
            - temperature: Sampling temperature
            - persona_name: Display name for simulated user
            - system_prompt: Custom system prompt
            - persona_traits: List of personality traits
            - initial_message: First message from user
            - max_turns: Maximum conversation turns
            - start_agent: Which agent to start with
            - goal_description: Goal for simulated user
            - verbose: Enable verbose output
            - show_tool_calls: Show tool calls in output

    Returns:
        SimulationResult containing all turns and metadata.
    """
    # Load base config and merge overrides
    base_config = load_config(config_path)
    config = merge_runtime_config(base_config, overrides)

    # Create output console
    sim_console = SimulationConsole(config)

    if config.verbose:
        console.print("\n[bold cyan]Starting Simulation[/bold cyan]")
        console.print(f"Model: {config.model_provider}/{config.model}")
        console.print(f"Persona: {config.persona_name}")
        console.print(f"Starting Agent: {config.start_agent}")
        if config.goal_description:
            console.print(f"Goal: {config.goal_description[:80]}...")
        console.print()

    # Initialize components
    user_agent = SimulatedUserAgent(config)
    turns: list[SimulationTurn] = []
    stop_reason = "max_turns"
    error_message = None

    try:
        async with AgentSessionRunner(
            start_agent=config.start_agent,
            model=config.agent_model,
        ) as runner:
            # Get initial agent greeting
            initial_greeting = runner.get_initial_greeting()

            if initial_greeting and config.verbose:
                sim_console.print_agent_message(initial_greeting)

            # Check if agent greeting ends the conversation
            if initial_greeting and user_agent.should_stop(initial_greeting):
                stop_reason = "agent_ended"
                return SimulationResult(
                    turns=turns,
                    total_turns=0,
                    stop_reason=stop_reason,
                    metadata={
                        "config": {
                            "model": config.model,
                            "persona": config.persona_name,
                            "start_agent": config.start_agent,
                        }
                    },
                )

            # Main conversation loop
            for turn_num in range(1, config.max_turns + 1):
                # Generate user response to agent
                if turn_num == 1 and config.initial_message:
                    user_message = config.initial_message
                elif initial_greeting:
                    user_message = await user_agent.generate_response(initial_greeting)
                    initial_greeting = None  # Only use once
                else:
                    # This shouldn't happen - we need agent to speak first
                    user_message = config.initial_message or "Hello?"

                if config.verbose:
                    sim_console.print_user_message(user_message, turn_num)

                # Check if user message ends conversation
                if user_agent.should_stop(user_message):
                    turns.append(
                        SimulationTurn(
                            turn_number=turn_num,
                            user_message=user_message,
                            agent_response="",
                            events=[],
                        )
                    )
                    stop_reason = "user_ended"
                    break

                # Send to agent and get response
                agent_response, events = await runner.send_message(user_message)

                if config.verbose:
                    sim_console.print_events(events)
                    sim_console.print_agent_message(agent_response)

                # Record turn
                turns.append(
                    SimulationTurn(
                        turn_number=turn_num,
                        user_message=user_message,
                        agent_response=agent_response,
                        events=events,
                    )
                )

                # Check if agent response ends conversation
                if user_agent.should_stop(agent_response):
                    # Give user chance to say goodbye
                    final_response = await user_agent.generate_response(agent_response)

                    if config.verbose:
                        sim_console.print_user_message(final_response, turn_num + 1)

                    turns.append(
                        SimulationTurn(
                            turn_number=turn_num + 1,
                            user_message=final_response,
                            agent_response="",
                            events=[],
                        )
                    )
                    stop_reason = "agent_ended"
                    break

                # Prepare for next turn - generate user response to this agent message
                if turn_num < config.max_turns:
                    next_user_message = await user_agent.generate_response(agent_response)

                    # Store for next iteration
                    initial_greeting = None  # Clear any remaining

                    # Check if generated message would end conversation
                    if user_agent.should_stop(next_user_message):
                        if config.verbose:
                            sim_console.print_user_message(next_user_message, turn_num + 1)

                        turns.append(
                            SimulationTurn(
                                turn_number=turn_num + 1,
                                user_message=next_user_message,
                                agent_response="",
                                events=[],
                            )
                        )
                        stop_reason = "user_ended"
                        break

                    # Use generated message for next turn
                    config = merge_runtime_config(
                        config, {"initial_message": next_user_message}
                    )

    except KeyboardInterrupt:
        stop_reason = "user_ended"
        if config.verbose:
            console.print("\n[yellow]Interrupted by user[/yellow]")
    except Exception as e:
        stop_reason = "error"
        error_message = str(e)
        if config.verbose:
            sim_console.print_error(str(e))

    result = SimulationResult(
        turns=turns,
        total_turns=len(turns),
        stop_reason=stop_reason,
        error=error_message,
        metadata={
            "config": {
                "model": config.model,
                "persona": config.persona_name,
                "start_agent": config.start_agent,
            }
        },
    )

    if config.verbose:
        sim_console.print_summary(result)

    return result


def main():
    """CLI entry point for running simulations."""
    parser = argparse.ArgumentParser(
        description="Simulated User for LiveKit Voice Agent Testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_simulation.py
  python run_simulation.py --config my_config.yaml
  python run_simulation.py --persona difficult --max-turns 10
  python run_simulation.py --model gpt-4o --temperature 0.9
  python run_simulation.py --goal "Refuse to pay and ask for manager"
  python run_simulation.py --agent negotiation
  python run_simulation.py --json > result.json
        """,
    )

    # Config file
    parser.add_argument(
        "--config", "-c", type=str, help="Path to YAML config file"
    )

    # Model settings
    parser.add_argument(
        "--model", "-m", type=str, help="LLM model (e.g., gpt-4o-mini)"
    )
    parser.add_argument(
        "--provider",
        type=str,
        choices=["openai", "anthropic"],
        help="Model provider",
    )
    parser.add_argument(
        "--temperature", "-t", type=float, help="Temperature (0.0-1.0)"
    )

    # Persona settings
    parser.add_argument(
        "--persona",
        "-p",
        type=str,
        choices=["cooperative", "difficult", "confused", "third_party"],
        help="Use a preset persona",
    )
    parser.add_argument("--goal", "-g", type=str, help="Goal description")
    parser.add_argument(
        "--initial-message", type=str, help="Initial user message"
    )

    # Simulation settings
    parser.add_argument(
        "--max-turns", type=int, help="Maximum conversation turns"
    )
    parser.add_argument("--agent", "-a", type=str, help="Starting agent")

    # Output settings
    parser.add_argument(
        "--json", "-j", action="store_true", help="Output as JSON"
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Minimal output"
    )
    parser.add_argument(
        "--no-tools", action="store_true", help="Hide tool calls"
    )

    args = parser.parse_args()

    # Build overrides from CLI args
    overrides: dict = {}

    if args.model:
        overrides["model"] = args.model
    if args.provider:
        overrides["model_provider"] = args.provider
    if args.temperature is not None:
        overrides["temperature"] = args.temperature
    if args.goal:
        overrides["goal_description"] = args.goal
    if args.initial_message:
        overrides["initial_message"] = args.initial_message
    if args.max_turns:
        overrides["max_turns"] = args.max_turns
    if args.agent:
        overrides["start_agent"] = args.agent
    if args.quiet:
        overrides["verbose"] = False
    if args.no_tools:
        overrides["show_tool_calls"] = False

    # Handle preset personas
    if args.persona:
        presets = load_presets(args.config)
        if args.persona in presets:
            preset = presets[args.persona]
            overrides["persona_name"] = preset.get("name", args.persona)
            overrides["system_prompt"] = preset.get("system_prompt", "")
            overrides["persona_traits"] = preset.get("traits", [])

    # Run simulation
    try:
        result = asyncio.run(simulate(config_path=args.config, **overrides))

        if args.json:
            print(result.to_json())

    except KeyboardInterrupt:
        console.print("\n[yellow]Simulation interrupted[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        if not args.quiet:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
