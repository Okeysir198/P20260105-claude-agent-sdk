# Sub-Agents

Multi-agent debt collection system with 5 specialized agents (POPI compliant).

## Public API

```python
from sub_agents import create_agents, INTRODUCTION

# Create all agents
agents = create_agents(userdata)

# Start with introduction agent
session.start(agent=agents[INTRODUCTION])
```

## Agent Flow

```
Introduction → Verification → Negotiation → Payment → Closing
     │              │              │            │
     └──────────────┴──────────────┴────────────┴─► Common tools available
```

## Agents

| Agent | Purpose | Key Tools | Handoff To |
|-------|---------|-----------|------------|
| **Introduction** | Identity confirmation | `confirm_person`, `handle_wrong_person` | Verification / Closing |
| **Verification** | POPI compliance (2+ fields) | `verify_field`, `mark_unavailable` | Negotiation / Closing |
| **Negotiation** | Payment arrangement | `offer_settlement`, `accept_arrangement` | Payment / Closing |
| **Payment** | Banking/portal capture | `setup_debicheck`, `send_portal_link` | Closing |
| **Closing** | Wrap-up, referrals | `offer_referral`, `end_call` | Terminal |

## Directory Structure

```
sub_agents/
├── __init__.py              # AGENT_CLASSES, create_agents export
├── factory.py               # Agent creation & prompt building
├── base_agent.py            # BaseAgent class, constants
├── agent01_introduction.py
├── agent02_verification.py
├── agent03_negotiation.py
├── agent04_payment.py
└── agent05_closing.py
```

## Key Concepts

### Handoffs (Tool-Driven)
```python
@function_tool()
async def confirm_person(context: RunContext_T) -> tuple[Agent, str]:
    userdata = context.userdata
    userdata.call.person_confirmed = True
    return await transfer_to_agent("verification", context)
```

### Context Preservation
- Last 6 chat items copied from previous agent
- System message added with current state
- Handled automatically in `BaseAgent.on_enter()`

### Agent Factory (`factory.py`)
- `create_agents(userdata)` - Creates all 5 agents with instructions and tools
- `get_agent_instructions(agent_id, userdata)` - Loads and formats prompts
- `build_prompt_variables(agent_id, userdata)` - Builds template variables

## Adding New Agent

1. Create `agent0X_name.py`:
```python
from .base_agent import BaseAgent

class NameAgent(BaseAgent):
    def __init__(self, instructions: str, tools: list, **kwargs):
        super().__init__(instructions=instructions, tools=tools, **kwargs)
```

2. Register in `__init__.py`:
```python
from .agent0X_name import NameAgent
AGENT_CLASSES["name"] = NameAgent
```

3. Create prompt: `prompts/prompt0X_name.yaml`

4. Configure in `agent.yaml`:
```yaml
sub_agents:
  - id: name
    tools: [tool1, tool2]
    instructions: prompts/prompt0X_name.yaml
```

## Constants

```python
CHAT_CONTEXT_MAX_ITEMS = 6   # Context from previous agent
DYNAMIC_PROMPT_AGENTS = {NEGOTIATION, PAYMENT}  # Agents with userdata-aware prompts
```

## Related

- Tools: `../tools/README.md`
- Prompts: `../prompts/`
- Business Rules: `../business_rules/README.md`
- Shared State: `../shared_state.py`
