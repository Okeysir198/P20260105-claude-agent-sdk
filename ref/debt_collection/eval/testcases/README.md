# Test Cases

YAML test suite for debt collection voice agent. Covers all 5 sub-agents with unit, integration, and E2E tests.

## Quick Start

```bash
cd /home/ct-admin/Documents/Langgraph/P20251120-livekit-agent/livekit-agent/debt_collection/eval

# List all tests
python run_tests.py --list

# Run all tests
python run_tests.py

# Run specific file
python run_tests.py --file agent01_introduction.yaml

# Run single test
python run_tests.py --test "INT-001: Person confirms identity"

# Filter by tags
python run_tests.py --tags unit,introduction

# Interactive mode
python run_tests.py --interactive
```

See `eval/README.md` for complete commands.

## Test Files

| File | Tests | Description |
|------|-------|-------------|
| `agent00_e2e_flow.yaml` | ~30 | End-to-end conversation flows |
| `agent01_introduction.yaml` | 6 | Person confirmation, wrong number, third party |
| `agent02_verification.yaml` | 7 | POPI field verification (ID, DOB, username) |
| `agent03_negotiation.yaml` | 14 | Settlement, installment, cancellation |
| `agent04_payment.yaml` | 12 | DebiCheck, portal, bank validation |
| `agent05_closing.yaml` | ~25 | Referrals, contact updates, wrap-up |
| `agent06_script_types.yaml` | ~40 | All 10 script type variations |

**Total:** ~134 test cases

## Test Format

### Basic Structure

```yaml
agent_id: debt_collection
sub_agent_id: introduction
description: "Tests for introduction agent"

# Default data (can be overridden per test)
default_test_data:
  full_name: "John Smith"
  user_id: "U12345"
  id_number: "8501015800087"
  outstanding_amount: 2500.00
  script_type: "ratio1_inflow"

test_cases:
  - name: "INT-001: Person confirms identity"
    test_type: single_turn
    tags: [unit, introduction, happy-path]
    turns:
      - user_input: "Yes, speaking"
        assertions:
          - type: contains_function_call
            value: "confirm_person"
```

### Test Types

**Single Turn:**
```yaml
test_type: single_turn
turns:
  - user_input: "Yes, that's me"
    assertions:
      - type: contains_function_call
        value: "confirm_person"
```

**Multi-Turn:**
```yaml
test_type: multi_turn
turns:
  - user_input: "Yes, speaking"
    assertions:
      - type: contains_function_call
        value: "confirm_person"
  - user_input: "My ID is 8501015800087"
    assertions:
      - type: contains_function_call
        value: "verify_field"
```

### Overriding Test Data

```yaml
# Override specific fields
test_cases:
  - name: "Short paid scenario"
    test_data:
      script_type: "short_paid"
      partial_payment_received: 1000.00
      outstanding_amount: 500.00
    turns:
      - user_input: "I already paid R1000"
```

## Assertion Types

| Type | Purpose | Example |
|------|---------|---------|
| `contains_function_call` | Verify tool invocation | `value: "confirm_person"` |
| `llm-rubric` | LLM evaluates content | `value: "Agent should mention R10 fee"` |
| `contains-any` | Keyword presence | `value: ["payment", "arrange"]` |
| `not-contains` | Forbidden terms | `value: ["debt", "amount"]` |
| `equals` | Exact match (rare) | `value: "expected text"` |

### 1. contains_function_call

**Verify tool was invoked:**

```yaml
assertions:
  - type: contains_function_call
    value: "confirm_person"
```

**With arguments:**
```yaml
assertions:
  - type: contains_function_call
    value: "verify_field"
    arguments:
      field_name: "id_number"
```

**Common Tools:**

| Agent | Tools |
|-------|-------|
| Introduction | `confirm_person`, `handle_wrong_person`, `handle_third_party` |
| Verification | `verify_field`, `mark_unavailable` |
| Negotiation | `accept_arrangement`, `offer_settlement`, `offer_installment` |
| Payment | `capture_immediate_debit`, `setup_debicheck`, `send_portal_link` |
| Closing | `offer_referral`, `update_contact_details`, `end_call` |

### 2. llm-rubric

**LLM evaluates response quality:**

```yaml
assertions:
  - type: llm-rubric
    value: "Agent should acknowledge R3,000 payment and thank customer"
```

**Specific criteria:**
```yaml
- type: llm-rubric
  value: "Agent should offer 50% discount (R1500) for settlement and mention 25th deadline"
```

**Use Cases:**
- Content verification: "Agent mentions R10 DebiCheck fee"
- Tone checking: "Professional and empathetic, not threatening"
- Completeness: "Explains all three payment options"
- Compliance: "Does not discuss debt with third party"

### 3. contains-any

**Response includes at least one keyword:**

```yaml
assertions:
  - type: contains-any
    value: ["payment", "arrange", "settlement"]
```

### 4. not-contains

**Response must NOT include forbidden terms:**

```yaml
# Third-party compliance
assertions:
  - type: not-contains
    value: ["debt", "amount", "payment", "arrears", "overdue"]
```

### 5. equals

**Exact text match (rarely used):**

```yaml
assertions:
  - type: equals
    value: "Thank you for confirming your identity."
```

**Note:** Prefer `llm-rubric` for semantic matching.

## Writing Tests (5 Steps)

### Step 1: Identify Scope

**Choose granularity:**
- **Unit:** Single agent, single behavior
- **Integration:** Multi-agent or multi-step
- **E2E:** Complete conversation

**Target agent:**
- Introduction, Verification, Negotiation, Payment, Closing

### Step 2: Define Test Data

```yaml
test_data:
  # Identity
  full_name: "John Smith"
  id_number: "8501015800087"
  birth_date: "1985-01-15"

  # Financial
  outstanding_amount: 2500.00
  overdue_days: 45
  monthly_subscription: 399.00

  # Account
  script_type: "ratio1_inflow"
  account_status: "active"
```

### Step 3: Write Test Structure

```yaml
- name: "TEST-ID: Descriptive name"
  test_type: single_turn  # or multi_turn
  tags: [granularity, agent, scenario]
  test_data:  # Optional overrides
    field: value
  turns:
    - user_input: "Customer says this"
      assertions:
        - type: contains_function_call
          value: "tool_name"
```

### Step 4: Choose Assertions

**Decision tree:**
1. Testing tool invocation? → `contains_function_call`
2. Testing content/tone? → `llm-rubric`
3. Testing keyword presence? → `contains-any`
4. Testing forbidden content? → `not-contains`
5. Testing exact match? → `equals` (rare)

**Combine multiple:**
```yaml
assertions:
  - type: contains_function_call
    value: "verify_field"
    arguments:
      field_name: "id_number"
  - type: llm-rubric
    value: "Agent should request full 13-digit ID"
  - type: not-contains
    value: "sorry"
```

### Step 5: Test the Test

```bash
# Run single test
python run_tests.py --test "TEST-ID: Description"

# Check output
# - Agent responses make sense?
# - Tool calls match expectations?
# - Assertions pass/fail correctly?
```

## Complete Example

```yaml
- name: "NEG-015: Recently suspended - Tier 1 settlement"
  test_type: multi_turn
  tags: [unit, negotiation, settlement, tier1, recently_suspended]
  test_data:
    script_type: "recently_suspended_120"
    outstanding_amount: 3000.00
    overdue_days: 125
  turns:
    # Customer asks about discount
    - user_input: "What discount can you offer?"
      assertions:
        - type: contains_function_call
          value: "offer_settlement"
        - type: llm-rubric
          value: "Agent should offer 50% discount (R1500) for once-off settlement"
        - type: llm-rubric
          value: "Agent should mention deadline is 25th of this month"

    # Customer accepts
    - user_input: "Yes, I'll pay R1500 today"
      assertions:
        - type: contains_function_call
          value: "accept_arrangement"
          arguments:
            arrangement_type: "settlement"
            amount: 1500.00
        - type: llm-rubric
          value: "Agent should confirm settlement and transfer to payment agent"
```

## Top 5 Troubleshooting Issues

### 1. Test Fails: "Agent not found"

**Cause:** `start_agent` missing or incorrect

**Solution:**
```yaml
- name: "Test name"
  start_agent: introduction  # Add this
  turns:
    - user_input: "..."
```

**Valid agents:** `introduction`, `verification`, `negotiation`, `payment`, `closing`

### 2. Function Call Assertion Fails

**Cause:** Tool not invoked or name misspelled

**Debug:**
```bash
# Check actual tool calls
python run_tests.py --test "Your test" --verbose
# Look for "TOOL: actual_function_name()"
```

**Common mistakes:**
- `confirm_person` (correct) vs. `confirm_identity` (wrong)
- `verify_field` (correct) vs. `verify_identity_field` (wrong)

### 3. LLM Rubric Inconsistent

**Cause:** Rubric too vague, LLM interpretation varies

**Solution - Make specific:**

**Bad:**
```yaml
- type: llm-rubric
  value: "Agent should be helpful"
```

**Good:**
```yaml
- type: llm-rubric
  value: "Agent should mention R10 DebiCheck fee, explain SMS authentication, and request bank details"
```

**Include quantifiable details:**
```yaml
- type: llm-rubric
  value: "Agent offers 50% discount, calculates R1500 from R3000 balance"
```

### 4. Test Data Not Applied

**Cause:** Typo in field name or YAML indentation

**Solution:**
```yaml
# Correct
- name: "Test"
  test_data:  # Indented under test case
    script_type: "short_paid"
    outstanding_amount: 500.00

# Wrong (indentation)
- name: "Test"
test_data:  # Not indented
  script_type: "short_paid"
```

**Check field names match:**
```yaml
# Wrong
test_data:
  balance: 5000.00  # Field doesn't exist

# Correct
test_data:
  outstanding_amount: 5000.00  # Matches DebtorProfile
```

### 5. Assertion Type Not Recognized

**Cause:** Typo in assertion type

**Valid types:**
- `contains_function_call` (underscore)
- `llm-rubric` (hyphen)
- `contains-any` (hyphen)
- `not-contains` (hyphen)
- `equals` (no separators)

**Wrong:**
```yaml
- type: llm_rubric  # Underscore instead of hyphen
```

**Correct:**
```yaml
- type: llm-rubric  # Hyphen
```

## Tags System

### Common Tags

| Category | Tags |
|----------|------|
| **Granularity** | `unit`, `integration`, `e2e` |
| **Agent** | `introduction`, `verification`, `negotiation`, `payment`, `closing` |
| **Scenario** | `happy-path`, `edge-case`, `wrong-person`, `third-party`, `callback` |
| **Script** | `ratio1_inflow`, `prelegal_120`, `recently_suspended`, `short_paid` |

### Filtering

```bash
# All unit tests
python run_tests.py --tags unit

# Negotiation agent only
python run_tests.py --tags negotiation

# E2E happy paths
python run_tests.py --tags e2e,happy-path

# Payment-related
python run_tests.py --tags payment,settlement,debicheck
```

## Test Data Fields

### Identity
```yaml
full_name: "John Smith"
user_id: "U12345"
username: "jsmith001"
id_number: "8501015800087"
birth_date: "1985-01-15"
```

### Contact
```yaml
email: "john.smith@example.com"
contact_number: "0821234567"
residential_address: "123 Main St, Johannesburg"
```

### Financial
```yaml
outstanding_amount: 2500.00
overdue_days: 45
monthly_subscription: 399.00
```

### Account
```yaml
account_status: "active"  # or "cancelled"
script_type: "ratio1_inflow"
```

### Banking
```yaml
bank_name: "FNB"
bank_account_number: "62012345678"
branch_code: "250655"
```

### Script-Specific
```yaml
partial_payment_received: 1000.00  # For short_paid
agreed_amount: 1500.00
has_reversal_history: true
```

## Script Types Reference

| Script Type | Discount | Use Case |
|-------------|----------|----------|
| `ratio1_inflow` | No | New overdue (30-60 days) |
| `ratio1_short_paid` | 30% | Partial payment received |
| `ratio2_inflow` | No | Escalated (60-90 days) |
| `pre_legal` | 40% | Pre-legal stage |
| `recently_suspended_120` | 50% Tier 1 | Recently suspended campaign |
| `legal` | 30% | Legal proceedings |

## Best Practices

1. **Descriptive names:** Include test ID, scenario, expected behavior
2. **Appropriate tags:** Granularity, agent, scenario
3. **Right assertions:** Objective (`contains_function_call`) vs. subjective (`llm-rubric`)
4. **Minimal overrides:** Only override necessary fields
5. **One thing per test:** Focus on single behavior (unit tests)
6. **Test edge cases:** Not just happy paths
7. **Validate compliance:** Use `not-contains` for POPI tests
8. **Specific rubrics:** Include quantifiable details

## Related Documentation

- **Evaluation:** `eval/README.md` - CLI commands, PromptFoo integration
- **Architecture:** `CLAUDE.md` - Agent system, business rules
- **Business Rules:** `business_rules/config.py` - Script types, discounts
- **Tools:** `tools/` - Function reference

---

**Last Updated:** 2025-12-05
**Test Coverage:** ~134 scenarios, 27/27 tools (100%)
