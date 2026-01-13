# Promptfoo Integration

[Promptfoo](https://www.promptfoo.dev/) provides a web UI for viewing test results and comparing prompt versions.

## Why Promptfoo?

| Capability | Benefit |
|------------|---------|
| **Web UI Dashboard** | Visual test results, filtering, sorting |
| **Side-by-Side Comparison** | Compare v1 vs v2 vs v3 prompts |
| **Built-in Assertions** | `contains`, `llm-rubric`, `javascript` |
| **Historical Tracking** | View past runs, track regressions |
| **CI/CD Integration** | JSON output for automation |

## Quick Start

```bash
# Run evaluation with web UI
python run_promptfoo.py --view

# Compare specific versions
python run_promptfoo.py -V v1 -V v2 --view

# Generate config only (for inspection)
python run_promptfoo.py --generate-only

# View previous results
python run_promptfoo.py --view-only

# Show test statistics
python run_promptfoo.py --stats-only
```

## How It Works

```
1. GENERATE: Convert testcases/*.yaml -> promptfooconfig.yaml
2. RUN: Promptfoo calls provider.py for each test
3. EVALUATE: Promptfoo evaluates assertions
4. VIEW: Web UI at http://localhost:15500
```

## Architecture

```
run_promptfoo.py
      |
      v
config_generator.py  -->  promptfooconfig.yaml
      |
      v
promptfoo eval
      |
      v (for each test)
provider.py:call_api()
      |
      v
EvalRunner.run_eval()
      |
      v
results.json  -->  promptfoo view (Web UI)
```

## Custom Provider

The provider bridges Promptfoo to our eval framework:

```python
# promptfoo/provider.py

def call_api(prompt: str, options: dict, context: dict) -> dict:
    # Extract test name from context
    test_name = context.get("vars", {}).get("test_case_definition", "")

    # Run test via EvalRunner
    runner = EvalRunner(model=options.get("model"), version=options.get("version"))
    test_case = runner.get_test(test_name)
    result = runner.run_eval(test_case)

    # Format response with tool markers
    output = format_conversation(result)
    return {"output": output}
```

## Tool Marker Convention

Since Promptfoo only sees text, tool calls are embedded as markers:

```
Agent: Good day, I'm calling about your account.
  -> Tool: confirm_person({})
  <- Result: {"confirmed": true}
  -> Handoff: introduction -> verification
[TOOL:confirm_person]
```

This enables assertions like:
```yaml
assert:
  - type: contains
    value: "[TOOL:confirm_person]"
```

## Assertion Mapping

| Our Assertion | Promptfoo Assertion |
|---------------|---------------------|
| `contains` | `contains` |
| `not_contains` | `not-contains` |
| `contains_function_call` | `contains` with `[TOOL:name]` |
| `llm_rubric` | `llm-rubric` |
| `equals` | `equals` |

## Prerequisites

```bash
# Install promptfoo globally
npm install -g promptfoo

# Or use npx (no install needed)
npx promptfoo eval
```

## CI/CD Integration

```bash
# Run in CI mode (exit code based on results)
promptfoo eval --threshold 0.8

# Output JSON for parsing
python run_promptfoo.py --json > results.json
```
