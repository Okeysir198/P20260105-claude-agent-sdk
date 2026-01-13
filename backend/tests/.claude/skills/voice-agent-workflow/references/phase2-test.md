# Phase 2: TEST

Create the evaluation framework and test cases.

## 2.1 Eval Structure

Create the eval directory structure:

```bash
mkdir -p {agent_path}/eval
mkdir -p {agent_path}/eval/testcases
mkdir -p {agent_path}/eval/results
```

## 2.2 Framework Files

Copy core framework files from a reference implementation:

| File | Purpose |
|------|---------|
| `_provider.py` | LLM provider abstraction |
| `_console.py` | Console output utilities |
| `run_test.py` | Single test runner |
| `run_eval.py` | Full evaluation orchestrator |

**Note**: Reference implementations can be found in existing agent eval folders. Use any working agent's eval/ as a template.

## 2.3 Eval Configuration

Create `eval/eval_config.yaml`:

```yaml
type: multi  # or single
default_agent: {first_sub_agent}
agent_ids:
  - {sub_agent_1}
  - {sub_agent_2}

imports:
  userdata_module: shared_state
  userdata_class: UserData
  test_data_factory: shared_state:create_test_userdata
  agent_classes_module: sub_agents
  agent_classes_var: AGENT_CLASSES
  tools_module: tools
  tools_function: get_tools_by_names
```

## 2.4 Test Case Format

For each sub-agent, create `testcases/agent0X_{sub_agent}.yaml`:

```yaml
agent_id: {agent_id}
sub_agent_id: {sub_agent}
description: "Tests for {sub_agent_name}"

default_test_data:
  full_name: "Test User"
  # Domain-specific fields...

test_cases:
  - name: "{PREFIX}-001: {scenario}"
    test_type: single_turn
    tags: [unit, {sub_agent}, happy-path]
    turns:
      - user_input: "{expected_input}"
        assertions:
          - type: contains_function_call
            value: "{expected_tool}"
```

### Test Type Reference

| Type | When to Use |
|------|-------------|
| `single_turn` | Testing one input/output pair |
| `multi_turn` | Testing conversation flow |
| `e2e` | Testing full agent handoff chain |

### Assertion Types

| Type | Value | Description |
|------|-------|-------------|
| `contains_function_call` | tool name | Agent calls specified tool |
| `contains_text` | substring | Response contains text |
| `not_contains_text` | substring | Response does NOT contain text |
| `matches_regex` | pattern | Response matches regex |
| `handoff_to` | agent_id | Agent hands off to specified agent |

## 2.5 Simulated User Config

Create `eval/simulated_user_config.yaml`:

```yaml
personas:
  cooperative:
    style: "Direct and helpful"
    compliance: high
  hesitant:
    style: "Uncertain, asks for clarification"
    compliance: medium
  difficult:
    style: "Resistant, tests boundaries"
    compliance: low
```

## 2.6 Test Case Guidelines

### Naming Convention

Use prefixes based on sub-agent:
- `GRT-XXX` - Greeting tests
- `VER-XXX` - Verification tests
- `RES-XXX` - Resolution tests
- `E2E-XXX` - End-to-end tests

### Coverage Goals

For each sub-agent, create tests for:
1. Happy path (expected flow)
2. Edge cases (unusual inputs)
3. Error handling (invalid data)
4. Boundary conditions (limits)
5. Handoff triggers (transitions)

## 2.7 Success Criteria

Phase 2 is complete when:
- [ ] eval/ directory exists
- [ ] Framework files are copied
- [ ] eval_config.yaml is valid
- [ ] At least 3 test cases per sub-agent
- [ ] At least 1 E2E test case

## Related Skills

- **eval-generator**: Provides detailed test case templates and assertion patterns
