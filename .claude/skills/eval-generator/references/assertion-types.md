# Assertion Types Reference

The eval framework supports 8 assertion types for validating agent responses.

## 1. contains

Check if the response contains a specific substring (case-insensitive).

**Use for**: Verifying specific words or phrases appear in the response.

```yaml
assertions:
  - type: contains
    value: "reservation confirmed"
```

**Behavior**:
- Case-insensitive matching
- Partial match (substring)
- PASS: "Your reservation confirmed for Saturday" contains "reservation confirmed"
- FAIL: "Your booking is set" does not contain "reservation confirmed"

---

## 2. not_contains

Ensure the response does NOT contain forbidden content.

**Use for**: Preventing sensitive data exposure, inappropriate responses, or premature actions.

```yaml
assertions:
  - type: not_contains
    value: "goodbye"
```

**Examples**:
```yaml
# Prevent early conversation termination
- type: not_contains
  value: "goodbye"

# Ensure no error messages leak
- type: not_contains
  value: "internal error"

# Prevent disclosure of sensitive info
- type: not_contains
  value: "password"
```

---

## 3. contains_any

Check if response contains at least ONE of the specified values.

**Use for**: Flexible keyword matching where multiple terms are acceptable.

```yaml
assertions:
  - type: contains_any
    value: ["available", "open", "free"]
```

**Behavior**:
- PASS if ANY value matches (OR logic)
- Case-insensitive
- PASS: "We have tables available" (matches "available")
- PASS: "That slot is open" (matches "open")
- FAIL: "Please hold" (matches none)

---

## 4. contains_all

Check if response contains ALL of the specified values.

**Use for**: Ensuring multiple required elements are present.

```yaml
assertions:
  - type: contains_all
    value: ["date", "time", "party size"]
```

**Behavior**:
- PASS only if ALL values match (AND logic)
- Case-insensitive
- PASS: "Please confirm the date, time, and party size"
- FAIL: "Please confirm the date and time" (missing "party size")

---

## 5. equals

Check for exact string match (after trimming whitespace).

**Use for**: Exact response verification (rare, use sparingly).

```yaml
assertions:
  - type: equals
    value: "Thank you for calling. Goodbye!"
```

**Behavior**:
- Exact match after whitespace trimming
- Case-sensitive
- Rarely recommended (agent responses vary)

---

## 6. matches

Check if response matches a regular expression pattern.

**Use for**: Pattern matching, format validation, flexible text matching.

```yaml
assertions:
  - type: matches
    value: "confirmation.*#[A-Z0-9]{6}"
```

**Examples**:
```yaml
# Match confirmation number format
- type: matches
  value: "confirmation.*#[A-Z0-9]{6}"

# Match time format
- type: matches
  value: "\\d{1,2}:\\d{2}\\s*(AM|PM)"

# Match phone number format
- type: matches
  value: "\\d{3}-\\d{3}-\\d{4}"

# Match date format
- type: matches
  value: "\\d{4}-\\d{2}-\\d{2}"
```

**Note**: Use double backslashes in YAML for regex escapes.

---

## 7. contains_function_call

Verify that a specific tool/function was invoked during the turn.

**Use for**: Ensuring the agent calls the correct tool for a given request.

```yaml
assertions:
  - type: contains_function_call
    value: "create_reservation"
```

**With argument verification** (optional):
```yaml
assertions:
  - type: contains_function_call
    value: "create_reservation"
    arguments:
      party_size: 4
      date: "2024-02-15"
```

**Examples by domain**:

```yaml
# Restaurant agent
- type: contains_function_call
  value: "check_availability"

- type: contains_function_call
  value: "create_reservation"
  arguments:
    party_size: 4

# Support agent
- type: contains_function_call
  value: "lookup_account"

- type: contains_function_call
  value: "create_ticket"
  arguments:
    priority: "high"

# Healthcare agent
- type: contains_function_call
  value: "schedule_appointment"
  arguments:
    appointment_type: "checkup"
```

**Behavior**:
- Checks tool call history for the turn
- Optional `arguments` field for partial argument matching
- PASS: Tool was called (with matching arguments if specified)
- FAIL: Tool was not called or arguments don't match

---

## 8. llm_rubric

Use an LLM to semantically evaluate the response quality.

**Use for**: Complex quality checks that can't be expressed with pattern matching.

```yaml
assertions:
  - type: llm_rubric
    value: "Agent should be empathetic and acknowledge the customer's frustration"
```

**Alternative syntax with rubric field**:
```yaml
assertions:
  - type: llm_rubric
    rubric: "The response should clearly explain the next steps"
```

**With custom model** (optional):
```yaml
assertions:
  - type: llm_rubric
    value: "Agent provides accurate pricing information"
    model: "gpt-4o"  # Override default judge model
```

**Best practices for rubrics**:

```yaml
# Good: Specific and measurable
- type: llm_rubric
  value: "Agent asks for the customer's name before proceeding"

# Good: Behavioral expectation
- type: llm_rubric
  value: "Agent offers at least two alternative time slots"

# Good: Quality criteria
- type: llm_rubric
  value: "Response is professional, concise, and includes a clear call-to-action"

# Avoid: Too vague
- type: llm_rubric
  value: "Agent is helpful"  # What does "helpful" mean?

# Avoid: Multiple criteria (split into separate assertions)
- type: llm_rubric
  value: "Agent is polite, provides accurate info, and closes properly"
```

**Examples by scenario**:

```yaml
# Error handling
- type: llm_rubric
  value: "Agent apologizes for the inconvenience and offers a solution"

# Information gathering
- type: llm_rubric
  value: "Agent asks clarifying questions before making assumptions"

# Handoff verification
- type: llm_rubric
  value: "Agent explains why transferring to a specialist"

# Closing
- type: llm_rubric
  value: "Agent confirms all details before ending the conversation"
```

---

## Assertion Combination Examples

Combine multiple assertions for comprehensive validation:

```yaml
turns:
  - user_input: "I want to book a table for 4 on Saturday"
    assertions:
      # Verify correct tool was called
      - type: contains_function_call
        value: "check_availability"

      # Verify response contains key info
      - type: contains_any
        value: ["available", "slot", "opening"]

      # Verify no premature goodbye
      - type: not_contains
        value: "goodbye"

      # Semantic quality check
      - type: llm_rubric
        value: "Agent should present available options and ask for preference"
```

---

## Summary Table

| Type | Required Field | Optional Fields | Use Case |
|------|---------------|-----------------|----------|
| `contains` | `value: string` | - | Substring present |
| `not_contains` | `value: string` | - | Substring absent |
| `contains_any` | `value: [strings]` | - | Any substring |
| `contains_all` | `value: [strings]` | - | All substrings |
| `equals` | `value: string` | - | Exact match |
| `matches` | `value: regex` | - | Pattern match |
| `contains_function_call` | `value: tool_name` | `arguments` | Tool invocation |
| `llm_rubric` | `value` or `rubric` | `model` | Semantic evaluation |
