# Eval Framework

A comprehensive evaluation framework for testing LiveKit voice agents with support for A/B testing different prompt versions and models.

## Features

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

## Quick Start

```bash
# Run a single test
python run_test.py TEST-001

# Run tests with streaming output
python run_test.py TEST

# Run evaluations with assertions
python run_eval.py TEST

# Run promptfoo for web UI comparison
python run_promptfoo.py --view

# Interactive mode
python run_interactive.py
```

## Directory Structure

```
eval/
  __init__.py
  eval_config.yaml          # Framework configuration
  simulated_user_config.yaml
  runner.py                 # Central EvalRunner API
  console.py                # Rich output utilities
  run_test.py              # CLI: Run tests without assertions
  run_eval.py              # CLI: Run tests with assertions
  run_simulation.py        # CLI: LLM-simulated conversations
  run_interactive.py       # CLI: Interactive REPL mode
  run_promptfoo.py         # CLI: Promptfoo integration
  run_list.py              # CLI: List available tests
  core/
    config.py              # Config loading, version resolution
    loader.py              # Test case loading, data factories
    session.py             # TestSession lifecycle management
    events.py              # Event extraction (tool calls, handoffs)
    userdata.py            # User data models
  workflows/
    test_workflow.py       # @entrypoint: Execute test turns
    eval_workflow.py       # @entrypoint: Test + assertions
    simulation_workflow.py # @entrypoint: LLM-simulated user
    batch_workflow.py      # @entrypoint: Parallel execution
  schemas/
    test_case.py           # Pydantic: TestCase, Assertion, Turn
    models.py              # TestResult, EvalResult, BatchResult
  promptfoo/
    provider.py            # Custom Promptfoo provider
    config_generator.py    # YAML -> promptfooconfig.yaml
    runner.py              # Promptfoo execution wrapper
  cli/
    cli_utils.py           # Shared CLI utilities
  prompts/
    llm_judge.yaml         # LLM judge system prompt
  testcases/               # Test case YAML files
    *.yaml
```

## Configuration

### eval_config.yaml

```yaml
type: multi                    # "single" or "multi" agent system
default_agent: introduction    # Starting agent ID
agent_ids:                     # All agent IDs to test
  - introduction
  - verification
  - completion

imports:
  userdata_module: shared_state
  userdata_class: UserData
  test_data_factory: shared_state:create_test_userdata
  agent_classes_module: sub_agents
  agent_classes_var: AGENT_CLASSES
  tools_module: tools
  tools_function: get_tools_by_names
```

## Test Case Format

```yaml
agent_id: my_agent
sub_agent_id: introduction

default_test_data:
  customer_name: "Test Customer"
  account_id: "12345"

test_cases:
  - name: "TEST-001: Customer confirms identity"
    tags: [unit, introduction]
    turns:
      - user_input: "Yes, speaking"
        assertions:
          - type: contains_function_call
            value: confirm_customer
          - type: contains
            value: verify
```

## Assertion Types

| Type | Description | Example |
|------|-------------|---------|
| `contains` | Response contains substring (case-insensitive) | `value: "verify"` |
| `not_contains` | Response must NOT contain | `value: "goodbye"` |
| `contains_any` | Contains at least one keyword | `value: ["payment", "settle"]` |
| `equals` | Exact text match | `value: "Yes"` |
| `contains_function_call` | Tool/function was invoked | `value: "confirm_person"` |
| `llm_rubric` | LLM judge evaluates semantic quality | `value: "Agent should be helpful"` |

## CLI Reference

### run_test.py / run_eval.py

```bash
python run_test.py [PATTERN] [LIMIT]
  PATTERN: "TEST" (prefix), "agent01.yaml" (file), 5 (count)
  --tags, -t       Filter by tags
  --model, -m      LLM model (default: from config)
  --version, -V    Prompt version (v1, v2, etc.)
  --json, -j       JSON output
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
python run_promptfoo.py [PATTERN] [OPTIONS]
  --view           Launch web UI after run
  -V, --versions   Specific versions to compare
  --generate-only  Only generate config, don't run
  --view-only      Only open web UI
  --stats-only     Show test statistics
```

## Dependencies

- Python 3.10+
- livekit-agents
- langchain
- langgraph
- pydantic
- pyyaml
- click
- rich
- python-dotenv
- promptfoo (npm package, optional for web UI)

## See Also

- [LANGGRAPH.md](./LANGGRAPH.md) - LangGraph Functional API patterns
- [PROMPTFOO.md](./PROMPTFOO.md) - Promptfoo integration details
