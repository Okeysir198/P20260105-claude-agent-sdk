# Tools

Function tools for debt collection voice agent (26 tools).

## Public API

```python
from tools import TOOL_REGISTRY, get_tools_by_names

# Load tools for an agent
tools = get_tools_by_names(["confirm_person", "schedule_callback"])

# List all available tools
print(list(TOOL_REGISTRY.keys()))
```

## Tool Registry

### Introduction (3)
- `confirm_person` - Confirm speaking with correct person
- `handle_wrong_person` - Handle wrong number
- `handle_third_party` - Handle third party contact

### Verification (2)
- `verify_field` - Verify identity field (auto-transfers after 2+ verified)
- `mark_unavailable` - Mark field as unavailable

### Negotiation (6)
- `offer_settlement` - Present settlement offer
- `offer_installment` - Present installment plan
- `accept_arrangement` - Accept payment arrangement
- `explain_consequences` - Explain non-payment consequences
- `explain_benefits` - Explain payment benefits
- `offer_tier2_fallback` - Offer tier 2 discount

### Payment (7)
- `capture_immediate_debit` - Process immediate debit
- `validate_bank_details` - Validate bank details
- `update_bank_details` - Update bank details
- `setup_debicheck` - Setup DebiCheck mandate
- `send_portal_link` - Send payment portal link
- `confirm_portal_payment` - Confirm portal payment
- `confirm_arrangement` - Confirm arrangement

### Closing (5)
- `offer_referral` - Log referral
- `update_contact_details` - Update contact details
- `update_next_of_kin` - Update next of kin
- `explain_subscription` - Explain subscription
- `end_call` - End call with outcome

### Common (3)
- `schedule_callback` - Schedule callback (Mon-Sat 07:00-18:00)
- `escalate` - Escalate to supervisor
- `handle_cancellation_request` - Process cancellation

## Workflow

```
Introduction → Verification → Negotiation → Payment → Closing
     │              │              │            │
     └──────────────┴──────────────┴────────────┴─► Common tools available
```

## Adding Tools

1. Create function in `tool0X_*.py`:
```python
@function_tool()
async def my_tool(param: Annotated[str, Field(...)], context: RunContext_T) -> str:
    """Tool docstring for LLM."""
    return "Result"
```

2. Register in `tools/__init__.py`:
```python
TOOL_REGISTRY["my_tool"] = my_tool
```

3. Add to agent config in `agent.yaml`
