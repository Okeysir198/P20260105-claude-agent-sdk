---
name: eval-generator
description: Generate eval framework with LangGraph test workflows for voice agents. Use when the user asks to create tests, generate test cases, set up evaluation framework, add test automation, or run evals for voice/chat agents. Supports LLM-powered test case generation from agent analysis.
---

# Eval Framework Generator

Generate a complete evaluation framework for LiveKit voice agents. This skill copies a generic eval framework and adapts the configuration files for your specific agent.

## Quick Workflow Checklist

Copy and track your progress:

```
Eval Framework Setup:
- [ ] Step 1: Create eval directory structure
- [ ] Step 2: Analyze target agent (read agent.yaml, prompts, tools)
- [ ] Step 3: Copy generic framework files from templates/
- [ ] Step 4: Generate eval_config.yaml (configure imports)
- [ ] Step 5: Generate simulated_user_config.yaml (add personas)
- [ ] Step 6: Create domain-specific test cases
- [ ] Step 7: Verify installation (run python eval/run_list.py)
```

## Validation Loop

After generating or modifying test cases:

1. Run validation: `python scripts/validate_eval.py ./eval`
2. If validation fails:
   - Review error messages carefully
   - Fix issues in test case YAML files
   - Run validation again
3. Only proceed when validation passes
4. Run a smoke test: `python eval/run_test.py "TEST-001"`

## Automated Test Case Generation (LLM-Powered)

Generate test cases automatically by analyzing agent architecture.

### Quick Start

1. **Analyze Agent Structure**
   ```bash
   python scripts/analyze_agent.py /path/to/agent -o analysis.json
   ```

2. **Generate Test Cases with LLM**
   ```bash
   # With streaming progress
   python scripts/generate_testcases.py analysis.json /path/to/agent/eval --streaming

   # Parallel generation (faster)
   python scripts/generate_testcases.py analysis.json /path/to/agent/eval --max-concurrent 5
   ```

3. **Validate Generated Tests**
   ```bash
   python scripts/validate_eval.py /path/to/agent/eval
   ```

### What Gets Analyzed

The analyzer extracts:
- Sub-agent definitions and workflows
- Tool functions with parameters and descriptions
- Prompt content and expected behaviors
- UserData fields and sample test data
- Version configurations

### What Gets Generated

For each sub-agent:
- 3-5 tests per tool (happy path, edge case, negative scenario)
- 2-3 behavior tests based on prompt content
- Realistic user inputs for the domain

Plus E2E tests:
- Critical path through all agents
- Alternative flow tests
- Error recovery scenarios

### Configuration Options

```bash
python scripts/generate_testcases.py analysis.json output/ \
    --model claude-sonnet-4-20250514 \  # LLM model
    --streaming \                        # Show progress
    --max-concurrent 5                   # Parallel limit
```

### After Generation

1. Review generated test cases in `eval/testcases/`
2. Customize LLM rubrics for your domain
3. Add edge cases based on real usage patterns
4. Run tests: `python -m eval run --file agent01_introduction.yaml`

## Architecture: Copy Framework + Adapt Configs

The eval framework is **100% generic**. All Python files use dynamic imports from `eval_config.yaml`. Only **2 files** need customization:

| File | Purpose | Customization |
|------|---------|---------------|
| `eval_config.yaml` | Framework config | Agent type, IDs, imports |
| `simulated_user_config.yaml` | Simulation personas | Domain-specific personas |
| `testcases/*.yaml` | Test cases | Domain-specific tests |

## Dependencies

```
pydantic>=2.0
langchain>=0.2
langgraph>=0.2
livekit-agents>=0.8
pyyaml
click
rich
python-dotenv
# Optional: npm install -g promptfoo  (for web UI)
```

## Working Directory Rules

The working directory IS the target agent folder. All paths are relative to `./`:

```bash
# Correct paths:
./eval/run_test.py
./eval/eval_config.yaml
./eval/testcases/e2e_critical.yaml

# WRONG paths (do not use):
livekit-backend/agents/xyz/eval/...
```

## Step 1: Create Eval Directory Structure

```bash
# Verify working directory
pwd

# Create eval structure
mkdir -p ./eval/testcases ./eval/core ./eval/schemas ./eval/workflows \
         ./eval/promptfoo ./eval/prompts ./eval/cli
```

## Step 2: Analyze Target Agent

Read the agent configuration:

```
Read agent.yaml
Glob prompts/**/*.yaml
Glob tools/**/*.py
Glob sub_agents/**/*.py  (if multi-agent)
```

Extract:
- `agent_type`: "single" or "multi"
- `default_agent`: Main agent ID
- `agent_ids`: List of all agent IDs
- `domain`: Business domain (restaurant, healthcare, support, etc.)

## Step 3: Copy Generic Framework Files

Copy ALL files from `templates/` to `./eval/`. These are 100% generic:

**Root files:**
- `__init__.py`
- `runner.py`
- `console.py`
- `run_test.py`
- `run_eval.py`
- `run_simulation.py`
- `run_interactive.py`
- `run_promptfoo.py`
- `run_list.py`
- `README.md`
- `LANGGRAPH.md`
- `PROMPTFOO.md`

**Subdirectories:**
- `core/__init__.py`, `config.py`, `loader.py`, `session.py`, `events.py`, `userdata.py`
- `schemas/__init__.py`, `models.py`, `test_case.py`
- `workflows/__init__.py`, `test_workflow.py`, `eval_workflow.py`, `simulation_workflow.py`, `batch_workflow.py`
- `promptfoo/__init__.py`, `provider.py`, `config_generator.py`, `runner.py`
- `cli/__init__.py`, `cli_utils.py`
- `prompts/llm_judge.yaml`

## Step 4: Generate eval_config.yaml

Use `templates/eval_config.yaml.template` with these placeholders:

```yaml
# eval_config.yaml
type: {{agent_type}}           # "single" or "multi"
default_agent: {{default_agent}}
agent_ids:
{{agent_ids_yaml}}             # YAML list, indented with "  - "

imports:
  userdata_module: shared_state
  userdata_class: UserData
  test_data_factory: shared_state:create_test_userdata
  agent_classes_module: sub_agents
  agent_classes_var: AGENT_CLASSES
  tools_module: tools
  tools_function: get_tools_by_names
```

**Example for multi-agent:**
```yaml
type: multi
default_agent: greeter
agent_ids:
  - greeter
  - order_taker
  - payment
```

**Example for single-agent:**
```yaml
type: single
default_agent: main
agent_ids:
  - main
```

## Step 5: Generate simulated_user_config.yaml

Use `templates/simulated_user_config.yaml.template` with domain-specific content:

| Placeholder | Description |
|-------------|-------------|
| `{{domain}}` | Business domain |
| `{{persona_name}}` | Default persona name |
| `{{persona_description}}` | Brief persona description |
| `{{persona_background}}` | Bullet points of background facts |
| `{{persona_behavior_guidelines}}` | Behavior guidelines |
| `{{persona_traits_yaml}}` | YAML list of traits |
| `{{simulation_goal}}` | Goal description |
| `{{default_agent}}` | Starting agent ID |
| `{{user_type}}` | Type of user (customer, patient, caller) |
| `{{cooperative_goal}}` | What cooperative user wants |

**Example: Restaurant Domain:**
```yaml
persona:
  name: "Alex Johnson"
  system_prompt: |
    You are simulating Alex Johnson, a customer calling a restaurant.

    Your background:
    - You want to make a reservation for 4 people
    - You prefer Friday evening around 7pm
    - You have no dietary restrictions

    Behavior guidelines:
    - Be polite and clear about your reservation needs
    - Ask about available times if your preferred slot is unavailable

  traits:
    - polite
    - organized
    - flexible

simulation:
  goal_description: |
    Complete the reservation call by:
    1. Requesting a reservation for your party
    2. Confirming date, time, and party size
    3. Providing your name and contact information
    4. Ending the call politely with "goodbye"
```

## Step 6: Generate Domain-Specific Test Cases

Create test case files in `./eval/testcases/`:

**Naming convention:**
- `agent01_{agent_id}.yaml` - Unit tests per agent
- `agent00_e2e_flow.yaml` - End-to-end workflow tests
- `e2e_critical.yaml` - Minimal critical path tests

**Test case structure:**
```yaml
agent_id: my_agent
sub_agent_id: {{agent_id}}

default_test_data:
  customer_name: "Test Customer"
  # ... domain-specific fields

test_cases:
  - name: "TEST-001: Happy path"
    tags: [unit, {{agent_id}}]
    turns:
      - user_input: "Hello"
        assertions:
          - type: contains
            value: "welcome"
          - type: contains_function_call
            value: greet_customer
```

**Assertion types:**
- `contains` / `not_contains` - Substring checks
- `contains_any` / `contains_all` - Multiple options
- `equals` - Exact match
- `matches` - Regex pattern
- `contains_function_call` - Tool invocation
- `llm_rubric` - LLM semantic evaluation

## Step 7: Verify Installation

```bash
cd <target_agent>
python eval/run_list.py           # List all test cases
python eval/run_test.py "TEST-001"  # Run a single test
python eval/run_eval.py "TEST"      # Run with assertions
python eval/run_interactive.py      # Interactive mode
```

## Files NOT to Copy (Auto-Generated)

- `results.json` - Created by eval runs
- `promptfooconfig.yaml` - Created by promptfoo runner
- `__pycache__/` - Python cache

## Template Files Reference

```
templates/
  eval_config.yaml.template         # Needs {{agent_type}}, {{default_agent}}, {{agent_ids_yaml}}
  simulated_user_config.yaml.template  # Needs domain-specific placeholders

  # Generic Python files (copy as-is):
  __init__.py
  runner.py
  console.py
  run_*.py
  core/*.py
  schemas/*.py
  workflows/*.py
  promptfoo/*.py
  cli/*.py
  prompts/llm_judge.yaml

  # Documentation:
  README.md
  LANGGRAPH.md
  PROMPTFOO.md

  # Test case templates:
  testcases/_template.yaml
  testcases/e2e_critical.yaml.template
```

## Example Output Structure

```
<target_agent>/
  eval/
    __init__.py
    eval_config.yaml          # Configured for this agent
    simulated_user_config.yaml  # Domain-specific
    runner.py
    console.py
    run_test.py
    run_eval.py
    run_simulation.py
    run_promptfoo.py
    run_interactive.py
    run_list.py
    README.md
    LANGGRAPH.md
    PROMPTFOO.md
    core/
      __init__.py
      config.py
      loader.py
      session.py
      events.py
      userdata.py
    schemas/
      __init__.py
      models.py
      test_case.py
    workflows/
      __init__.py
      test_workflow.py
      eval_workflow.py
      simulation_workflow.py
      batch_workflow.py
    promptfoo/
      __init__.py
      provider.py
      config_generator.py
      runner.py
    cli/
      __init__.py
      cli_utils.py
    prompts/
      llm_judge.yaml
    testcases/
      e2e_critical.yaml
      agent01_{agent}.yaml
```
