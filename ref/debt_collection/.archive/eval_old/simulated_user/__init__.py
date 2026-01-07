"""
Simulated User Module for LiveKit Voice Agent Testing

This module provides a LangChain/LangGraph-based simulated user
for automated conversation testing of LiveKit voice agents.

Usage:
    from simulated_user import simulate, SimulationResult

    # Run with defaults
    result = simulate()

    # Run with custom config
    result = simulate(config_path="custom_config.yaml")

    # Run with overrides
    result = simulate(
        model="gpt-4o",
        temperature=0.9,
        max_turns=15,
        start_agent="verification"
    )
"""

from .types import (
    Role,
    Message,
    TurnEvent,
    SimulationTurn,
    SimulationResult,
)
from .config import (
    SimulatedUserConfig,
    load_config,
    merge_runtime_config,
)
from .simulation import (
    run_simulation,
    run_simulation_async,
    simulate,
)
from .user_agent import SimulatedUserAgent
from .session_runner import AgentSessionRunner
from .console import SimulationConsole

__all__ = [
    # Types
    "Role",
    "Message",
    "TurnEvent",
    "SimulationTurn",
    "SimulationResult",
    # Config
    "SimulatedUserConfig",
    "load_config",
    "merge_runtime_config",
    # Simulation
    "run_simulation",
    "run_simulation_async",
    "simulate",
    # Components
    "SimulatedUserAgent",
    "AgentSessionRunner",
    "SimulationConsole",
]
