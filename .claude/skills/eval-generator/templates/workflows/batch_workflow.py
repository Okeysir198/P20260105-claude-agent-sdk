"""Batch workflow - parallel test execution with concurrency control."""
import time
import uuid
import asyncio
from typing import Optional, Literal

from langgraph.func import entrypoint, task
from langgraph.config import get_stream_writer, get_config, RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver

from .test_workflow import test_workflow, checkpointer, thread_config
from .eval_workflow import eval_workflow
from ..schemas.models import TestResult, EvalResult, BatchResult


@task
async def run_single_in_batch(
    test_case: dict,
    workflow_type: Literal["test", "eval"],
    model: Optional[str] = None
) -> TestResult:
    """Run a single test case as part of a batch."""
    inner_thread = str(uuid.uuid4())
    config = thread_config(inner_thread)

    # Enrich test_case with runtime options (test_workflow expects these in the dict)
    # Note: model parameter is always passed from EvalRunner, use it directly
    enriched_case = {
        **test_case,
        "_runtime_model": model,
        "_runtime_temperature": test_case.get("_runtime_temperature", 0.2),
        "_runtime_start_agent": test_case.get("_runtime_start_agent"),
        "_runtime_version": test_case.get("_runtime_version"),
    }

    if workflow_type == "eval":
        return await eval_workflow.ainvoke(enriched_case, config=config)
    else:
        return await test_workflow.ainvoke(enriched_case, config=config)


@entrypoint(checkpointer=checkpointer)
async def batch_workflow(
    test_cases: list[dict],
    config: RunnableConfig | None = None,
) -> BatchResult:
    """Run multiple tests in parallel with concurrency control.

    Args:
        test_cases: List of test case dicts
        config: LangGraph config with configurable params:
            - workflow_type: "test" or "eval"
            - model: LLM model to use
            - max_concurrent: Max concurrent executions (default: 5)
    """
    # Get runtime params from config
    invocation_config = get_config()
    configurable = invocation_config.get("configurable", {})

    workflow_type: Literal["test", "eval"] = configurable.get("workflow_type", "test")
    model: Optional[str] = configurable.get("model")
    max_concurrent: int = configurable.get("max_concurrent", 5)

    start_time = time.time()
    writer = get_stream_writer()

    writer({"event": "batch_started", "total": len(test_cases)})

    if not test_cases:
        writer({"event": "batch_completed", "passed": 0, "failed": 0, "total": 0})
        return BatchResult(
            results=[],
            total=0,
            passed_count=0,
            failed_count=0,
            duration_ms=0
        )

    # Create semaphore for concurrency control
    semaphore = asyncio.Semaphore(max_concurrent)
    completed_count = 0

    async def run_with_semaphore(tc: dict, index: int) -> TestResult:
        nonlocal completed_count
        async with semaphore:
            try:
                result = await run_single_in_batch(tc, workflow_type, model)
                completed_count += 1
                is_passed = not (result.error or result.stop_reason == "error" or
                                (isinstance(result, EvalResult) and result.failed_count > 0))
                writer({
                    "event": "test_completed",
                    "name": tc.get("name", "Unknown"),
                    "passed": is_passed,
                    "index": index
                })
                return result
            except Exception as e:
                completed_count += 1
                writer({
                    "event": "test_completed",
                    "name": tc.get("name", "Unknown"),
                    "passed": False,
                    "index": index
                })
                # Return a failed result on error
                return TestResult(
                    turns=[],
                    total_turns=0,
                    duration_ms=0,
                    stop_reason="error",
                    error=str(e),
                    test_name=tc.get("name", "Unknown")
                )

    # Run all tests with concurrency control
    tasks = [run_with_semaphore(tc, i) for i, tc in enumerate(test_cases)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process results
    valid_results: list[TestResult] = []
    passed = 0
    failed = 0

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            # Handle unexpected exceptions
            failed += 1
            valid_results.append(TestResult(
                turns=[],
                total_turns=0,
                duration_ms=0,
                stop_reason="error",
                error=str(result),
                test_name="Unknown"
            ))
        else:
            valid_results.append(result)
            if result.error or result.stop_reason == "error":
                failed += 1
            elif isinstance(result, EvalResult) and result.failed_count > 0:
                failed += 1
            else:
                passed += 1

    writer({"event": "batch_completed", "passed": passed, "failed": failed, "total": len(test_cases)})

    duration_ms = (time.time() - start_time) * 1000

    return BatchResult(
        results=valid_results,
        total=len(test_cases),
        passed_count=passed,
        failed_count=failed,
        duration_ms=duration_ms
    )
