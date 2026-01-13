"""Eval - LangGraph-based evaluation system for LiveKit voice agents.

Components:
    EvalRunner: Unified API for tests, evals, simulations
    test_workflow, eval_workflow, simulation_workflow, batch_workflow: LangGraph workflows
    TestResult, EvalResult, SimulationResult, BatchResult: Result types

Usage:
    python run_test.py "INT-001: Person confirms identity"
    python run_eval.py --file agent01_introduction.yaml
    python run_simulation.py --persona difficult --max-turns 10
"""

from .runner import EvalRunner
from .schemas import (
    BatchResult,
    EvalResult,
    EventType,
    SimulationResult,
    TestResult,
    Turn,
    TurnEvent,
)
from .workflows import (
    test_workflow,
    eval_workflow,
    simulation_workflow,
    batch_workflow,
    thread_config,
)

__all__ = [
    # Runner
    "EvalRunner",
    # Types
    "EventType",
    "TurnEvent",
    "Turn",
    "TestResult",
    "EvalResult",
    "SimulationResult",
    "BatchResult",
    # Workflows
    "test_workflow",
    "eval_workflow",
    "simulation_workflow",
    "batch_workflow",
    "thread_config",
]
