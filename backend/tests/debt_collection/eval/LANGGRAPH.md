# LangGraph Architecture Deep Dive

This eval framework is built entirely on **LangGraph Functional API** - a modern approach to building stateful, streaming workflows. Understanding these patterns is key to extending or integrating the framework.

## Why LangGraph?

| Requirement | LangGraph Solution |
|-------------|-------------------|
| Real-time streaming | `get_stream_writer()` emits events as they happen |
| State isolation | Thread configs provide per-invocation isolation |
| Checkpointing | `MemorySaver` preserves state across streaming chunks |
| Composability | `@task` decorators create reusable subtasks |
| Async-first | Native async with sync wrappers for convenience |

## Core Concepts

### 1. Entrypoints (`@entrypoint`)

Entrypoints are the main workflow entry points. They:
- Accept a single input (we pack everything into a dict)
- Support checkpointing for state persistence
- Enable streaming via `get_stream_writer()`
- Require thread configuration for isolation

```python
from langgraph.func import entrypoint
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()

@entrypoint(checkpointer=checkpointer)
async def test_workflow(test_case: dict) -> TestResult:
    """Main entry point for test execution."""
    writer = get_stream_writer()

    # Emit start event
    writer({"event": "started", "test_name": test_case["name"]})

    # ... workflow logic ...

    # Emit completion event
    writer({"event": "completed", "total_turns": len(turns)})

    return TestResult(turns=turns, duration_ms=duration)
```

### 2. Tasks (`@task`)

Tasks are reusable units of work called within entrypoints:

```python
from langgraph.func import task

@task
async def run_assertion(
    assertion: dict,
    user_input: str,
    agent_response: str,
    events: list
) -> dict:
    """Evaluate a single assertion against the response."""
    assertion_type = assertion["type"]
    value = assertion.get("value", "")

    if assertion_type == "contains":
        passed = value.lower() in agent_response.lower()
        return {"passed": passed, "message": f"Contains '{value}': {passed}"}

    elif assertion_type == "contains_function_call":
        tool_calls = [e for e in events if e["type"] == "tool_call"]
        passed = any(tc["name"] == value for tc in tool_calls)
        return {"passed": passed, "message": f"Tool '{value}' called: {passed}"}

    elif assertion_type == "llm_rubric":
        # Call LLM judge for semantic evaluation
        result = await evaluate_with_llm(user_input, agent_response, value)
        return result

    # ... other assertion types
```

### 3. Stream Writer Pattern

The `get_stream_writer()` function provides real-time event emission:

```python
from langgraph.config import get_stream_writer

@entrypoint(checkpointer=checkpointer)
async def eval_workflow(test_case: dict) -> EvalResult:
    writer = get_stream_writer()

    # Stream test execution events
    writer({"event": "started", "test_name": test_case["name"]})

    for i, turn in enumerate(test_case["turns"]):
        # Stream user input
        writer({"event": "user_input", "turn": i, "content": turn["user_input"]})

        # Execute turn
        response, events = await session.send_message(turn["user_input"])

        # Stream agent response
        writer({"event": "agent_response", "turn": i, "content": response})

        # Stream tool calls and handoffs
        for event in events:
            writer({"event": "turn_event", "turn": i, **event})

        # Stream assertion results
        for assertion in turn.get("assertions", []):
            result = await run_assertion(assertion, turn["user_input"], response, events)
            writer({"event": "assertion_result", "turn": i, **result})

    writer({"event": "eval_completed", "score": score})
    return EvalResult(...)
```

### 4. Thread Configuration

Each workflow invocation needs a unique thread ID for state isolation:

```python
from langgraph.types import RunnableConfig
import uuid

def thread_config(thread_id: str = None) -> RunnableConfig:
    """Generate thread config for workflow invocation."""
    return {
        "configurable": {
            "thread_id": thread_id or str(uuid.uuid4())
        }
    }

# Usage: Each test gets its own thread
for test_case in test_cases:
    config = thread_config()  # New UUID for each test
    result = await test_workflow.ainvoke(test_case, config=config)
```

## Workflow Invocation Patterns

### Pattern 1: Async Invoke (Wait for Result)

```python
# Simple async invocation - waits for completion
result = await test_workflow.ainvoke(
    test_case,
    config=thread_config()
)
print(f"Test completed: {result.status}")
```

### Pattern 2: Async Streaming (Real-time Events)

```python
# Stream events as they happen
async for mode, chunk in test_workflow.astream(
    test_case,
    stream_mode=["custom", "updates"],
    config=thread_config()
):
    if mode == "custom":
        # These are our writer() events
        event = chunk
        if event["event"] == "agent_response":
            print(f"Agent: {event['content']}")
        elif event["event"] == "assertion_result":
            status = "✓" if event["passed"] else "✗"
            print(f"  {status} {event['type']}: {event['value']}")
```

### Pattern 3: Sync Wrapper (For Scripts)

```python
import asyncio

def run_test(test_case: dict) -> TestResult:
    """Synchronous wrapper for scripts and simple usage."""
    return asyncio.run(test_workflow.ainvoke(
        test_case,
        config=thread_config()
    ))

# Usage in scripts
if __name__ == "__main__":
    result = run_test(test_case)
    print(f"Result: {result.status}")
```

### Pattern 4: Generator Streaming (Sync Context)

```python
def stream_test(test_case: dict):
    """Sync generator that yields events."""
    async def _stream():
        async for mode, chunk in test_workflow.astream(
            test_case,
            stream_mode=["custom"],
            config=thread_config()
        ):
            if mode == "custom":
                yield chunk

    # Run async generator in sync context
    loop = asyncio.new_event_loop()
    gen = _stream()
    try:
        while True:
            yield loop.run_until_complete(gen.__anext__())
    except StopAsyncIteration:
        pass
    finally:
        loop.close()

# Usage
for event in stream_test(test_case):
    print(event)
```

## Batch Execution with Concurrency Control

```python
import asyncio
from langgraph.func import entrypoint, task

@task
async def run_single_test(test_case: dict, semaphore: asyncio.Semaphore) -> TestResult:
    """Run single test with semaphore for concurrency control."""
    async with semaphore:
        return await test_workflow.ainvoke(test_case, config=thread_config())

@entrypoint(checkpointer=checkpointer)
async def batch_workflow(batch_input: dict) -> BatchResult:
    """Run multiple tests in parallel with concurrency limit."""
    writer = get_stream_writer()
    test_cases = batch_input["test_cases"]
    max_concurrent = batch_input.get("max_concurrent", 5)

    semaphore = asyncio.Semaphore(max_concurrent)
    writer({"event": "batch_started", "total": len(test_cases)})

    # Create all tasks
    tasks = [
        run_single_test(tc, semaphore)
        for tc in test_cases
    ]

    # Execute with concurrency control
    results = []
    for i, coro in enumerate(asyncio.as_completed(tasks)):
        result = await coro
        results.append(result)
        writer({
            "event": "test_completed",
            "index": i,
            "name": result.test_name,
            "passed": result.status == "passed"
        })

    passed = sum(1 for r in results if r.status == "passed")
    writer({"event": "batch_completed", "passed": passed, "total": len(results)})

    return BatchResult(results=results, passed_count=passed)
```

## Runtime Configuration Injection

Since LangGraph entrypoints accept only one input, we pack runtime options into the test case:

```python
@entrypoint(checkpointer=checkpointer)
async def test_workflow(test_case: dict) -> TestResult:
    # Extract runtime options (injected by EvalRunner)
    model = test_case.get("_runtime_model", "gpt-4o-mini")
    version = test_case.get("_runtime_version")
    temperature = test_case.get("_runtime_temperature", 0.0)
    start_agent = test_case.get("_runtime_start_agent", "introduction")

    # Extract test data (from YAML loader)
    test_data = test_case.get("_default_test_data", {})

    # Create session with runtime config
    async with TestSession(
        model=model,
        version=version,
        temperature=temperature,
        start_agent=start_agent,
        test_data=test_data
    ) as session:
        # ... execute test turns
```

**EvalRunner packs options before calling workflow:**

```python
class EvalRunner:
    def __init__(self, model="gpt-4o-mini", version=None):
        self.model = model
        self.version = version

    async def arun_test(self, test_case: dict, version: str = None) -> TestResult:
        # Pack runtime options into test_case
        enriched = {
            **test_case,
            "_runtime_model": self.model,
            "_runtime_version": version or self.version,
            "_runtime_temperature": 0.0,
        }
        return await test_workflow.ainvoke(enriched, config=thread_config())
```

## Checkpointer and State Management

The `MemorySaver` checkpointer enables:
- State persistence across streaming chunks
- Resumable workflows (if needed)
- Debugging and inspection

```python
from langgraph.checkpoint.memory import MemorySaver

# Single checkpointer instance for all workflows
checkpointer = MemorySaver()

@entrypoint(checkpointer=checkpointer)
async def test_workflow(test_case: dict) -> TestResult:
    # State is automatically checkpointed at each step
    # This enables streaming to work correctly
    pass
```

**Why checkpointing matters for streaming:**

```
Without checkpointer:
  astream() -> Error: Cannot stream without checkpointer

With checkpointer:
  astream() -> Yields events as workflow progresses
             -> State preserved between yields
             -> Final result available at end
```

## Error Handling in Workflows

```python
@entrypoint(checkpointer=checkpointer)
async def test_workflow(test_case: dict) -> TestResult:
    writer = get_stream_writer()

    try:
        writer({"event": "started", "test_name": test_case["name"]})

        async with TestSession(...) as session:
            turns = []
            for turn_data in test_case["turns"]:
                response, events = await session.send_message(turn_data["user_input"])
                turns.append({"response": response, "events": events})

        writer({"event": "completed", "status": "success"})
        return TestResult(turns=turns, status="passed")

    except Exception as e:
        # Stream error event
        writer({"event": "error", "message": str(e)})

        # Return error result (don't raise - let caller handle)
        return TestResult(
            turns=[],
            status="error",
            error=str(e)
        )
```

## Integration with FastAPI

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import json

app = FastAPI()

@app.post("/api/eval/stream")
async def stream_test(test_name: str, version: str = None):
    """Stream test execution events via SSE."""
    test_case = load_test_case(test_name)

    enriched = {
        **test_case,
        "_runtime_model": "gpt-4o-mini",
        "_runtime_version": version,
    }

    async def event_generator():
        async for mode, chunk in test_workflow.astream(
            enriched,
            stream_mode=["custom"],
            config=thread_config()
        ):
            if mode == "custom":
                yield f"data: {json.dumps(chunk)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
```

## Summary: LangGraph Patterns Used

| Pattern | Implementation | Purpose |
|---------|---------------|---------|
| **Entrypoint** | `@entrypoint(checkpointer=...)` | Main workflow entry, enables streaming |
| **Task** | `@task` | Reusable subtasks (assertions, single test) |
| **Stream Writer** | `get_stream_writer()` | Real-time event emission |
| **Thread Config** | `{"configurable": {"thread_id": ...}}` | Per-invocation isolation |
| **Checkpointer** | `MemorySaver()` | State persistence for streaming |
| **Runtime Injection** | `_runtime_*` keys in input dict | Pass config to single-input entrypoints |
| **Concurrency** | `asyncio.Semaphore` + `as_completed` | Parallel batch with limits |

## File Reference

| File | LangGraph Usage |
|------|-----------------|
| `workflows/test_workflow.py` | `@entrypoint`, `get_stream_writer()` |
| `workflows/eval_workflow.py` | `@entrypoint`, `@task` for assertions |
| `workflows/batch_workflow.py` | `@entrypoint`, semaphore concurrency |
| `workflows/simulation_workflow.py` | `@entrypoint`, multi-LLM coordination |
| `workflows/__init__.py` | Exports, `thread_config()` helper |
