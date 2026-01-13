# LangGraph Architecture

This eval framework uses LangGraph Functional API for stateful, streaming workflows.

## Core Concepts

### 1. Entrypoints (`@entrypoint`)

Main workflow entry points that support checkpointing and streaming:

```python
from langgraph.func import entrypoint
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()

@entrypoint(checkpointer=checkpointer)
async def test_workflow(test_case: dict) -> TestResult:
    writer = get_stream_writer()
    writer({"event": "started", "test_name": test_case["name"]})
    # ... workflow logic ...
    writer({"event": "completed", "total_turns": len(turns)})
    return TestResult(turns=turns, duration_ms=duration)
```

### 2. Tasks (`@task`)

Reusable units of work called within entrypoints:

```python
from langgraph.func import task

@task
async def run_assertion(turn: Turn, assertion: dict) -> dict:
    assertion_type = assertion["type"]
    # ... evaluate assertion ...
    return {"passed": passed, "message": message}
```

### 3. Stream Writer Pattern

Real-time event emission during workflow execution:

```python
from langgraph.config import get_stream_writer

@entrypoint(checkpointer=checkpointer)
async def eval_workflow(test_case: dict) -> EvalResult:
    writer = get_stream_writer()

    for i, turn in enumerate(test_case["turns"]):
        writer({"event": "user_input", "turn": i, "content": turn["user_input"]})
        response, events = await session.send_message(turn["user_input"])
        writer({"event": "agent_response", "turn": i, "content": response})
```

### 4. Thread Configuration

Each workflow invocation needs a unique thread ID for state isolation:

```python
import uuid

def thread_config(thread_id: str = None) -> dict:
    return {"configurable": {"thread_id": thread_id or str(uuid.uuid4())}}

# Each test gets its own thread
for test_case in test_cases:
    result = await test_workflow.ainvoke(test_case, config=thread_config())
```

## Invocation Patterns

### Async Invoke (Wait for Result)

```python
result = await test_workflow.ainvoke(test_case, config=thread_config())
```

### Async Streaming (Real-time Events)

```python
async for mode, chunk in test_workflow.astream(
    test_case,
    stream_mode=["custom", "updates"],
    config=thread_config()
):
    if mode == "custom":
        print(chunk)  # Our writer() events
```

### Sync Wrapper

```python
def run_test(test_case: dict) -> TestResult:
    return asyncio.run(test_workflow.ainvoke(test_case, config=thread_config()))
```

## Runtime Configuration Injection

LangGraph entrypoints accept only one input, so runtime options are packed into the test case:

```python
@entrypoint(checkpointer=checkpointer)
async def test_workflow(test_case: dict) -> TestResult:
    # Extract runtime options (injected by EvalRunner)
    model = test_case.get("_runtime_model")
    version = test_case.get("_runtime_version")
    temperature = test_case.get("_runtime_temperature")
```

**EvalRunner packs options before calling workflow:**

```python
class EvalRunner:
    async def arun_test(self, test_case: dict) -> TestResult:
        enriched = {
            **test_case,
            "_runtime_model": self.model,
            "_runtime_version": self.version,
            "_runtime_temperature": self.temperature,
        }
        return await test_workflow.ainvoke(enriched, config=thread_config())
```

## Workflow Files

| File | Purpose |
|------|---------|
| `workflows/test_workflow.py` | Execute test turns, emit events |
| `workflows/eval_workflow.py` | Test + assertion evaluation |
| `workflows/batch_workflow.py` | Parallel execution with semaphore |
| `workflows/simulation_workflow.py` | LLM-simulated user conversations |
