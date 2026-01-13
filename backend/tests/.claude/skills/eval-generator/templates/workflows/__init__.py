"""
LangGraph workflow entrypoints for the eval system.

This module exports the core workflow entrypoints for advanced LangGraph usage.
For most use cases, use EvalRunner from runner.py instead.

Workflows:
    test_workflow: Execute single/multi-turn tests against an agent
    eval_workflow: Execute tests with assertion evaluation
    simulation_workflow: Run simulated user conversations
    batch_workflow: Execute multiple tests in parallel

Utilities:
    thread_config: Create LangGraph config with thread ID
    checkpointer: Shared InMemorySaver for workflow state

Usage (advanced):
    >>> from eval.workflows import test_workflow, thread_config
    >>> result = await test_workflow.ainvoke(test_case, config=thread_config())

For standard usage, prefer EvalRunner:
    >>> from eval.runner import EvalRunner
    >>> runner = EvalRunner(model="gpt-4o-mini")
    >>> result = runner.run_test(test_case)
"""

from .test_workflow import test_workflow, thread_config, checkpointer
from .eval_workflow import eval_workflow
from .batch_workflow import batch_workflow
from .simulation_workflow import simulation_workflow

__all__ = [
    "test_workflow",
    "eval_workflow",
    "batch_workflow",
    "simulation_workflow",
    "thread_config",
    "checkpointer",
]
