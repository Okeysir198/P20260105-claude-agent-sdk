# Debt Collection Multi-Agent System

> **Last Updated:** 2025-12-17
> **Status:** Production Ready

POPI-compliant voice agent for debt collection built with LiveKit Agents SDK 1.2+. Features 5 specialized agents with modular state management, prompt versioning, and A/B testing support.

---

## Architecture

```
+---------------------------------------------------------------------+
|                         AgentSession                                |
|   LLM: gpt-4o-mini | STT: Deepgram | TTS: Cartesia/Chatterbox      |
+---------------------------------------------------------------------+
|                                                                     |
|  Introduction --> Verification --> Negotiation --> Payment --> Closing
|       |               |                |             |           |
|   Confirm          POPI Check      Negotiate      Capture     Wrap-up
|   Identity         2+ fields       Payment        Details     Referrals
|       |               |                |             |           |
|       v               v                v             v           v
|  [Tools x4]       [Tools x4]      [Tools x9]    [Tools x9]   [Tools x5]
|                                                                     |
+---------------------------------------------------------------------+
|                        Shared Components                            |
+---------------------------------------------------------------------+
|  UserData       | prompts/       | tools/        | business_rules/ |
|  (state)        | (versioned)    | (registry)    | (domain logic)  |
+---------------------------------------------------------------------+
```

### Agent Workflow

| Agent | Purpose | Tools | Exit Conditions |
|-------|---------|-------|-----------------|
| **Introduction** | Confirm debtor identity | 4 | Person confirmed -> Verification |
| **Verification** | POPI 2+ field check | 4 | Verified -> Negotiation |
| **Negotiation** | Explain debt, negotiate | 9 | Accepted -> Payment |
| **Payment** | Capture payment details | 9 | Confirmed -> Closing |
| **Closing** | Referrals, wrap-up | 5 | Call ends |

---

## Folder Structure

```
debt_collection/
|
+-- agent.yaml              # Main configuration (LLM, TTS, versions, handoffs)
+-- agents.py               # LiveKit entrypoint, session creation
+-- shared_state.py         # UserData container (aggregates profile + call state)
|
+-- state/                  # Modular state management
|   +-- __init__.py         # Exports DebtorProfile, CallState
|   +-- profile.py          # DebtorProfile (immutable debtor data)
|   +-- session.py          # CallState (mutable call progression)
|   +-- types.py            # Enums: CallOutcome, PaymentType, etc.
|
+-- sub_agents/             # Agent implementations
|   +-- __init__.py         # Agent registry and constants
|   +-- base_agent.py       # BaseAgent with context preservation
|   +-- factory.py          # create_agents() - builds all agents
|   +-- agent01_introduction.py
|   +-- agent02_verification.py
|   +-- agent03_negotiation.py
|   +-- agent04_payment.py
|   +-- agent05_closing.py
|
+-- prompts/                # Versioned prompt templates
|   +-- __init__.py         # load_prompt(), format_prompt()
|   +-- _versions.yaml      # Version registry with metrics
|   +-- prompt01_introduction.yaml      # v1 (baseline)
|   +-- prompt01_introduction_v2.yaml   # v2 (empathetic)
|   +-- prompt02_verification.yaml
|   +-- prompt02_verification_v2.yaml
|   +-- ...
|
+-- tools/                  # Tool registry
|   +-- __init__.py         # TOOL_REGISTRY, get_tools_by_names()
|   +-- common_tools.py     # Shared tools (schedule_callback, escalate)
|   +-- tool01_introduction.py
|   +-- tool02_verification.py
|   +-- tool03_negotiation.py
|   +-- tool04_payment.py
|   +-- tool05_closing.py
|
+-- business_rules/         # Domain logic
|   +-- __init__.py         # build_negotiation_context(), etc.
|   +-- config.py           # SCRIPT_TYPES, AUTHORITIES, FEES
|   +-- discount_calculator.py
|   +-- script_context.py
|
+-- utils/                  # Helpers
|   +-- id_generator.py     # generate_session_id(), generate_agent_id()
|   +-- fuzzy_match.py      # Voice input normalization
|   +-- date_parser.py      # Natural language dates
|   +-- spoken_digits.py    # Number handling
|
+-- finetuning/             # Sample logging for training data
|   +-- logger.py           # ConversationSample, log_sample()
|   +-- samples/            # Daily JSONL files
|
+-- eval/                   # Testing framework
|   +-- run_tests.py        # CLI test runner
|   +-- run_eval.py         # Promptfoo evaluation
|   +-- promptfooconfig.yaml
|   +-- testcases/          # YAML test definitions
```

---

## Key Features

### 1. Prompt Versioning

Prompts support versioning for A/B testing without code changes:

```yaml
# prompts/_versions.yaml
versions:
  v1:
    description: "Baseline professional prompts"
    status: active
  v2:
    description: "Empathetic approach"
    status: testing

defaults:
  prompt01_introduction: v1
  prompt03_negotiation: v1
```

Usage:
```python
from prompts import load_prompt, format_prompt

# Load default version
template = load_prompt("prompt01_introduction")

# Load specific version
template = load_prompt("prompt01_introduction", version="v2")

# Format with variables
formatted = format_prompt(template, agent_name="Alex", debtor_name="John")
```

### 2. Modular State Management

State is split into immutable and mutable components:

```python
from state import DebtorProfile, CallState
from shared_state import UserData

# Immutable debtor data
debtor = DebtorProfile(
    full_name="John Smith",
    user_id="12345",
    outstanding_amount=5000.00
)

# Mutable call state
call = CallState(script_type="ratio1_inflow")
call.identity_verified = True
call.add_note("Customer confirmed identity")

# Combined container
userdata = UserData(debtor=debtor, call=call)
```

### 3. Unique Session IDs

Every session gets a unique identifier for tracking:

```python
from utils.id_generator import generate_session_id

session_id = generate_session_id()  # "session-abc123def456"
```

### 4. Fine-tuning Sample Collection

Optionally log conversation samples for model fine-tuning:

```bash
# Enable logging
export ENABLE_FINETUNING_LOG=true

# Samples written to: finetuning/samples/YYYY-MM-DD.jsonl
```

### 5. A/B Testing via agent.yaml

Test different prompt versions without code changes:

```yaml
# agent.yaml
versions:
  v1_baseline:
    description: "Baseline - all agents use default prompts"

  v2_empathetic:
    description: "Empathetic approach"
    sub_agents:
      introduction:
        prompt_version: v2
      negotiation:
        prompt_version: v2

  v3_mixed:
    description: "Mixed - empathetic negotiation only"
    sub_agents:
      negotiation:
        prompt_version: v2
```

Run with specific version:
```bash
cd eval
python run_eval.py --version v2_empathetic
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- LiveKit server running (port 18003)
- API keys: OpenAI, Deepgram, Cartesia (or Chatterbox TTS)

### Setup

```bash
# 1. Activate virtual environment
cd /path/to/livekit-backend
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 4. Run agent
cd agents/debt_collection
python agents.py dev

# 5. Test interactively
cd eval
python run_tests.py --interactive
```

---

## Configuration (agent.yaml)

### Core Settings

```yaml
id: debt-collection-agent-7b3f2a
name: Cartrack Debt Collection Agent

llm:
  provider: openai
  model: gpt-4o-mini
  temperature: 0.2

prompt_version: null  # null = use base prompts

stt:
  provider: deepgram
  model: nova-2

tts:
  provider: chatterbox_tts  # or cartesia
  chatterbox_tts:
    api_url: http://localhost:19810
    audio_prompt_path: voice/debt_voice.mp3
```

### Sub-Agent Configuration

```yaml
sub_agents:
  - id: introduction
    name: Introduction Agent
    description: Confirms speaking with correct person
    tools:
      - confirm_person
      - handle_wrong_person
      - handle_third_party
      - schedule_callback
    instructions: prompts/prompt01_introduction.yaml
    prompt_version: null  # Override per-agent
```

### Handoff Rules

```yaml
handoffs:
  - source: introduction
    target: verification
    condition: Person confirmed identity
    context: Pass customer name and confirmation status

  - source: verification
    target: negotiation
    condition: Identity verified (2+ fields confirmed)
    context: Pass verification status
```

---

## Testing

### Run Tests

```bash
cd eval

# List all tests
python run_tests.py --list

# Run all tests
python run_tests.py

# Run specific phase
python run_tests.py --file agent01_introduction.yaml

# Interactive mode
python run_tests.py --interactive
```

### Version-Specific Testing

```bash
# Test baseline
python run_eval.py --version v1_baseline

# Test empathetic version
python run_eval.py --version v2_empathetic

# View results
python run_eval.py --view
```

### Promptfoo Evaluation

```bash
# Run eval with Promptfoo
npx promptfoo eval -c promptfooconfig.yaml

# View results in browser
npx promptfoo view
```

---

## State Management

### DebtorProfile (Immutable)

Contains validated debtor data:

| Field | Type | Description |
|-------|------|-------------|
| `full_name` | str | Customer name |
| `user_id` | str | Account ID |
| `outstanding_amount` | float | Debt amount |
| `overdue_days` | int | Days overdue |
| `contact_number` | str | Phone number |
| `email` | str | Email address |
| `bank_name` | str | Bank for debit |

### CallState (Mutable)

Tracks call progression:

| Field | Type | Description |
|-------|------|-------------|
| `script_type` | str | Script being used |
| `identity_verified` | bool | POPI verification done |
| `verified_fields` | list | Fields verified |
| `discount_offered` | bool | Discount presented |
| `payment_confirmed` | bool | Payment captured |
| `call_outcome` | enum | Final result |
| `call_notes` | list | Session notes |

### UserData (Container)

Aggregates profile + state:

```python
userdata = UserData(debtor=debtor, call=call)

# Get summary for agent context
context = userdata.summarize()

# Clean up at session end
userdata.cleanup()
```

---

## Tools Reference

| Phase | Tool | Purpose |
|-------|------|---------|
| Introduction | `confirm_person` | Mark debtor confirmed |
| Introduction | `handle_wrong_person` | Wrong number flow |
| Introduction | `handle_third_party` | Third party handling |
| Verification | `verify_field` | Check debtor info |
| Verification | `mark_unavailable` | Customer unavailable |
| Negotiation | `offer_settlement` | Present settlement |
| Negotiation | `offer_installment` | Present installment plan |
| Negotiation | `accept_arrangement` | Record acceptance |
| Payment | `capture_immediate_debit` | Immediate payment |
| Payment | `setup_debicheck` | DebiCheck setup |
| Payment | `send_portal_link` | SMS payment link |
| Closing | `offer_referral` | Referral program |
| Closing | `end_call` | Terminate call |
| Common | `schedule_callback` | Schedule future call |
| Common | `escalate` | Escalate to human |

---

## Business Rules

### Script Types

| Script | Authority | Max Payments | Discount |
|--------|-----------|--------------|----------|
| ratio1_inflow | Cartrack | 2 | None |
| recently_suspended | Cartrack | 3 | 50%/40% |
| pre_legal_120 | Viljoen | 3 | 30-70% |
| legal_stage | Viljoen | 6 | 65-75% |
| booksale_stage | Viljoen | 6 | 70-80% |

### Discount Tiers (Pre-Legal)

| Days Overdue | Balance <= R1.5K | R1.5K-R5K | > R5K |
|--------------|------------------|-----------|-------|
| 150-179 | 30% | 35% | 40% |
| 180-209 | 40% | 45% | 50% |
| 210+ | 60% | 65% | 70% |

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Agent not connecting | LiveKit server down | Check `curl -I http://localhost:18003` |
| Tool not executing | Not in TOOL_REGISTRY | Verify tool in `tools/__init__.py` |
| Prompt not loading | Wrong version | Check `prompts/_versions.yaml` |
| State not updating | Using DebtorProfile | Use `userdata.call.*` for mutable state |

### Debug Mode

```bash
export DEBUG=1
export LOGLEVEL=DEBUG
python agents.py dev
```

### Health Check

```bash
# LiveKit server
curl -I http://localhost:18003

# Tool registry
python -c "from tools import TOOL_REGISTRY; print(len(TOOL_REGISTRY))"

# Prompt loading
python -c "from prompts import load_prompt; print(load_prompt('prompt01_introduction')[:100])"
```

---

## Related Documentation

- [TEMPLATE_GUIDE.md](./TEMPLATE_GUIDE.md) - Create new agents from this template
- [Sub-Agents](./sub_agents/README.md) - Agent implementation details
- [Tools](./tools/README.md) - Tool API reference
- [Business Rules](./business_rules/README.md) - Discount logic
- [Evaluation](./eval/README.md) - Testing workflows
