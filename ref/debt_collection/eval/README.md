# Eval Framework

A comprehensive evaluation framework for testing LiveKit voice agents with support for A/B testing different prompt versions and models.

**Stats:** 47 Python files | ~3,600 lines of code | 8 test case files (~109 KB, ~140 tests)

## Features at a Glance

| Feature | Description |
|---------|-------------|
| **Multi-Mode Testing** | Tests, evaluations with assertions, LLM simulations, interactive REPL, batch runs |
| **Real-Time Streaming** | Full conversation output with tool calls, handoffs, and results via LangGraph |
| **6 Assertion Types** | `contains`, `not_contains`, `contains_any`, `equals`, `contains_function_call`, `llm_rubric` |
| **LLM Judge** | Semantic evaluation using LLM rubrics for tone, quality, and correctness |
| **Version System** | A/B test different prompts/models with single source of truth in `agent.yaml` |
| **Session Isolation** | Each test gets fresh LLM, agents, and user data - no cross-contamination |
| **Parallel Execution** | Batch tests with configurable concurrency (semaphore-based) |
| **Promptfoo Integration** | Web UI dashboard, side-by-side version comparison, detailed reports |
| **Simulated Users** | LLM-powered customer personas (cooperative, difficult, confused) |
| **Test Data Layering** | Factory defaults + YAML overrides for flexible test scenarios |

## Design Principles

### 1. Session Isolation

**Each test case gets a completely fresh session.** No state leaks between tests:

```
Test 1                    Test 2                    Test 3
   |                         |                         |
   v                         v                         v
+-----------------+   +-----------------+   +-----------------+
| Fresh Session   |   | Fresh Session   |   | Fresh Session   |
| +- New LLM      |   | +- New LLM      |   | +- New LLM      |
| +- New Userdata |   | +- New Userdata |   | +- New Userdata |
| +- New Agents   |   | +- New Agents   |   | +- New Agents   |
+-----------------+   +-----------------+   +-----------------+
```

### 2. Configuration Priority Chain

Explicit, no silent fallbacks:

```
CLI flag > Runtime parameter > Version config > agent.yaml > defaults
```

- **CLI `--model`** always wins if specified
- **Version config** provides per-version overrides
- Raises `ConfigurationError` if required values missing

### 3. LangGraph Functional API

All workflows use `@entrypoint` and `@task` decorators with streaming support:

```python
@entrypoint(checkpointer=checkpointer)
async def test_workflow(test_case: dict) -> TestResult:
    writer = get_stream_writer()
    writer({"event": "started", "name": test_case["name"]})
    # ... execution with real-time event emission
```

### 4. Test Data Layering

Two-layer override system for flexible test scenarios:

```
Layer 1: Factory Defaults (shared_state.py)
         username: "jsmith", id_number: "8501125678901"
                              |
                              v
Layer 2: YAML Overrides (testcases/*.yaml)
         username: "jsmith001", id_number: "8501015800087"
                              |
                              v
         Final UserData used in test
```

### 5. Async/Sync Duality

Every workflow provides three interfaces:

```python
# Async - returns result
result = await test_workflow.ainvoke(test_case, config=thread_config())

# Async streaming - real-time events
async for mode, chunk in test_workflow.astream(test_case, stream_mode=["custom"], config=thread_config()):
    print(chunk)

# Sync wrapper - for scripts
result = run_test(test_case)
```

### 6. Strict Schema Validation

Pydantic models validate all test cases with normalized assertion types:

```python
# Auto-converts: llm-rubric -> llm_rubric
# Validates: AssertionType enum, required fields, non-empty turns
# Fails fast: TestCaseValidationError with detailed messages
```

### 7. Dependency Injection

Dynamic imports based on configuration:

```yaml
# eval_config.yaml
imports:
  userdata_module: shared_state
  agent_classes_module: sub_agents
  tools_module: tools
```

## Quick Start

```bash
# Run a single test
python run_test.py INT-001

# Run tests with streaming output
python run_test.py INT

# Run evaluations with assertions
python run_eval.py INT

# Run promptfoo for web UI comparison
python run_promptfoo.py run --view
```

## Directory Structure

```
eval/
├── runner.py                 # Central EvalRunner API (350 lines)
├── run_test.py              # CLI: Run tests without assertions
├── run_eval.py              # CLI: Run tests with assertions
├── run_simulation.py        # CLI: LLM-simulated conversations
├── run_interactive.py       # CLI: Interactive REPL mode
├── run_promptfoo.py         # CLI: Promptfoo integration
├── run_list.py              # CLI: List available tests
├── eval_config.yaml         # Framework config
├── simulated_user_config.yaml
│
├── core/
│   ├── config.py            # Config loading, version resolution
│   ├── loader.py            # Test case loading, data factories
│   ├── session.py           # TestSession lifecycle management
│   ├── events.py            # Event extraction (tool calls, handoffs)
│   └── userdata.py          # User data models
│
├── workflows/
│   ├── test_workflow.py     # @entrypoint: Execute test turns
│   ├── eval_workflow.py     # @entrypoint: Test + assertions
│   ├── simulation_workflow.py  # @entrypoint: LLM-simulated user
│   └── batch_workflow.py    # @entrypoint: Parallel execution
│
├── schemas/
│   ├── test_case.py         # Pydantic: TestCase, Assertion, Turn
│   └── models.py            # TestResult, EvalResult, BatchResult
│
├── promptfoo/
│   ├── provider.py          # Custom Promptfoo provider
│   └── config_generator.py  # YAML -> promptfooconfig.yaml
│
├── cli/
│   └── cli_utils.py         # Shared CLI utilities
│
└── testcases/               # Test case YAML files
    ├── agent01_introduction.yaml
    ├── agent02_verification.yaml
    ├── agent03_negotiation.yaml
    ├── agent04_payment.yaml
    ├── agent05_closing.yaml
    ├── agent06_script_types.yaml
    ├── agent00_e2e_flow.yaml
    └── e2e_critical.yaml
```

## Version System

The eval framework supports A/B testing different prompt versions and models. **Versions are defined in `agent.yaml`** (single source of truth), used by both eval testing and production.

### Defined Versions

| Version | Description | Model | Prompt Changes |
|---------|-------------|-------|----------------|
| v1 | Default prompts | default | None |
| v2 | Softer tone | gpt-4o-mini | introduction, negotiation, closing use _v2 prompts |
| v3 | Mixed approach | default | Only negotiation uses _v2 prompt |

### Applying to Production

After A/B testing, set `active_version` in `agent.yaml` to apply the winning version:

```yaml
# agent.yaml
active_version: v2  # Set to winning version (null = use base prompts)

versions:
  v1:
    description: "Baseline - all agents use default prompts"
  v2:
    description: "Empathetic approach - softer tone"
    model: gpt-4o-mini
    sub_agents:
      introduction: { prompt_version: v2 }
      negotiation: { prompt_version: v2 }
      closing: { prompt_version: v2 }
```

### CLI Usage

```bash
# Run with specific version
python run_test.py INT --version v2
python run_eval.py INT -V v2

# Run with version + model override (CLI model wins)
python run_eval.py INT -V v2 -m gpt-4-turbo

# Promptfoo: Compare all versions (default)
python run_promptfoo.py run --view

# Promptfoo: Compare specific versions
python run_promptfoo.py run -v v1 -v v2 --view
```

## Assertion Types

| Type | Description | Example |
|------|-------------|---------|
| `contains` | Response contains substring (case-insensitive) | `value: "verify"` |
| `not_contains` | Response must NOT contain | `value: "goodbye"` |
| `contains_any` | Contains at least one keyword | `value: ["payment", "settle"]` |
| `equals` | Exact text match | `value: "Yes"` |
| `contains_function_call` | Tool/function was invoked | `value: "confirm_person"` |
| `llm_rubric` | LLM judge evaluates semantic quality | `value: "Agent should be empathetic"` |

### LLM Rubric Example

```yaml
turns:
  - user_input: "I can't afford the full amount"
    assertions:
      - type: llm_rubric
        value: "Agent should acknowledge financial difficulty and offer alternatives"
```

The LLM judge returns `{passed: bool, reason: string}` with detailed explanation.

## Test Case Format

```yaml
agent_id: debt_collection
sub_agent_id: introduction

# Applied to ALL tests in this file
default_test_data:
  full_name: "John Smith"
  outstanding_amount: 2500.00

test_cases:
  - name: "INT-001: Person confirms identity"
    tags: [unit, introduction]
    turns:
      - user_input: "Yes, speaking"
        assertions:
          - type: contains_function_call
            value: confirm_person
          - type: contains
            value: verify
```

## Execution Flows

### Test Execution

```
run_test.py "INT-001"
      |
      v
1. LOAD: load_test_cases()
   +- Parse YAML, validate schema
   +- Attach _default_test_data
      |
      v
2. RUN: test_workflow(test_case)
   +- Create fresh TestSession
   +- Get initial greeting
   +- For each turn:
   |   +- Send user_input
   |   +- Capture tool calls, outputs, handoffs
   |   +- Get agent response
      |
      v
3. RETURN: TestResult(turns, duration_ms, status)
```

### Eval Execution

```
run_eval.py "INT-001"
      |
      v
1. Run test_workflow (same as above)
      |
      v
2. EVALUATE: For each turn with assertions
   +- contains: substring check
   +- contains_function_call: check turn.events
   +- llm_rubric: call LLM judge
      |
      v
3. RETURN: EvalResult(turns, score, passed_count, failed_count, assertions)
```

### Simulation Execution

```
run_simulation.py --persona difficult
      |
      v
1. INIT: Create LLMs
   +- Simulated User (gpt-4o-mini, temp=0.7, persona prompt)
   +- Agent (via TestSession)
      |
      v
2. LOOP: while turn < max_turns
   +- Get agent response
   +- Generate simulated user response via LLM
   +- Check stop phrases
      |
      v
3. RETURN: SimulationResult(turns, stop_reason, persona)
```

## Programmatic API

### EvalRunner (Recommended)

```python
from eval import EvalRunner

runner = EvalRunner(model="gpt-4o-mini", version="v2")

# Sync
result = runner.run_test(test_case)
result = runner.run_eval(test_case)

# Async
result = await runner.arun_test(test_case)

# Streaming
async for event in runner.astream_test(test_case):
    print(event)
```

### Direct Workflow Calls

```python
from eval.workflows import test_workflow, eval_workflow, thread_config

# Pack runtime options into test_case
enriched_case = {
    **test_case,
    "_runtime_model": "gpt-4o-mini",
    "_runtime_version": "v2",
}

# Async invoke
result = await test_workflow.ainvoke(enriched_case, config=thread_config())

# Streaming
async for mode, chunk in test_workflow.astream(
    enriched_case,
    stream_mode=["custom", "updates"],
    config=thread_config()
):
    if mode == "custom":
        print(chunk)
```

### FastAPI Integration

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from eval import EvalRunner

app = FastAPI()
runner = EvalRunner(model="gpt-4o-mini")

@app.post("/api/eval/stream")
async def run_test_stream(test_name: str, version: str = None):
    test_case = runner.get_test(test_name)

    async def generate():
        async for event in runner.astream_test(test_case, version=version):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

## Stream Event Types

| Event | Fields | Description |
|-------|--------|-------------|
| `started` | `test_name` | Test execution started |
| `user_input` | `turn`, `content` | User message sent |
| `agent_response` | `turn`, `content` | Agent response received |
| `turn_event` | `turn`, `type`, `content` | Tool call, output, or handoff |
| `completed` | `total_turns` | Test finished |
| `assertion_result` | `passed`, `type`, `value`, `message` | Eval assertion result |
| `eval_completed` | `score`, `passed`, `failed` | Eval finished |
| `batch_started` | `total` | Batch execution started |
| `batch_completed` | `passed`, `failed`, `total` | Batch finished |

## CLI Reference

### run_test.py / run_eval.py

```bash
python run_test.py [PATTERN] [LIMIT]
  PATTERN: "INT" (prefix), "agent01_introduction.yaml" (file), 5 (count)
  --tags, -t       Filter by tags
  --model, -m      LLM model (default: gpt-4o-mini)
  --version, -V    Prompt version (v1, v2, v3)
  --json, -j       JSON output

  Examples:
    python run_test.py INT 2              # Run 2 tests starting with "INT"
    python run_test.py INT --version v2   # Run INT tests with v2 prompts
```

### run_simulation.py

```bash
python run_simulation.py
  --persona, -p    cooperative, difficult, confused
  --max-turns, -n  Maximum turns (default: 20)
  --agent, -a      Starting agent
  --model, -m      LLM model
  --version, -V    Prompt version
```

### run_interactive.py

```bash
python run_interactive.py
  --agent, -a      Starting agent
  --model, -m      LLM model
  --version, -V    Prompt version

  Commands: quit, reset, clear, data
```

### run_promptfoo.py

```bash
python run_promptfoo.py run [PATTERN] [OPTIONS]
  --view, -w       Launch web UI after run
  -v, --versions   Specific versions to compare

python run_promptfoo.py view       # View previous results
python run_promptfoo.py generate   # Generate config only
python run_promptfoo.py stats      # Show test statistics
```

## Output Format

### Streaming Output

```
Test: INT-001: Person confirms identity
------------------------------------------------------------
Agent: Good day, you are speaking to...

User: Yes, speaking
  -> Tool: confirm_person({})
  <- Result: {"confirmed": true}
  -> Handoff: introduction_agent -> verification_agent
Agent: Please note that this call is recorded...

Completed: 2 turns
```

### Eval Output

```
  PASS contains_function_call: confirm_person
  FAIL contains: verify
       Expected 'verify' in response

Score: 50% (1 passed, 1 failed)
```

## Configuration Files

### eval_config.yaml

```yaml
type: multi
default_agent: introduction
agent_ids: [introduction, verification, negotiation]

imports:
  userdata_module: shared_state
  userdata_class: UserData
  test_data_factory: shared_state:create_test_userdata
  agent_classes_module: sub_agents
  agent_classes_var: AGENT_CLASSES
```

### simulated_user_config.yaml

```yaml
model:
  provider: openai
  name: gpt-4o-mini
  temperature: 0.7

persona:
  name: "John Smith"
  system_prompt: |
    You are simulating John Smith receiving a debt collection call.
    - You owe R5,000 for overdue subscription fees
    - Say "goodbye" when the call ends

simulation:
  max_turns: 20
  stop_phrases: ["goodbye", "bye"]
```

## Promptfoo Integration

Promptfoo provides a web UI for viewing results and comparing versions:

```bash
# Run with web UI
python run_promptfoo.py run --view

# Compare specific versions
python run_promptfoo.py run -v v1 -v v2 --view
```

### How It Works

```
1. GENERATE: Convert testcases/*.yaml -> promptfooconfig.yaml
2. RUN: Promptfoo calls provider.py for each test
3. EVALUATE: Promptfoo evaluates assertions
4. VIEW: Web UI at http://localhost:15500
```

Requires: `npm install -g promptfoo`

## Architecture Summary

| Component | Purpose | Pattern |
|-----------|---------|---------|
| **EvalRunner** | Unified API | Singleton config, method overloading |
| **Workflows** | Execution | LangGraph `@entrypoint`, streaming |
| **TestSession** | Agent lifecycle | Async context manager |
| **Loader** | Test loading | Dynamic imports, Pydantic validation |
| **Schemas** | Type safety | Pydantic, normalized enums |
| **Promptfoo** | Web UI | Config generation, custom provider |

## Result Types

```python
TestResult       # turns, duration_ms, status, error
EvalResult       # + score, passed_count, failed_count, assertions
SimulationResult # + persona, goal_achieved, stop_reason
BatchResult      # + total, passed, failed (aggregate)

# All have: .to_dict(), .to_json()
```

## Adding New Versions

1. Edit `agent.yaml`:

```yaml
versions:
  v4_formal:
    description: "Formal business tone"
    model: gpt-4o
    sub_agents:
      introduction: { prompt_version: v4 }
```

2. Create prompt files:
   - `prompts/prompt01_introduction_v4.yaml`

3. Test:
   ```bash
   python run_eval.py INT --version v4_formal
   ```

---

## Deep Dive Documentation

For detailed implementation patterns, see:

- **[LANGGRAPH.md](./LANGGRAPH.md)** - LangGraph Functional API patterns, workflows, streaming, checkpointing
- **[PROMPTFOO.md](./PROMPTFOO.md)** - Promptfoo integration, config generation, version comparison
