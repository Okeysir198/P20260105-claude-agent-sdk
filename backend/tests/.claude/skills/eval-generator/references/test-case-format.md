# Test Case YAML Schema

Complete schema reference for test case YAML files.

## File Structure

```yaml
# =============================================================================
# FILE METADATA
# =============================================================================
agent_id: string          # Required. Agent identifier (e.g., "restaurant_agent")
sub_agent_id: string      # Optional. Sub-agent for multi-agent systems
description: string       # Optional. File description

# =============================================================================
# DEFAULT TEST DATA
# =============================================================================
# Applied to ALL test cases in this file unless overridden per test.
# Structure should match your agent's UserData schema.
default_test_data:
  field_name: value
  nested:
    field: value

# =============================================================================
# TEST CASES ARRAY
# =============================================================================
test_cases:
  - name: string          # Required. Unique test identifier
    test_type: string     # Optional. "single_turn" or "multi_turn"
    tags: [string]        # Optional. For filtering tests
    description: string   # Optional. Human-readable description
    test_data: object     # Optional. Override default_test_data for this test
    start_agent: string   # Optional. Starting agent for multi-agent tests
    max_turns: integer    # Optional. Max turns for simulation tests
    turns: [Turn]         # Required. Array of conversation turns
```

## Turn Structure

```yaml
turns:
  - user_input: string        # Required. User's message
    assertions: [Assertion]   # Optional. Array of assertions
    expected_agent: string    # Optional. Expected agent after this turn
```

## Full Example: Single-Turn Test

```yaml
agent_id: restaurant_agent
sub_agent_id: reservation
description: "Reservation sub-agent unit tests"

default_test_data:
  customer_name: "John Doe"
  phone: "555-0123"
  party_size: 4
  preferred_date: "2024-02-15"
  preferred_time: "19:00"

test_cases:
  - name: "RES-001: Make new reservation"
    test_type: single_turn
    tags: [unit, reservation, happy-path]
    turns:
      - user_input: "I'd like to book a table for 4 people"
        assertions:
          - type: contains_function_call
            value: "create_reservation"
          - type: llm_rubric
            value: "Agent should confirm party size and ask for date/time"
```

## Full Example: Multi-Turn Test

```yaml
agent_id: restaurant_agent
sub_agent_id: null
description: "End-to-end reservation flow"

default_test_data:
  customer_name: "Jane Smith"
  phone: "555-0456"

test_cases:
  - name: "E2E-001: Complete reservation flow"
    test_type: multi_turn
    tags: [e2e, critical, happy-path]
    turns:
      # Turn 1: Initial greeting
      - user_input: "Hello, I want to make a reservation"
        assertions:
          - type: llm_rubric
            value: "Agent should greet and ask for reservation details"

      # Turn 2: Provide party size
      - user_input: "Party of 6 for Saturday evening"
        assertions:
          - type: contains_function_call
            value: "check_availability"
          - type: contains_any
            value: ["available", "time", "slot"]

      # Turn 3: Confirm time
      - user_input: "7pm works great"
        assertions:
          - type: contains_function_call
            value: "create_reservation"
          - type: llm_rubric
            value: "Agent should confirm the reservation details"

      # Turn 4: Provide contact info
      - user_input: "My name is Jane and my number is 555-0456"
        assertions:
          - type: contains
            value: "confirmed"
          - type: not_contains
            value: "error"
```

## Full Example: Test Data Override

```yaml
agent_id: support_agent
description: "Support agent tests with varying account states"

default_test_data:
  customer_id: "C00001"
  account_status: "active"
  support_tier: "standard"

test_cases:
  - name: "SUP-001: Active account inquiry"
    tags: [unit, support, happy-path]
    turns:
      - user_input: "What's my account balance?"
        assertions:
          - type: contains_function_call
            value: "get_account_balance"

  - name: "SUP-002: Suspended account handling"
    tags: [unit, support, edge-case]
    # Override default_test_data for this specific test
    test_data:
      customer_id: "C00002"
      account_status: "suspended"
      suspension_reason: "payment_overdue"
    turns:
      - user_input: "I want to make a purchase"
        assertions:
          - type: llm_rubric
            value: "Agent should explain account is suspended and provide resolution steps"
          - type: not_contains
            value: "purchase"
```

## Test Case Naming Convention

Use a consistent naming format: `{PREFIX}-{NUMBER}: {Description}`

| Prefix | Meaning | Example |
|--------|---------|---------|
| RES | Reservation agent | RES-001: New reservation |
| SUP | Support agent | SUP-003: Escalation flow |
| ORD | Order agent | ORD-005: Cancel order |
| INT | Introduction agent | INT-001: Identity verification |
| E2E | End-to-end test | E2E-010: Full workflow |

## Tags Reference

### Test Granularity
- `unit` - Single turn, isolated tests
- `integration` - Multi-turn within one agent
- `e2e` - End-to-end across multiple agents

### Priority
- `critical` - Must pass, blocks deployment
- `happy-path` - Expected success scenario
- `edge-case` - Boundary conditions
- `regression` - Prevents known bugs

### Agent-Specific
- Tag with sub-agent ID (e.g., `reservation`, `support`, `billing`)

## Validation Rules

The test case schema enforces:

1. **Required fields**: `agent_id`, `test_cases`, `name`, `turns`, `user_input`
2. **Non-empty arrays**: At least one test case, at least one turn
3. **Valid assertion types**: Only the 8 supported types
4. **Assertion requirements**: Each type requires specific fields (see assertion-types.md)
