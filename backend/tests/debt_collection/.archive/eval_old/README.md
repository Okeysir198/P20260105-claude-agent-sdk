# Eval Framework

Self-contained testing framework for LiveKit voice agents. Supports three testing modes:
- **Single-turn tests**: One user input, one agent response
- **Multi-turn tests**: Scripted conversation flows with assertions
- **Simulated user**: LLM-powered user simulation for end-to-end testing

## Quick Start

```bash
cd eval/

# List all tests
python run_tests.py --list

# Run specific test
python run_tests.py --test "INT-001: Person confirms identity"

# Run by file
python run_tests.py --file agent01_introduction.yaml

# Run by tags
python run_tests.py --tags unit,introduction

# Custom input
python run_tests.py --input "Hello" --agent introduction

# Interactive chat
python run_tests.py --interactive

# PromptFoo evaluation
python run_eval.py
python run_eval.py --view  # Web UI at localhost:15500

# Simulated user (LLM-powered)
python run_simulation.py
python run_simulation.py --persona difficult --max-turns 10
```

## Configuration

Edit `eval_config.yaml`:

```yaml
type: multi                    # "single" or "multi" agent system
default_agent: introduction    # Starting agent
agent_ids:                     # All agent IDs to instantiate
  - introduction
  - verification
  - negotiation
  - payment
  - closing

imports:
  userdata_module: shared_state
  userdata_class: UserData
  test_data_factory: eval.test_data:create_test_userdata
  agent_classes_module: sub_agents
  agent_classes_var: AGENT_CLASSES
  tools_module: tools
  tools_function: get_tools_by_names
```

## Copy to Another Agent

1. Copy entire `eval/` folder to your agent
2. Edit `eval_config.yaml` with your agent's settings
3. Edit `test_data.py` with your test data factory
4. Add test cases to `testcases/`

## Folder Structure

```
eval/
├── eval_config.yaml           # Test configuration (edit this)
├── test_data.py               # Test data factory (edit this)
├── _provider.py               # Core engine (don't edit)
├── _console.py                # Output formatting
├── run_tests.py               # CLI runner for scripted tests
├── run_eval.py                # PromptFoo integration
├── run_simulation.py          # CLI for simulated user
├── promptfooconfig.yaml       # PromptFoo config
├── simulated_user_config.yaml # Simulated user config
├── simulated_user/            # Simulated user module
│   ├── __init__.py
│   ├── types.py               # Data structures
│   ├── config.py              # Config loading
│   ├── console.py             # Rich output
│   ├── user_agent.py          # LangChain user agent
│   ├── session_runner.py      # LiveKit session wrapper
│   └── simulation.py          # LangGraph simulation loop
└── testcases/                 # Test YAML files
    ├── agent01_introduction.yaml
    └── ...
```

## CLI Reference

### run_tests.py

| Flag | Description |
|------|-------------|
| `--list`, `-l` | List all tests |
| `--test NAME`, `-t` | Run single test |
| `--file FILE`, `-f` | Run tests from file |
| `--tags TAGS` | Filter by tags (comma-separated) |
| `--agent AGENT`, `-a` | Target agent for --input |
| `--input TEXT` | Run custom input |
| `--interactive`, `-i` | Interactive chat mode |
| `--json`, `-j` | JSON output |

### run_eval.py

| Flag | Description |
|------|-------------|
| `--view`, `-v` | Open web UI |
| `--config FILE`, `-c` | Custom config file |
| `--output FILE`, `-o` | Save results to file |

### run_simulation.py

| Flag | Description |
|------|-------------|
| `--config FILE`, `-c` | Custom YAML config file |
| `--model MODEL`, `-m` | LLM model (e.g., gpt-4o-mini) |
| `--provider PROVIDER` | Model provider (openai, anthropic) |
| `--temperature TEMP`, `-t` | Sampling temperature (0.0-1.0) |
| `--persona PRESET`, `-p` | Preset persona (cooperative, difficult, confused, third_party) |
| `--goal TEXT`, `-g` | Goal description for simulated user |
| `--initial-message TEXT` | First message from simulated user |
| `--max-turns N` | Maximum conversation turns |
| `--agent AGENT`, `-a` | Starting agent |
| `--json`, `-j` | Output as JSON |
| `--quiet`, `-q` | Minimal output |
| `--no-tools` | Hide tool call output |

## Simulated User

The simulated user uses LangChain/LangGraph to simulate realistic user behavior during conversations.

### Configuration

Edit `simulated_user_config.yaml`:

```yaml
model:
  provider: openai
  name: gpt-4o-mini
  temperature: 0.7
  max_tokens: 500

persona:
  name: "John Smith"
  system_prompt: |
    You are simulating a person receiving a debt collection call.
    Be cooperative but cautious.
    When the call ends, say "goodbye" to terminate.
  traits: [cooperative, cautious]
  initial_message: "Hello?"

simulation:
  max_turns: 20
  stop_phrases: ["bye", "goodbye", "good bye", "have a good day"]
  goal_description: "Complete the call and agree to payment plan"

agent:
  start_agent: introduction

output:
  verbose: true
  show_tool_calls: true
```

### Preset Personas

| Persona | Description |
|---------|-------------|
| `cooperative` | Agrees quickly, answers directly |
| `difficult` | Frustrated, may deny debt or demand manager |
| `confused` | Asks many questions, needs clarification |
| `third_party` | Not the debtor, spouse answering phone |

### Termination

Simulation ends when ANY message (user or agent) contains:
- "bye", "goodbye", "good bye"
- "have a good day", "thank you for your time"

### Programmatic Usage

```python
from simulated_user import simulate, SimulationResult

# Run with defaults
result = simulate()

# Run with overrides
result = simulate(
    model="gpt-4o",
    temperature=0.9,
    max_turns=15,
    start_agent="verification"
)

# Access results
for turn in result.turns:
    print(f"User: {turn.user_message}")
    print(f"Agent: {turn.agent_response}")
    for event in turn.events:
        print(f"  [{event.type}] {event.content}")

# JSON output
print(result.to_json())
```

## Test Case Format

```yaml
# testcases/agent01_introduction.yaml
agent_id: debt_collection
sub_agent_id: introduction

test_cases:
  - name: "INT-001: Person confirms identity"
    test_type: single_turn
    tags: [unit, introduction, happy-path]
    turns:
      - user_input: "Yes, speaking"
```

## Programmatic Usage

```python
from _provider import (
    run_single_turn,
    run_conversation,
    run_test_case,
    get_test_case
)

# Single turn
result = run_single_turn("Yes, speaking", target_agent="introduction")

# Multi-turn
result = run_conversation(
    turns=[{"user_input": "Yes"}, {"user_input": "My ID is 123"}],
    start_agent="introduction"
)

# Run test case
test = get_test_case("INT-001: Person confirms identity")
result = run_test_case(test)

# Access results
print(result.get_assistant_messages())
print(result.get_tool_calls())
print(result.to_json())
```

## Test Tags

| Tag | Description |
|-----|-------------|
| `unit` | Single agent tests |
| `integration` | Multi-agent flow |
| `e2e` | End-to-end scenarios |
| `happy-path` | Success cases |
| `introduction` | Introduction agent |
| `verification` | Verification agent |
| `negotiation` | Negotiation agent |
| `payment` | Payment agent |
| `closing` | Closing agent |
