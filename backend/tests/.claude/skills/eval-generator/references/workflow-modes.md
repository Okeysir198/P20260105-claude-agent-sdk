# Workflow Modes Reference

The eval framework supports 5 execution modes for different testing scenarios.

## Overview

| Mode | Purpose | Assertions | Speed | Use Case |
|------|---------|------------|-------|----------|
| Test | Smoke testing | No | Fast | Verify agent responds |
| Eval | Validation | Yes | Medium | CI/CD, regression |
| Simulation | Exploration | Optional | Slow | Edge case discovery |
| Promptfoo | A/B testing | Yes | Slow | Prompt comparison |
| Interactive | Manual testing | No | Real-time | Development |

---

## 1. Test Mode

Run tests without assertions. Shows agent responses for visual inspection.

**Use for**: Smoke testing, quick validation that agent responds coherently.

### CLI Commands

```bash
# Run all tests
python eval/run_test.py

# Run specific test by name prefix
python eval/run_test.py INT
python eval/run_test.py "E2E-001"

# Run from specific file
python eval/run_test.py agent01_reservation.yaml

# Limit number of tests
python eval/run_test.py 5
python eval/run_test.py INT 3

# Filter by tags
python eval/run_test.py --tags unit
python eval/run_test.py --tags "unit,happy-path"

# Use specific model/temperature
python eval/run_test.py --model gpt-4o --temperature 0.3

# Use prompt version
python eval/run_test.py -V v2

# JSON output (for CI)
python eval/run_test.py --json
```

### Output

```
Running 3 test(s)
Model: gpt-4o-mini | Temperature: 0.7

[INT-001] Person confirms identity
  User: Yes, this is John speaking
  Agent: Thank you for confirming, John. How can I help you today?
  Status: COMPLETED

[INT-002] Person denies identity
  User: No, you have the wrong number
  Agent: I apologize for the inconvenience...
  Status: COMPLETED
```

---

## 2. Eval Mode

Run tests WITH assertions. Reports pass/fail for each assertion.

**Use for**: CI/CD pipelines, regression testing, validation before deployment.

### CLI Commands

```bash
# Run all evaluations
python eval/run_eval.py

# Run specific tests
python eval/run_eval.py INT
python eval/run_eval.py "E2E-001"

# Filter by tags
python eval/run_eval.py --tags critical
python eval/run_eval.py --tags "e2e,happy-path"

# Limit tests
python eval/run_eval.py 10

# Use specific configuration
python eval/run_eval.py --model gpt-4o -T 0.5 -V v2

# JSON output for CI integration
python eval/run_eval.py --json
```

### Output

```
Evaluating 3 test(s)
Model: gpt-4o-mini | Temperature: 0.7

[INT-001] Person confirms identity
  User: Yes, this is John speaking
  Agent: Thank you for confirming, John...

  Assertions:
    [PASS] contains_function_call: verify_identity
    [PASS] llm_rubric: Agent should greet warmly

  Result: PASS (2/2)

[INT-002] Person denies identity
  User: No, wrong number
  Agent: I apologize...

  Assertions:
    [PASS] not_contains: goodbye
    [FAIL] llm_rubric: Agent should offer to help anyway
      Reason: Agent ended call without offering alternatives

  Result: FAIL (1/2)

Summary: 1/2 tests passed
```

---

## 3. Simulation Mode

LLM-powered simulated user has multi-turn conversations with the agent.

**Use for**: Discovering edge cases, stress testing, exploring conversation paths.

### CLI Commands

```bash
# Default simulation (cooperative persona, 20 turns)
python eval/run_simulation.py

# Different personas
python eval/run_simulation.py --persona cooperative
python eval/run_simulation.py --persona difficult
python eval/run_simulation.py --persona confused

# Custom turn limit
python eval/run_simulation.py --max-turns 10

# Start with specific agent
python eval/run_simulation.py --agent reservation

# Custom goal
python eval/run_simulation.py --goal "Try to get a refund but eventually accept store credit"

# Use specific configuration
python eval/run_simulation.py --model gpt-4o -T 0.7 -V v2

# JSON output
python eval/run_simulation.py --json
```

### Persona Descriptions

| Persona | Behavior |
|---------|----------|
| `cooperative` | Helpful, provides information when asked |
| `difficult` | Impatient, complains, challenges agent |
| `confused` | Asks for clarification, misunderstands |

### Output

```
Simulation Mode
Model: gpt-4o-mini | Temperature: 0.7 | Persona: difficult

Turn 1:
  User: I need to change my reservation and I'm not happy about it
  Agent: I understand your frustration. Let me help you with that...

Turn 2:
  User: This is ridiculous, why wasn't I notified earlier?
  Agent: I apologize for any inconvenience...

[... continues until max_turns or conversation ends ...]

Simulation Complete
Turns: 8/20
Final Agent: reservation
```

---

## 4. Promptfoo Mode

Run evaluations with web UI for comparing prompt versions.

**Use for**: A/B testing prompts, comparing model performance, visual analysis.

### CLI Commands

```bash
# Run all tests with web UI
python eval/run_promptfoo.py

# Run specific tests
python eval/run_promptfoo.py INT
python eval/run_promptfoo.py 5

# Filter by tags
python eval/run_promptfoo.py --tags critical

# Compare versions (A/B testing)
python eval/run_promptfoo.py -V v1 -V v2
python eval/run_promptfoo.py -V baseline -V experimental

# Use specific model/temperature
python eval/run_promptfoo.py --model gpt-4o -T 0.5

# Generate config without running
python eval/run_promptfoo.py --generate-only

# View previous results
python eval/run_promptfoo.py --view-only

# Show test statistics
python eval/run_promptfoo.py --stats-only

# Disable auto-open browser
python eval/run_promptfoo.py --no-view
```

### Features

- **Web UI**: Visual grid of test results
- **Version Comparison**: Side-by-side prompt version comparison
- **Export**: Download results as JSON/CSV
- **History**: Browse previous evaluation runs

### Output

```
Generating promptfoo config...
Tests: 15 | Versions: v1, v2

Running promptfoo evaluation...
[====================] 30/30 complete

Results saved to: eval/.promptfoo/output.json

Opening web UI at http://localhost:15500
Press Ctrl+C to stop the server
```

---

## 5. Interactive Mode

REPL for manual testing with persistent conversation state.

**Use for**: Development, debugging, manual exploration.

### CLI Commands

```bash
# Start interactive session
python eval/run_interactive.py

# Start with specific agent
python eval/run_interactive.py --agent reservation

# Use specific configuration
python eval/run_interactive.py --model gpt-4o -T 0.5 -V v2
```

### In-Session Commands

| Command | Action |
|---------|--------|
| `quit` / `exit` | End session |
| `reset` | Start new session (clear history) |
| `clear` | Clear terminal screen |
| `data` | Show current test data |

### Output

```
Interactive Mode
Model: gpt-4o-mini | Temperature: 0.7
Commands: quit, reset, clear, data

Test Data
----------------------------------------
Customer Name: Test User
Phone: 555-0100
----------------------------------------

Agent: Hello! Thank you for calling. How can I assist you today?

You: I'd like to make a reservation
Agent: I'd be happy to help with that. For how many guests?
  -> Tool: check_availability({})

You: 4 people for Saturday
Agent: Great! I have several times available for Saturday...
  -> Tool: check_availability({"date": "Saturday", "party_size": 4})
  <- Result: ["18:00", "19:30", "21:00"]

You: data

Test Data
----------------------------------------
Customer Name: Test User
Phone: 555-0100
Reservation: pending
----------------------------------------

You: quit
Goodbye!
```

---

## Common Options

All CLI scripts support these common options:

| Option | Short | Description |
|--------|-------|-------------|
| `--model` | `-m` | LLM model (overrides config) |
| `--temperature` | `-T` | LLM temperature (overrides config) |
| `--version` | `-V` | Prompt version from agent.yaml |
| `--json` | `-j` | Output as JSON (disables streaming) |
| `--tags` | `-t` | Filter tests by tags (comma-separated) |

---

## CI/CD Integration

For CI/CD pipelines, use JSON output mode:

```bash
# Run critical tests with JSON output
python eval/run_eval.py --tags critical --json > results.json

# Check exit code (0 = all pass, non-zero = failures)
if python eval/run_eval.py --tags critical --json > /dev/null; then
  echo "All tests passed"
else
  echo "Tests failed"
  exit 1
fi
```

### GitHub Actions Example

```yaml
- name: Run Agent Evaluations
  run: |
    cd agents/my_agent
    python eval/run_eval.py --tags critical --json > eval_results.json

- name: Upload Results
  uses: actions/upload-artifact@v3
  with:
    name: eval-results
    path: agents/my_agent/eval_results.json
```
