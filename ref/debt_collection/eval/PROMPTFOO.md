# Promptfoo Integration Deep Dive

[Promptfoo](https://www.promptfoo.dev/) is a third-party evaluation framework that provides a web UI for viewing results and comparing prompt versions. This document explains how our eval framework integrates with Promptfoo.

## Why Promptfoo?

| Capability | Benefit |
|------------|---------|
| **Web UI Dashboard** | Visual test results, filtering, sorting |
| **Side-by-Side Comparison** | Compare v1 vs v2 vs v3 prompts |
| **Built-in Assertions** | `contains`, `llm-rubric`, `javascript` |
| **Historical Tracking** | View past runs, track regressions |
| **CI/CD Integration** | JSON output for automation |

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        run_promptfoo.py                         │
│                                                                 │
│  1. Generate Config    2. Run Promptfoo    3. View Results      │
└─────────────────────────────────────────────────────────────────┘
           │                      │                    │
           ▼                      ▼                    ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ config_generator│    │  promptfoo eval │    │  promptfoo view │
│                 │    │                 │    │                 │
│ testcases/*.yaml│    │ For each test:  │    │ Web UI at       │
│       ↓         │    │   ↓             │    │ localhost:15500 │
│ promptfooconfig │    │ provider.py     │    │                 │
│      .yaml      │    │   ↓             │    │                 │
│                 │    │ EvalRunner      │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Execution Flow

```
python run_promptfoo.py run --view
                │
                ▼
┌───────────────────────────────────────────────────────────────────┐
│ STEP 1: GENERATE CONFIG (config_generator.py)                     │
│                                                                   │
│   Load testcases/*.yaml                                           │
│         │                                                         │
│         ▼                                                         │
│   For each test_case:                                             │
│     ├─ Extract name, turns, assertions                            │
│     ├─ Convert assertions to promptfoo format:                    │
│     │    contains_function_call → contains "[TOOL:name]"          │
│     │    llm_rubric → llm-rubric                                  │
│     │    contains → contains                                      │
│     └─ Add to prompts[] array                                     │
│         │                                                         │
│         ▼                                                         │
│   Generate providers[] for each version:                          │
│     ├─ v1: python:promptfoo/provider.py:call_api --version v1     │
│     ├─ v2: python:promptfoo/provider.py:call_api --version v2     │
│     └─ v3: python:promptfoo/provider.py:call_api --version v3     │
│         │                                                         │
│         ▼                                                         │
│   Write promptfooconfig.yaml                                      │
└───────────────────────────────────────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────────────────────────┐
│ STEP 2: RUN PROMPTFOO (subprocess: promptfoo eval)                │
│                                                                   │
│   Promptfoo reads promptfooconfig.yaml                            │
│         │                                                         │
│         ▼                                                         │
│   For each (test_case, version) combination:                      │
│     │                                                             │
│     ├─ Call provider.py:call_api(prompt, options)                 │
│     │    │                                                        │
│     │    ▼                                                        │
│     │  provider.py:                                               │
│     │    ├─ Parse test_name from prompt                           │
│     │    ├─ Extract version from provider config                  │
│     │    ├─ Create EvalRunner(version=version)                    │
│     │    ├─ Load test_case by name                                │
│     │    ├─ Run: result = runner.run_test(test_case)              │
│     │    ├─ Format response with [TOOL:name] markers              │
│     │    └─ Return {"output": response_with_markers}              │
│     │         │                                                   │
│     │         ▼                                                   │
│     └─ Promptfoo evaluates assertions against output              │
│          ├─ contains "[TOOL:confirm_person]" → PASS/FAIL          │
│          ├─ llm-rubric "should be empathetic" → PASS/FAIL         │
│          └─ contains "verify" → PASS/FAIL                         │
│         │                                                         │
│         ▼                                                         │
│   Aggregate results → results.json                                │
└───────────────────────────────────────────────────────────────────┘
                │
                ▼
┌───────────────────────────────────────────────────────────────────┐
│ STEP 3: VIEW RESULTS (subprocess: promptfoo view)                 │
│                                                                   │
│   Launch web server at http://localhost:15500                     │
│     ├─ Side-by-side version comparison                            │
│     ├─ Filter by pass/fail                                        │
│     ├─ Drill into individual assertions                           │
│     └─ Export reports                                             │
└───────────────────────────────────────────────────────────────────┘
```

## Key Files

| File | Purpose |
|------|---------|
| `run_promptfoo.py` | CLI orchestrator (generate, run, view commands) |
| `promptfoo/config_generator.py` | Converts test cases to promptfooconfig.yaml |
| `promptfoo/provider.py` | Custom provider that runs tests via EvalRunner |
| `promptfooconfig.yaml` | Generated config (DO NOT EDIT MANUALLY) |
| `results.json` | Test results from promptfoo eval |

## Provider Implementation

The provider is the bridge between Promptfoo and our eval framework:

```python
# promptfoo/provider.py

def call_api(prompt: str, options: dict, context: dict) -> dict:
    """
    Promptfoo calls this function for each test case.

    Args:
        prompt: The test name (e.g., "INT-001: Person confirms identity")
        options: Provider config including version
        context: Additional context from promptfoo

    Returns:
        {"output": "response with [TOOL:name] markers"}
    """
    # Extract version from provider config
    version = options.get("config", {}).get("version")

    # Create runner with version
    runner = EvalRunner(model="gpt-4o-mini", version=version)

    # Find and run the test
    test_case = runner.get_test_by_name(prompt)
    result = runner.run_test(test_case)

    # Format response with tool markers for assertion matching
    response = format_response_with_markers(result)

    return {"output": response}


def format_response_with_markers(result: TestResult) -> str:
    """
    Add [TOOL:name] markers to response for contains assertions.

    Example output:
        Agent: Good day, I'm calling about your account.
        [TOOL:confirm_person]
        Agent: Thank you for confirming...
    """
    parts = []
    for turn in result.turns:
        parts.append(f"Agent: {turn.response}")

        # Add tool markers
        for event in turn.events:
            if event["type"] == "tool_call":
                parts.append(f"[TOOL:{event['name']}]")
            elif event["type"] == "handoff":
                parts.append(f"[HANDOFF:{event['from']}->{event['to']}]")

    return "\n".join(parts)
```

## Config Generation

The config generator converts our YAML test cases to Promptfoo format:

```python
# promptfoo/config_generator.py

def generate_promptfoo_config(
    versions: list[str] = None,
    test_pattern: str = None
) -> dict:
    """Generate promptfooconfig.yaml content."""

    # Load all test cases
    test_cases = load_all_test_cases(pattern=test_pattern)

    # Build prompts array (one per test case)
    prompts = []
    for tc in test_cases:
        prompts.append({
            "raw": tc["name"],  # Test name passed to provider
            "label": tc["name"]
        })

    # Build providers array (one per version)
    versions = versions or ["v1", "v2", "v3"]
    providers = []
    for version in versions:
        providers.append({
            "id": f"python:promptfoo/provider.py:call_api",
            "label": version,
            "config": {
                "version": version
            }
        })

    # Build tests with assertions
    tests = []
    for tc in test_cases:
        test_assertions = []
        for turn in tc.get("turns", []):
            for assertion in turn.get("assertions", []):
                test_assertions.append(
                    convert_assertion(assertion)
                )

        tests.append({
            "vars": {"test_name": tc["name"]},
            "assert": test_assertions
        })

    return {
        "prompts": prompts,
        "providers": providers,
        "tests": tests,
        "outputPath": "results.json"
    }


def convert_assertion(assertion: dict) -> dict:
    """Convert our assertion format to Promptfoo format."""
    atype = assertion["type"]
    value = assertion.get("value", "")

    if atype == "contains_function_call":
        # Convert to contains with marker
        return {
            "type": "contains",
            "value": f"[TOOL:{value}]"
        }

    elif atype == "llm_rubric":
        # Use promptfoo's llm-rubric
        return {
            "type": "llm-rubric",
            "value": value
        }

    elif atype == "contains":
        return {
            "type": "contains",
            "value": value
        }

    elif atype == "not_contains":
        return {
            "type": "not-contains",
            "value": value
        }

    # ... other types
```

## Generated promptfooconfig.yaml Structure

```yaml
# AUTO-GENERATED - DO NOT EDIT
# Generated by: python run_promptfoo.py generate

description: "Debt Collection Agent Evaluation"

prompts:
  - raw: "INT-001: Person confirms identity"
    label: "INT-001: Person confirms identity"
  - raw: "INT-002: Wrong number scenario"
    label: "INT-002: Wrong number scenario"
  # ... more test cases

providers:
  - id: "python:promptfoo/provider.py:call_api"
    label: "v1"
    config:
      version: "v1"
  - id: "python:promptfoo/provider.py:call_api"
    label: "v2"
    config:
      version: "v2"
  - id: "python:promptfoo/provider.py:call_api"
    label: "v3"
    config:
      version: "v3"

tests:
  - vars:
      test_name: "INT-001: Person confirms identity"
    assert:
      - type: contains
        value: "[TOOL:confirm_person]"
      - type: contains
        value: "verify"

  - vars:
      test_name: "INT-002: Wrong number scenario"
    assert:
      - type: contains
        value: "[TOOL:wrong_number]"
      - type: not-contains
        value: "verification"

outputPath: results.json
```

## Version Comparison Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Version Comparison                           │
│                                                                 │
│  Test: INT-001: Person confirms identity                        │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │     v1      │  │     v2      │  │     v3      │              │
│  ├─────────────┤  ├─────────────┤  ├─────────────┤              │
│  │ Default     │  │ Empathetic  │  │ Mixed       │              │
│  │ prompts     │  │ prompts     │  │ approach    │              │
│  ├─────────────┤  ├─────────────┤  ├─────────────┤              │
│  │ Response:   │  │ Response:   │  │ Response:   │              │
│  │ "Good day,  │  │ "Hello! I   │  │ "Good day,  │              │
│  │ this is..." │  │ hope you're │  │ this is..." │              │
│  │             │  │ well..."    │  │             │              │
│  ├─────────────┤  ├─────────────┤  ├─────────────┤              │
│  │ Assertions: │  │ Assertions: │  │ Assertions: │              │
│  │ ✓ TOOL:     │  │ ✓ TOOL:     │  │ ✓ TOOL:     │              │
│  │   confirm   │  │   confirm   │  │   confirm   │              │
│  │ ✗ contains  │  │ ✓ contains  │  │ ✗ contains  │              │
│  │   "verify"  │  │   "verify"  │  │   "verify"  │              │
│  ├─────────────┤  ├─────────────┤  ├─────────────┤              │
│  │ Score: 50%  │  │ Score: 100% │  │ Score: 50%  │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│                                                                 │
│  Winner: v2 (Empathetic prompts)                                │
└─────────────────────────────────────────────────────────────────┘
```

## CLI Commands

```bash
# Generate config only (for inspection)
python run_promptfoo.py generate
python run_promptfoo.py generate --versions v1,v2  # Specific versions
python run_promptfoo.py generate --pattern INT     # Filter tests

# Run evaluation
python run_promptfoo.py run                        # Run all
python run_promptfoo.py run --view                 # Run + open web UI
python run_promptfoo.py run -v v1 -v v2 --view     # Compare v1 vs v2
python run_promptfoo.py run INT 5 --view           # Run 5 INT tests

# View previous results
python run_promptfoo.py view                       # Open web UI

# Show statistics
python run_promptfoo.py stats                      # Test count by file
```

## Assertion Mapping

| Our Assertion | Promptfoo Assertion | Notes |
|---------------|--------------------|-|
| `contains` | `contains` | Direct mapping |
| `not_contains` | `not-contains` | Direct mapping |
| `contains_any` | `contains-any` | Direct mapping |
| `equals` | `equals` | Direct mapping |
| `contains_function_call` | `contains` | Maps to `[TOOL:name]` marker |
| `llm_rubric` | `llm-rubric` | Uses Promptfoo's LLM judge |

## Tool Marker Convention

Since Promptfoo only sees the text response, we embed tool calls as markers:

```
Input from agent:
  response: "Good day, I'm calling about your account."
  events: [
    {"type": "tool_call", "name": "confirm_person", "args": {}},
    {"type": "tool_output", "result": {"confirmed": true}},
    {"type": "handoff", "from": "introduction", "to": "verification"}
  ]

Output to Promptfoo:
  "Agent: Good day, I'm calling about your account.
   [TOOL:confirm_person]
   [HANDOFF:introduction->verification]"

Assertion check:
  contains "[TOOL:confirm_person]" → PASS ✓
```

## Error Handling

```python
# provider.py error handling

def call_api(prompt: str, options: dict, context: dict) -> dict:
    try:
        # ... run test ...
        return {"output": response}

    except TestNotFoundError as e:
        return {
            "output": "",
            "error": f"Test not found: {prompt}"
        }

    except Exception as e:
        return {
            "output": "",
            "error": str(e)
        }
```

## Web UI Features

The Promptfoo web UI (http://localhost:15500) provides:

| Feature | Description |
|---------|-------------|
| **Results Table** | All tests with pass/fail status |
| **Version Columns** | Side-by-side comparison |
| **Assertion Details** | Expand to see individual assertions |
| **Filters** | Filter by status, version, test name |
| **Sorting** | Sort by score, name, duration |
| **Export** | Download CSV/JSON reports |
| **History** | View previous evaluation runs |

## CI/CD Integration

```bash
# Run in CI mode (no web UI, exit code based on results)
python run_promptfoo.py run --ci

# Output JSON for parsing
python run_promptfoo.py run --output json > results.json

# Fail if score below threshold
promptfoo eval --threshold 0.8
```

## Prerequisites

```bash
# Install promptfoo globally
npm install -g promptfoo

# Verify installation
promptfoo --version

# Or use npx (no install needed)
npx promptfoo eval
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `promptfoo: command not found` | Run `npm install -g promptfoo` |
| Provider import error | Ensure running from `eval/` directory |
| Test not found | Check test name matches exactly |
| Slow execution | Reduce `--max-concurrent` or test count |
| Port 15500 in use | Kill existing `promptfoo view` process |

## Summary: Promptfoo Integration Patterns

| Pattern | Implementation | Purpose |
|---------|---------------|---------|
| **Config Generation** | `config_generator.py` | Convert YAML → promptfooconfig.yaml |
| **Custom Provider** | `provider.py:call_api` | Bridge to EvalRunner |
| **Tool Markers** | `[TOOL:name]` convention | Enable tool call assertions |
| **Version Providers** | Multiple provider entries | Side-by-side comparison |
| **Assertion Mapping** | Type conversion | Unified assertion format |
