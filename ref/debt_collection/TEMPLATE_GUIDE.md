# Template Guide: Creating New Agents

This guide walks through creating a new multi-agent system using the debt_collection agent as a template.

---

## Quick Start

```bash
# 1. Copy the template
cp -r agents/debt_collection agents/my_new_agent

# 2. Update agent identity
# Edit agent.yaml: id, name, description

# 3. Customize your workflow
# Edit sub_agents, prompts, tools, business_rules

# 4. Run
cd agents/my_new_agent
python agents.py dev
```

---

## Step-by-Step Guide

### Step 1: Copy Template

```bash
cd /path/to/livekit-backend/agents
cp -r debt_collection my_new_agent
cd my_new_agent
```

### Step 2: Update Agent Identity

Edit `agent.yaml`:

```yaml
# BEFORE
id: debt-collection-agent-7b3f2a
name: Cartrack Debt Collection Agent
description: Multi-agent debt collection system

# AFTER
id: my-new-agent-abc123
name: My New Agent
description: Description of what your agent does
```

### Step 3: Define Your Workflow

Map out your agent flow. Example:

```
debt_collection:  Introduction -> Verification -> Negotiation -> Payment -> Closing
your_agent:       Greeting -> Qualification -> Solution -> Booking -> Followup
```

### Step 4: Update Sub-Agents

Edit `agent.yaml` sub_agents section:

```yaml
sub_agents:
  - id: greeting
    name: Greeting Agent
    description: Initial greeting and rapport building
    tools:
      - greet_customer
      - identify_caller
    instructions: prompts/prompt01_greeting.yaml

  - id: qualification
    name: Qualification Agent
    description: Qualify the customer needs
    tools:
      - ask_questions
      - record_needs
    instructions: prompts/prompt02_qualification.yaml

  # Add more agents...
```

### Step 5: Create Prompts

Create prompt files in `prompts/`:

```yaml
# prompts/prompt01_greeting.yaml
name: greeting_prompt
version: v1

prompt: |
  You are {{agent_name}}, a friendly customer service representative.

  Your goal is to greet the customer warmly and identify who you're speaking with.

  Customer name: {{customer_name}}

  Guidelines:
  - Be warm and professional
  - Confirm you're speaking with the right person
  - Ask how you can help today
```

### Step 6: Create Tools

Add tools in `tools/`:

```python
# tools/tool01_greeting.py
from livekit.agents.llm import function_tool
from shared_state import UserData

@function_tool()
async def greet_customer(
    context: RunContext[UserData],
    customer_response: str
) -> str:
    """Record that customer has been greeted.

    Args:
        customer_response: What the customer said in response to greeting
    """
    userdata = context.userdata
    userdata.call.greeted = True
    userdata.call.add_note(f"Customer greeted. Response: {customer_response}")
    return "Customer greeted successfully"
```

Register in `tools/__init__.py`:

```python
from .tool01_greeting import greet_customer, identify_caller

TOOL_REGISTRY = {
    "greet_customer": greet_customer,
    "identify_caller": identify_caller,
    # Add more tools...
}
```

### Step 7: Update State

Modify `state/` for your domain:

```python
# state/profile.py
@dataclass(frozen=True)
class CustomerProfile:
    """Immutable customer data."""
    full_name: str
    email: str
    phone: str
    account_type: str
    # Add your fields...

# state/session.py
@dataclass
class CallState:
    """Mutable call progression."""
    greeted: bool = False
    qualified: bool = False
    solution_presented: bool = False
    booking_confirmed: bool = False
    # Add your fields...
```

Update `shared_state.py`:

```python
from state import CustomerProfile, CallState

@dataclass
class UserData:
    customer: CustomerProfile
    call: CallState = field(default_factory=CallState)
    # ...
```

### Step 8: Update Agent Classes

Modify `sub_agents/` for your agents:

```python
# sub_agents/agent01_greeting.py
from .base_agent import BaseAgent

class GreetingAgent(BaseAgent):
    """Entry point agent - greets customer."""

    async def on_enter(self) -> None:
        await super().on_enter()
        self.session.generate_reply(tool_choice="none")
```

Update `sub_agents/__init__.py`:

```python
GREETING = "greeting"
QUALIFICATION = "qualification"
# ...

AGENT_CLASSES = {
    GREETING: GreetingAgent,
    QUALIFICATION: QualificationAgent,
    # ...
}
```

### Step 9: Update Entrypoint

Modify `agents.py`:

```python
from sub_agents import GREETING, create_agents

@server.rtc_session(agent_name=CONFIG.get("id", "my-new-agent"))
async def entrypoint(ctx: JobContext):
    # Load customer data from metadata
    metadata = json.loads(ctx.job.metadata) if ctx.job.metadata else get_test_customer()

    # Initialize state
    customer = CustomerProfile(**metadata.get("customer", {}))
    call_state = CallState()
    userdata = UserData(customer=customer, call=call_state)

    # Create agents
    userdata.agents = create_agents(userdata)

    # Start session
    session = AgentSession[UserData](
        userdata=userdata,
        llm=openai.LLM(model="gpt-4o-mini"),
        stt=create_stt(),
        tts=create_tts(),
    )

    await session.start(
        agent=userdata.agents[GREETING],  # Start with greeting agent
        room=ctx.room,
    )
```

### Step 10: Add Tests

Create test cases in `eval/testcases/`:

```yaml
# eval/testcases/agent01_greeting.yaml
- name: "Greeting - Happy Path"
  description: "Customer responds positively to greeting"
  agent: greeting
  conversation:
    - role: agent
      expected_action: greet
    - role: user
      message: "Yes, this is John speaking"
    - role: agent
      expected_tool: greet_customer
      expected_action: confirm_identity

- name: "Greeting - Wrong Person"
  description: "Not the expected customer"
  agent: greeting
  conversation:
    - role: user
      message: "No, John isn't here right now"
    - role: agent
      expected_tool: handle_wrong_person
```

---

## Checklist

### Files to Copy and Modify

| File | Action | Notes |
|------|--------|-------|
| `agent.yaml` | Modify | Update id, name, sub_agents, handoffs |
| `agents.py` | Modify | Update entrypoint, state initialization |
| `shared_state.py` | Modify | Update UserData fields |
| `state/profile.py` | Rewrite | Define your immutable data |
| `state/session.py` | Rewrite | Define your mutable state |
| `state/types.py` | Rewrite | Define your enums |
| `sub_agents/*.py` | Rewrite | Create your agent classes |
| `sub_agents/__init__.py` | Modify | Update agent registry |
| `sub_agents/factory.py` | Modify | Update build_prompt_variables() |
| `prompts/*.yaml` | Rewrite | Create your prompts |
| `prompts/_versions.yaml` | Modify | Update version registry |
| `tools/*.py` | Rewrite | Create your tools |
| `tools/__init__.py` | Modify | Update TOOL_REGISTRY |
| `business_rules/` | Optional | Add domain logic if needed |

### Files to Keep As-Is

| File | Notes |
|------|-------|
| `sub_agents/base_agent.py` | Context preservation works for any agent |
| `prompts/__init__.py` | Prompt loading is generic |
| `utils/id_generator.py` | ID generation is generic |
| `finetuning/logger.py` | Sample logging is generic |
| `eval/run_tests.py` | Test runner is generic |

---

## Customization Patterns

### Prompts

**Mustache Variables:**
```yaml
prompt: |
  You are {{agent_name}} from {{company_name}}.
  Customer: {{customer_name}}
  Account: {{account_type}}
```

**Conditional Sections:**
```yaml
prompt: |
  {{#has_discount}}
  Special offer: {{discount_percentage}}% off
  {{/has_discount}}
  {{^has_discount}}
  No special offers available.
  {{/has_discount}}
```

**Lists:**
```yaml
prompt: |
  Available options:
  {{#options}}
  - {{name}}: {{description}}
  {{/options}}
```

### Tools

**Basic Tool:**
```python
@function_tool()
async def my_tool(
    context: RunContext[UserData],
    param1: str,
    param2: int = 10
) -> str:
    """Tool description shown to LLM.

    Args:
        param1: Description of param1
        param2: Description of param2 (default: 10)
    """
    userdata = context.userdata
    # Do something...
    return "Result message"
```

**Tool with Handoff:**
```python
@function_tool()
async def complete_and_handoff(
    context: RunContext[UserData],
) -> tuple[Agent, str]:
    """Complete current phase and move to next agent."""
    userdata = context.userdata
    userdata.call.current_phase_done = True

    next_agent = userdata.agents["next_agent_id"]
    return (next_agent, "Handing off to next agent")
```

### State Management

**Immutable Profile (frozen=True):**
```python
@dataclass(frozen=True)
class CustomerProfile:
    # Use for data that never changes during call
    full_name: str
    account_id: str

    @classmethod
    def from_metadata(cls, data: dict) -> "CustomerProfile":
        return cls(
            full_name=data.get("full_name", ""),
            account_id=data.get("account_id", ""),
        )
```

**Mutable State:**
```python
@dataclass
class CallState:
    # Use for data that changes during call
    phase: str = "greeting"
    notes: list[str] = field(default_factory=list)

    def add_note(self, note: str) -> None:
        self.notes.append(f"[{datetime.now():%H:%M}] {note}")
```

### Handoffs

**In Tool:**
```python
@function_tool()
async def transition_to_next(context: RunContext[UserData]) -> tuple[Agent, str]:
    userdata = context.userdata
    next_agent = userdata.agents["next_agent_id"]
    userdata.prev_agent = context.agent  # Save for context preservation
    return (next_agent, "Transitioning to next phase")
```

**Agent-Initiated:**
```python
class MyAgent(BaseAgent):
    async def check_transition(self) -> None:
        userdata = self.session.userdata
        if userdata.call.should_transition:
            next_agent = userdata.agents["next_agent_id"]
            userdata.prev_agent = self
            await self.session.handoff(next_agent)
```

### Tool Registration

**In tools/__init__.py:**
```python
from .tool01_greeting import greet_customer, identify_caller
from .tool02_qualification import ask_question, record_answer
from .common_tools import schedule_callback, escalate

TOOL_REGISTRY = {
    # Greeting
    "greet_customer": greet_customer,
    "identify_caller": identify_caller,
    # Qualification
    "ask_question": ask_question,
    "record_answer": record_answer,
    # Common
    "schedule_callback": schedule_callback,
    "escalate": escalate,
}

def get_tools_by_names(names: list[str]) -> list:
    """Get tool functions by name list."""
    return [TOOL_REGISTRY[name] for name in names if name in TOOL_REGISTRY]
```

---

## Best Practices

### 1. Keep Agents Focused

Each agent should have a single responsibility:

```
BAD:  GreetingAndQualificationAgent
GOOD: GreetingAgent, QualificationAgent
```

### 2. Use Descriptive Tool Names

```python
# BAD
@function_tool()
async def do_thing(context): ...

# GOOD
@function_tool()
async def confirm_customer_identity(context): ...
```

### 3. Document Tools for LLM

The docstring is what the LLM sees:

```python
@function_tool()
async def schedule_callback(
    context: RunContext[UserData],
    date: str,
    time: str,
    reason: str
) -> str:
    """Schedule a callback for the customer.

    Use this when:
    - Customer requests to be called back later
    - Customer is busy and cannot continue
    - Customer needs to gather information

    Args:
        date: Date for callback (YYYY-MM-DD format)
        time: Time for callback (HH:MM format, business hours only)
        reason: Why the callback is needed

    Returns:
        Confirmation message with callback details
    """
```

### 4. Validate Early

Validate in profile initialization, not in tools:

```python
@dataclass(frozen=True)
class CustomerProfile:
    email: str

    def __post_init__(self):
        if self.email and "@" not in self.email:
            raise ValueError(f"Invalid email: {self.email}")
```

### 5. Use Enums for States

```python
# state/types.py
from enum import Enum

class CallPhase(Enum):
    GREETING = "greeting"
    QUALIFICATION = "qualification"
    SOLUTION = "solution"
    BOOKING = "booking"
    FOLLOWUP = "followup"

class CallOutcome(Enum):
    SUCCESS = "success"
    CALLBACK = "callback"
    NOT_INTERESTED = "not_interested"
    WRONG_NUMBER = "wrong_number"
```

### 6. Test Each Agent Independently

Create test cases per agent:

```
eval/testcases/
  agent01_greeting.yaml
  agent02_qualification.yaml
  agent03_solution.yaml
  ...
```

### 7. Version Prompts for A/B Testing

```yaml
# prompts/_versions.yaml
versions:
  v1:
    description: "Professional tone"
  v2:
    description: "Friendly tone"
  v3:
    description: "Urgent tone"
```

---

## Common Patterns

### Pattern: Conditional Handoff

```python
@function_tool()
async def process_response(
    context: RunContext[UserData],
    customer_interested: bool
) -> Union[str, tuple[Agent, str]]:
    """Process customer response and route accordingly."""
    userdata = context.userdata

    if customer_interested:
        userdata.call.qualified = True
        next_agent = userdata.agents["solution"]
        return (next_agent, "Customer interested, proceeding to solution")
    else:
        userdata.call.not_interested = True
        next_agent = userdata.agents["followup"]
        return (next_agent, "Customer not interested, scheduling followup")
```

### Pattern: State Validation Before Handoff

```python
@function_tool()
async def complete_qualification(context: RunContext[UserData]) -> tuple[Agent, str]:
    """Complete qualification and proceed to solution."""
    userdata = context.userdata

    # Validate required data collected
    if not userdata.call.needs_identified:
        return "Cannot proceed - customer needs not yet identified"

    if not userdata.call.budget_confirmed:
        return "Cannot proceed - budget not confirmed"

    # All requirements met, handoff
    userdata.call.qualified = True
    return (userdata.agents["solution"], "Qualification complete")
```

### Pattern: Dynamic Prompt Variables

```python
# sub_agents/factory.py
def build_prompt_variables(agent_id: str, userdata: UserData) -> dict:
    base_vars = {
        "agent_name": "Alex",
        "company_name": "Acme Corp",
    }

    if userdata:
        base_vars.update({
            "customer_name": userdata.customer.full_name,
            "account_type": userdata.customer.account_type,
        })

        # Agent-specific variables
        if agent_id == "solution":
            base_vars["recommended_product"] = get_recommendation(userdata)

    return base_vars
```

### Pattern: Audit Logging

```python
# state/session.py
@dataclass
class CallState:
    audit_log: list[dict] = field(default_factory=list)

    def log_event(self, event_type: str, details: dict = None) -> None:
        self.audit_log.append({
            "timestamp": datetime.now().isoformat(),
            "event": event_type,
            "details": details or {},
        })
```

---

## Troubleshooting

### Agent Not Starting

```bash
# Check agent registration
python -c "from sub_agents import AGENT_CLASSES; print(AGENT_CLASSES.keys())"
```

### Tools Not Working

```bash
# Verify tool registry
python -c "from tools import TOOL_REGISTRY; print(list(TOOL_REGISTRY.keys()))"

# Check tool in agent.yaml matches registry
grep "tools:" agent.yaml
```

### Prompt Not Loading

```bash
# Test prompt loading
python -c "from prompts import load_prompt; print(load_prompt('prompt01_greeting'))"
```

### Handoff Failing

```python
# Ensure you return tuple[Agent, str]
return (next_agent, "Handoff message")  # Correct
return next_agent  # Wrong - missing message
```

---

## Next Steps

1. Copy the template and rename
2. Define your workflow (agents and transitions)
3. Create prompts for each agent
4. Implement tools for each phase
5. Update state for your domain
6. Write test cases
7. Run and iterate

For questions, see the main [README.md](./README.md) or the LiveKit Agents documentation.
