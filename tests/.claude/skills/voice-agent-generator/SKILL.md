---
name: voice-agent-generator
description: >
  Generate production-ready LiveKit voice agents with multi-agent workflows.
  Trigger phrases: "create voice agent", "build agent", "scaffold agent",
  "LiveKit agent", "new voice agent", "generate agent"
---

# Voice Agent Generator

Generate production-ready LiveKit voice agents using SDK 1.2+ patterns.

## CRITICAL: Working Directory Rules

The working directory IS the target agent folder. The skill is responsible for:
1. Creating the folder if it doesn't exist
2. Creating all subdirectories and files

**FIRST ACTION - Create the agent folder and structure:**
```bash
# Verify working directory and create structure
pwd
mkdir -p ./state ./sub_agents ./tools ./prompts
ls -la ./
```

**Path Rules:**
- ✅ CORRECT: `./agent.yaml`, `./agents.py`, `./state/types.py`
- ❌ WRONG: `livekit-backend/agents/xyz/agent.yaml` (nested path)
- ❌ WRONG: `../somewhere/agent.yaml` (parent path)

Do NOT:
- Add `livekit-backend/agents/` prefix to file paths
- Create a new subdirectory for the agent (the working directory IS the agent folder)
- Reference paths from the debt_collection example literally

## Prerequisites

Before generating, gather:
1. Agent name and purpose (e.g., "customer support", "appointment booking")
2. Sub-agent workflow (sequence of conversation phases)
3. Tools needed for each sub-agent
4. State fields to track during calls
5. TTS/STT/LLM provider preferences

## Default Configuration

**IMPORTANT**: Always generate agent ID with a random suffix (e.g., `my-agent-7b3f2a`).

```yaml
# Default LLM
llm:
  provider: openai
  model: gpt-4o-mini
  temperature: 0.2

# Default STT
stt:
  provider: deepgram
  model: nova-2

# Default TTS (supertonic_tts)
tts:
  provider: supertonic_tts
  supertonic_tts:
    api_url: http://localhost:18012
    voice_style: M1
    speed: 1.2
    total_step: 5
    silence_duration: 0.3
```

Available TTS providers: cartesia, chatterbox_tts, kokoro_tts, supertonic_tts

## Step 1: Analyze Reference Implementation

Use Read tool to study the reference agent structure:

```
livekit-backend/agents/debt_collection/
├── agents.py              # Main entrypoint with AgentSession
├── agent.yaml             # Configuration (LLM, STT, TTS, sub-agents)
├── shared_state.py        # UserData container
├── state/
│   ├── types.py           # Enums (Outcome, PersonType, etc.)
│   ├── profile.py         # Immutable profile (frozen=True)
│   └── session.py         # Mutable call state
├── sub_agents/
│   ├── base_agent.py      # BaseAgent with context preservation
│   ├── factory.py         # create_agents() factory
│   └── agent01_*.py       # Individual agent classes
├── tools/
│   ├── __init__.py        # TOOL_REGISTRY and get_tools_by_names()
│   └── tool01_*.py        # Tool modules per phase
└── prompts/
    ├── __init__.py        # load_prompt(), format_prompt()
    └── prompt01_*.yaml    # YAML prompts with Mustache templates
```

Read these files to understand patterns:
- `agents.py` - Entrypoint structure
- `shared_state.py` - UserData pattern
- `sub_agents/base_agent.py` - Agent class pattern
- `tools/__init__.py` - Tool registry pattern
- `prompts/__init__.py` - Prompt loading

## Step 2: Create Directory Structure

**CRITICAL PATH RULES** (violations will break the agent):

1. Run `pwd` first to confirm you're in the correct directory
2. ALL files go in `./` (current directory) - NO nested paths
3. Use Write tool with paths like `./agent.yaml`, NOT `livekit-backend/agents/xyz/agent.yaml`

```bash
# FIRST: Verify working directory
pwd

# THEN: Create subdirectories in current working directory
mkdir -p ./state ./sub_agents ./tools ./prompts

# Verify structure
ls -la ./
```

When using Write tool, use relative paths:
- `./agent.yaml` ✅
- `./agents.py` ✅
- `./state/types.py` ✅
- `./sub_agents/__init__.py` ✅

## Step 3: Generate Configuration (agent.yaml)

Create `agent.yaml` with:
- Agent identity (id, name, description)
- LLM config (provider, model, temperature)
- STT config (provider, model)
- TTS config (provider, voice settings)
- Sub-agents list with tools and instructions
- Handoff definitions

See `references/livekit-patterns.md` for configuration structure.

## Step 4: Generate State Module

Create state files:

1. `state/types.py` - Enums for outcomes, statuses, types
2. `state/profile.py` - Immutable profile dataclass (frozen=True)
3. `state/session.py` - Mutable call state dataclass
4. `shared_state.py` - UserData container aggregating profile + session

**CRITICAL RULES for state:**

1. **Check None before numeric comparisons** - Optional fields may be None:
   ```python
   def is_complete(self) -> bool:
       if self.count is None:  # Check None FIRST!
           return False
       return 1 <= self.count <= 10  # Now safe
   ```

2. **Domain-specific dataclasses** - Add fields specific to your domain:
   ```python
   @dataclass
   class ReservationDetails:
       date: Optional[str] = None
       time: Optional[str] = None
       party_size: Optional[int] = None

       def is_complete(self) -> bool:
           if self.party_size is None:
               return False
           return all([self.date, self.time, 1 <= self.party_size <= 20])
   ```

See `references/state-management.md` for patterns.

## Step 5: Generate Tools

Create tool modules:

1. `tools/__init__.py` - TOOL_REGISTRY dict and get_tools_by_names()
2. `tools/common_tools.py` - Shared tools (schedule_callback, escalate, end_call)
3. `tools/tool01_{phase}.py` - Phase-specific tools

Each tool must use:
- `@function_tool()` decorator
- `RunContext[UserData]` for state access
- `Annotated[type, Field(description=...)]` for parameters

**CRITICAL RULES for tools:**

1. **Import `Any` from typing, not `any`** - `any` is a builtin function, not a type:
   ```python
   from typing import Any  # Correct
   def foo() -> tuple[Any, str] | Any:  # Correct
   # NOT: tuple[any, str] | any  # WRONG - causes TypeError
   ```

2. **Place `context` BEFORE optional parameters** - Python requires non-default params first:
   ```python
   async def my_tool(
       required_param: str,
       context: RunContext_T,  # Before optional params!
       optional_param: str = None,  # After context
   ) -> str:
   ```

3. **get_tools_by_names must have `strict` parameter**:
   ```python
   def get_tools_by_names(tool_names: list[str], strict: bool = True) -> list:
   ```

**Complete Tool Example:**

```python
"""tools/tool01_verification.py - Example verification tool."""

from typing import Annotated, Literal
from pydantic import Field
from livekit.agents.llm import function_tool, ToolError
from livekit.agents.voice import Agent, RunContext

from shared_state import UserData

# Type alias for RunContext with UserData
RunContext_T = RunContext[UserData]


@function_tool()
async def verify_identity(
    field: Annotated[
        Literal["name", "email", "phone", "id_number"],
        Field(description="Field to verify")
    ],
    provided_value: Annotated[str, Field(description="Value provided by customer")],
    context: RunContext_T,
) -> str:
    """
    Verify customer identity by checking provided value against records.

    Usage: Call when customer provides information to verify their identity.
    Compare at least 2 fields before marking as verified.
    """
    userdata = context.userdata
    profile = userdata.profile
    session = userdata.session

    # Get actual value from profile
    actual_values = {
        "name": profile.name,
        "email": profile.email,
        "phone": profile.phone,
        "id_number": getattr(profile, "id_number", None),
    }
    actual = actual_values.get(field)

    if not actual:
        raise ToolError(f"Field '{field}' not available for verification")

    # Simple comparison (use fuzzy matching in production)
    if provided_value.lower().strip() == actual.lower().strip():
        session.verified_fields.append(field)
        session.add_note(f"Verified: {field}")

        if len(session.verified_fields) >= 2:
            session.verified = True
            return f"Identity verified. {field} confirmed. You are now verified."

        return f"Thank you. {field} confirmed. Please verify one more field."
    else:
        session.verification_attempts += 1
        if session.verification_attempts >= 3:
            raise ToolError("Maximum verification attempts exceeded")
        return f"That doesn't match our records. Please try again."
```

See `references/tool-design.md` for patterns.

## Step 6: Generate Prompts

Create prompt files:

1. `prompts/__init__.py` - load_prompt(), format_prompt() with Mustache (use chevron library)
2. `prompts/_versions.yaml` - Version tracking file
3. `prompts/prompt01_{agent}.yaml` - YAML with version, metadata, prompt

**CRITICAL: `prompts/__init__.py` must include:**
```python
import chevron  # Use chevron for Mustache templating, not pystache

def format_instruction(template: str, **variables) -> str:
    """Alias for format_prompt for backward compatibility."""
    return format_prompt(template, **variables)

__all__ = [
    "load_prompt",
    "format_prompt",
    "format_instruction",  # Required for eval framework!
]
```

Prompts must follow TTS optimization rules:
- Plain text only (no markdown, JSON, code)
- Brief responses (1-3 sentences, under 25 words)
- Spell out numbers ("oh-one-one" not "011")

See `references/prompt-best-practices.md` for TTS rules.

## Step 7: Generate Sub-Agents

Create sub-agent files:

1. `sub_agents/base_agent.py` - BaseAgent with on_enter(), context preservation
2. `sub_agents/factory.py` - AGENT_CLASSES dict, create_agents()
3. `sub_agents/agent01_{name}.py` - Minimal agent class extending BaseAgent
4. `sub_agents/__init__.py` - **Must export AGENT_CLASSES from factory**

**CRITICAL: `sub_agents/__init__.py` must include:**
```python
from .factory import create_agents, AGENT_CLASSES

__all__ = [
    "BaseAgent",
    "create_agents",
    "AGENT_CLASSES",  # Required for eval framework!
    # ... agent classes
]
```

Agents use composition, not customization - pass instructions and tools via constructor.

## Step 8: Generate Main Entrypoint

Create `agents.py` with:
- STT/TTS factory functions
- AgentServer with @server.rtc_session decorator
- entrypoint() async function
- AgentSession initialization with userdata

## Step 9: Validate Structure

Use Bash to verify in current directory:

```bash
# Check all required files exist (in current working directory)
ls -la ./

# Verify Python syntax (use current directory paths)
python -m py_compile ./agents.py
python -m py_compile ./shared_state.py
```

## File Templates

Templates are in `templates/` subdirectory:

**Core Files:**
- `agent.yaml.template` - Configuration with LLM/STT/TTS settings
- `agents.py.template` - Main entrypoint with AgentSession
- `shared_state.py.template` - UserData container

**State Module:**
- `state/__init__.py.template`
- `state/types.py.template` - Enums (CallOutcome, etc.)
- `state/profile.py.template` - Immutable profile (frozen=True)
- `state/session.py.template` - Mutable session state

**Sub-Agents:**
- `sub_agents/__init__.py.template`
- `sub_agents/base_agent.py.template` - BaseAgent with context preservation
- `sub_agents/factory.py.template` - AGENT_CLASSES and create_agents()

**Tools:**
- `tools/__init__.py.template` - TOOL_REGISTRY and get_tools_by_names()
- `tools/common_tools.py.template` - schedule_callback, escalate, end_call

**Prompts:**
- `prompts/__init__.py.template` - load_prompt(), format_prompt()
- `prompts/_versions.yaml.template` - Version tracking

**Business Rules:**
- `business_rules/__init__.py.template`
- `business_rules/config.py.template` - Domain configuration
- `business_rules/calculator.py.template` - Domain calculations

**Utilities:**
- `utils/__init__.py.template`
- `utils/id_generator.py.template`
- `utils/fuzzy_match.py.template`

## Reference Documentation

Pattern references in `references/`:
- `livekit-patterns.md` - Agent, AgentSession, STT/LLM/TTS factories
- `tool-design.md` - @function_tool, RunContext, Annotated params
- `state-management.md` - UserData, Profile, Session, Types
- `prompt-best-practices.md` - TTS optimization, prompt structure

## Output Checklist

After generation, verify:

- [ ] agent.yaml has valid YAML syntax
- [ ] All Python files pass syntax check
- [ ] TOOL_REGISTRY contains all tools from agent.yaml
- [ ] Sub-agents match those defined in agent.yaml
- [ ] Prompts use Mustache syntax ({{variable}})
- [ ] No hardcoded secrets or API keys
