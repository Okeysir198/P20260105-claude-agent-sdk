"""
EvalRunner - THE unified API for tests, evals, and simulations.

This is the single entry point for all eval operations. Do not use workflow
helper functions directly - they have been removed to avoid API confusion.

Usage:
    runner = EvalRunner(model="gpt-4o-mini")

    # Synchronous
    result = runner.run_test(test_case)
    result = runner.run_eval(test_case)
    result = runner.run_simulation(config)
    result = runner.run_batch(test_cases)

    # Asynchronous
    result = await runner.arun_test(test_case)
    result = await runner.arun_eval(test_case)

    # Streaming
    async for event in runner.astream_test(test_case):
        print(event)
    async for event in runner.astream_eval(test_case):
        print(event)

For advanced LangGraph usage, import workflows directly:
    from eval.workflows import test_workflow, thread_config
    result = await test_workflow.ainvoke(test_case, config=thread_config())
"""

import asyncio
import logging
from typing import AsyncIterator, Iterator, Literal, Optional

from .core.config import get_config, ConfigurationError

logger = logging.getLogger(__name__)
from .core.loader import get_test_case, load_test_cases
from .schemas.models import BatchResult, EvalResult, SimulationResult, TestResult
from .workflows import (
    batch_workflow,
    eval_workflow,
    simulation_workflow,
    test_workflow,
    thread_config,
)


class EvalRunner:
    """Unified API for tests, evaluations, and simulations."""

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        version: Optional[str] = None,
    ) -> None:
        """Initialize runner with strict config resolution.

        Config priority (NO silent fallbacks):
            CLI override > version config > agent.yaml llm defaults

        Args:
            model: LLM model override (None = use config)
            temperature: LLM temperature override (None = use config)
            version: Agent version override (None = use active_version from agent.yaml)

        Raises:
            ConfigurationError: If version not found or no model/temperature configured
        """
        self.config = get_config()

        # Resolve version: CLI override > active_version from agent.yaml
        self.version = version or self.config.get_active_version()

        # Validate version exists if specified
        if self.version:
            self.config.validate_version(self.version)

        # Resolve model and temperature with strict validation
        # These methods raise ConfigurationError if no value is configured anywhere
        self.model = self.config.resolve_model(cli_override=model, version=self.version)
        self.temperature = self.config.resolve_temperature(cli_override=temperature, version=self.version)

    # =========================================================================
    # Test Methods
    # =========================================================================

    def run_test(
        self,
        test_case: dict,
        model: Optional[str] = None,
        start_agent: Optional[str] = None,
        version: Optional[str] = None,
    ) -> TestResult:
        """Run a test case synchronously."""
        return asyncio.run(self.arun_test(test_case, model, start_agent, version))

    async def arun_test(
        self,
        test_case: dict,
        model: Optional[str] = None,
        start_agent: Optional[str] = None,
        version: Optional[str] = None,
    ) -> TestResult:
        """Run a test case asynchronously."""
        # Pack runtime options into test_case for LangGraph (entrypoints only accept one input)
        enriched_case = {
            **test_case,
            "_runtime_model": model or self.model,
            "_runtime_temperature": self.temperature,
            "_runtime_start_agent": start_agent,
            "_runtime_version": version or self.version,
        }
        return await test_workflow.ainvoke(enriched_case, config=thread_config())  # type: ignore[attr-defined]

    async def astream_test(
        self,
        test_case: dict,
        model: Optional[str] = None,
        start_agent: Optional[str] = None,
        version: Optional[str] = None,
    ) -> AsyncIterator[dict]:
        """Stream test execution with real-time progress."""
        # Pack runtime options into test_case for LangGraph (entrypoints only accept one input)
        enriched_case = {
            **test_case,
            "_runtime_model": model or self.model,
            "_runtime_temperature": self.temperature,
            "_runtime_start_agent": start_agent,
            "_runtime_version": version or self.version,
        }

        langgraph_stream = test_workflow.astream(  # type: ignore[attr-defined]
            enriched_case,
            stream_mode=["custom"],
            config=thread_config(),
        )

        try:
            async for mode, chunk in langgraph_stream:
                yield chunk
                # Break after completed since LangGraph's astream doesn't properly signal completion
                if isinstance(chunk, dict) and chunk.get("event") == "completed":
                    logger.debug("Test workflow completed, closing stream")
                    break
        except GeneratorExit:
            # Generator was closed - propagate cancellation
            logger.info("Test workflow stream generator closed")
            await langgraph_stream.aclose()
            raise
        except asyncio.CancelledError:
            logger.info("Test workflow stream cancelled")
            await langgraph_stream.aclose()
            raise
        finally:
            await langgraph_stream.aclose()

    def stream_test(
        self,
        test_case: dict,
        model: Optional[str] = None,
        start_agent: Optional[str] = None,
        version: Optional[str] = None,
    ) -> list:
        """Stream test and return all chunks (sync wrapper)."""
        async def collect():
            chunks = []
            async for chunk in self.astream_test(test_case, model, start_agent, version):
                chunks.append(chunk)
            return chunks
        return asyncio.run(collect())

    # =========================================================================
    # Eval Methods
    # =========================================================================

    def run_eval(
        self,
        test_case: dict,
        model: Optional[str] = None,
        start_agent: Optional[str] = None,
        version: Optional[str] = None,
    ) -> EvalResult:
        """Run evaluation with assertions synchronously."""
        return asyncio.run(self.arun_eval(test_case, model, start_agent, version))

    async def arun_eval(
        self,
        test_case: dict,
        model: Optional[str] = None,
        start_agent: Optional[str] = None,
        version: Optional[str] = None,
    ) -> EvalResult:
        """Run evaluation asynchronously."""
        # Pack runtime options into test_case for LangGraph (entrypoints only accept one input)
        enriched_case = {
            **test_case,
            "_runtime_model": model or self.model,
            "_runtime_temperature": self.temperature,
            "_runtime_start_agent": start_agent,
            "_runtime_version": version or self.version,
        }
        return await eval_workflow.ainvoke(enriched_case, config=thread_config())  # type: ignore[attr-defined]

    async def astream_eval(
        self,
        test_case: dict,
        model: Optional[str] = None,
        start_agent: Optional[str] = None,
        version: Optional[str] = None,
    ) -> AsyncIterator[dict]:
        """Stream evaluation with real-time progress."""
        # Pack runtime options into test_case for LangGraph (entrypoints only accept one input)
        enriched_case = {
            **test_case,
            "_runtime_model": model or self.model,
            "_runtime_temperature": self.temperature,
            "_runtime_start_agent": start_agent,
            "_runtime_version": version or self.version,
        }

        langgraph_stream = eval_workflow.astream(  # type: ignore[attr-defined]
            enriched_case,
            stream_mode=["custom"],
            config=thread_config(),
        )

        try:
            async for mode, chunk in langgraph_stream:
                yield chunk
                # Break after eval_completed since LangGraph's astream doesn't properly signal completion
                if isinstance(chunk, dict) and chunk.get("event") == "eval_completed":
                    logger.debug("Eval workflow completed, closing stream")
                    break
        except GeneratorExit:
            # Generator was closed - propagate cancellation
            logger.info("Eval workflow stream generator closed")
            await langgraph_stream.aclose()
            raise
        except asyncio.CancelledError:
            logger.info("Eval workflow stream cancelled")
            await langgraph_stream.aclose()
            raise
        finally:
            await langgraph_stream.aclose()

    def stream_eval(
        self,
        test_case: dict,
        model: Optional[str] = None,
        start_agent: Optional[str] = None,
        version: Optional[str] = None,
    ) -> list:
        """Stream eval and return all chunks (sync wrapper)."""
        async def collect():
            chunks = []
            async for chunk in self.astream_eval(test_case, model, start_agent, version):
                chunks.append(chunk)
            return chunks
        return asyncio.run(collect())

    # =========================================================================
    # Simulation Methods
    # =========================================================================

    def run_simulation(
        self,
        config: Optional[dict] = None,
        **overrides,
    ) -> SimulationResult:
        """Run simulation synchronously."""
        return asyncio.run(self.arun_simulation(config, **overrides))

    async def arun_simulation(
        self,
        config: Optional[dict] = None,
        **overrides,
    ) -> SimulationResult:
        """Run simulation asynchronously."""
        # Pack everything into a single dict - LangGraph entrypoints only receive first arg
        sim_config = {
            **(config or {}),
            "_runtime_model": self.model,
            "_runtime_temperature": self.temperature,
            "_runtime_version": self.version,
            **overrides,
        }
        return await simulation_workflow.ainvoke(  # type: ignore[attr-defined]
            sim_config,
            config=thread_config(),
        )

    async def astream_simulation(
        self,
        config: Optional[dict] = None,
        **overrides,
    ) -> AsyncIterator[dict]:
        """Stream simulation with real-time progress."""
        # Pack everything into a single dict - LangGraph entrypoints only receive first arg
        sim_config = {
            **(config or {}),
            "_runtime_model": self.model,
            "_runtime_temperature": self.temperature,
            "_runtime_version": self.version,
            **overrides,
        }

        langgraph_stream = simulation_workflow.astream(  # type: ignore[attr-defined]
            sim_config,
            stream_mode=["custom"],
            config=thread_config(),
        )

        try:
            async for mode, chunk in langgraph_stream:
                yield chunk
                # Break after simulation_completed since LangGraph's astream doesn't properly signal completion
                if isinstance(chunk, dict) and chunk.get("event") == "simulation_completed":
                    logger.debug("Simulation workflow completed, closing stream")
                    break
        except GeneratorExit:
            # Generator was closed - propagate cancellation
            logger.info("Simulation workflow stream generator closed")
            await langgraph_stream.aclose()
            raise
        except asyncio.CancelledError:
            logger.info("Simulation workflow stream cancelled")
            await langgraph_stream.aclose()
            raise
        finally:
            await langgraph_stream.aclose()

    def stream_simulation(
        self,
        config: Optional[dict] = None,
        **overrides,
    ) -> list:
        """Stream simulation and return all chunks (sync wrapper)."""
        async def collect():
            chunks = []
            async for chunk in self.astream_simulation(config, **overrides):
                chunks.append(chunk)
            return chunks
        return asyncio.run(collect())

    # =========================================================================
    # Batch Methods
    # =========================================================================

    def run_batch(
        self,
        test_cases: list[dict],
        workflow: Literal["test", "eval"] = "test",
        max_concurrent: int = 5,
    ) -> BatchResult:
        """Run multiple tests synchronously."""
        return asyncio.run(self.arun_batch(test_cases, workflow, max_concurrent))

    async def arun_batch(
        self,
        test_cases: list[dict],
        workflow: Literal["test", "eval"] = "test",
        max_concurrent: int = 5,
    ) -> BatchResult:
        """Run multiple tests asynchronously."""
        # LangGraph entrypoints receive additional params via config['configurable']
        config = thread_config()
        config["configurable"] = {
            **config.get("configurable", {}),
            "workflow_type": workflow,
            "model": self.model,
            "max_concurrent": max_concurrent,
        }

        return await batch_workflow.ainvoke(  # type: ignore[attr-defined]
            test_cases,
            config=config,
        )

    def stream_batch(
        self,
        test_cases: list[dict],
        workflow: Literal["test", "eval"] = "test",
        max_concurrent: int = 5,
    ) -> Iterator:
        """Stream batch execution updates."""
        # LangGraph entrypoints receive additional params via config['configurable']
        config = thread_config()
        config["configurable"] = {
            **config.get("configurable", {}),
            "workflow_type": workflow,
            "model": self.model,
            "max_concurrent": max_concurrent,
        }

        for chunk in batch_workflow.stream(  # type: ignore[attr-defined]
            test_cases,
            stream_mode="updates",
            config=config,
        ):
            yield chunk

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def load_tests(
        self,
        file: Optional[str] = None,
        tags: Optional[list[str]] = None,
    ) -> list[dict]:
        """Load test cases from YAML files."""
        return load_test_cases(file=file, tags=tags)

    def get_test(self, name: str) -> Optional[dict]:
        """Get a single test case by name."""
        return get_test_case(name)
