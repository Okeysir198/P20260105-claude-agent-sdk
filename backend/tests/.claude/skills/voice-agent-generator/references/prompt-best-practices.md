# Prompt Best Practices for Voice Agents

Reference patterns for TTS-optimized prompts.

## TTS Output Rules

Voice agents speak through TTS. Follow these rules:

### 1. Plain Text Only

No markdown, JSON, code blocks, or special formatting:

```yaml
# WRONG - TTS will speak asterisks and formatting
prompt: |
  **Important:** Your balance is $500.
  - Item 1
  - Item 2
  ```json
  {"status": "ok"}
  ```

# CORRECT - Clean spoken text
prompt: |
  Important. Your balance is five hundred dollars.
  First, Item 1.
  Second, Item 2.
```

### 2. Brief Responses

Keep responses under 25 words, 1-3 sentences:

```yaml
# WRONG - Too verbose
prompt: |
  Please respond with detailed explanations that thoroughly cover
  all aspects of the customer's question, ensuring they have a
  complete understanding of the matter at hand.

# CORRECT - Concise
prompt: |
  Keep responses under 25 words. Be direct and helpful.
```

### 3. Spell Out Numbers

Numbers should be spoken naturally:

```yaml
# WRONG - TTS may mispronounce
prompt: |
  The phone number is 011-250-3000.
  Your balance is $5,000.50.
  The date is 2025-01-15.

# CORRECT - Spoken form
prompt: |
  Spell out numbers naturally:
  - Phone: "oh-one-one, two-five-oh, three-thousand"
  - Money: "five thousand rand and fifty cents"
  - Dates: "January fifteenth, twenty twenty-five"
```

### 4. Avoid Special Characters

No emojis, symbols, or technical notation:

```yaml
# WRONG
prompt: |
  Great! Your appointment is confirmed.
  Email: john@example.com
  Reference #12345

# CORRECT
prompt: |
  Your appointment is confirmed.
  Email: john at example dot com
  Reference number one two three four five
```

## Prompt Structure

### Standard Sections

Organize prompts with clear sections:

```yaml
version: "1.0"
agent_id: introduction
metadata:
  tags: [introduction, greeting]

prompt: |
  # Identity
  You are {{ agent_name }}, a customer service agent from {{ company }}.

  # Output Rules
  - Keep responses under 25 words
  - No emojis, markdown, or special formatting
  - Spell out numbers naturally
  - Sound professional and friendly

  # Goal
  Greet the customer and confirm their identity.

  # Opening Line
  "Good day, this is {{ agent_name }} from {{ company }}. Am I speaking with {{ customer_name }}?"

  # Response Handling
  - If confirmed (yes, speaking) -> call confirm_person()
  - If wrong person (wrong number) -> call handle_wrong_person()
  - If third party (not here) -> call handle_third_party(relationship)

  # Guardrails
  - NEVER discuss account details before verification
  - NEVER reveal call purpose to third parties
```

### Section Definitions

1. **Identity** - Who the agent is and represents
2. **Output Rules** - TTS formatting constraints
3. **Goal** - Primary objective for this agent
4. **Opening Line** - Exact first statement (optional)
5. **Response Handling** - Decision tree for user responses
6. **Guardrails** - What the agent must NOT do

## Mustache Template Variables

Use `{{variable}}` syntax for dynamic content:

```yaml
prompt: |
  You are {{ agent_name }} from {{ authority }}.

  Customer: {{ customer_name }}
  Outstanding: {{ outstanding_amount }}

  Opening: "Hello {{ customer_name }}, this is {{ agent_name }}."
```

### Common Variables

| Variable | Description |
|----------|-------------|
| `agent_name` | Display name of the agent |
| `authority` | Company or department name |
| `authority_contact` | Callback phone number |
| `customer_name` | Full name of customer |
| `outstanding_amount` | Formatted currency |
| `email` | Customer email |
| `phone` | Customer phone |

## Tool Usage Instructions

Guide the LLM on when to call tools:

```yaml
prompt: |
  # Tools Available
  - confirm_person: Call when customer confirms "yes" or "that's me"
  - handle_wrong_person: Call when caller says "wrong number"
  - schedule_callback: Call when customer requests to be called back

  # Tool Decision Flow
  1. Greet and ask if speaking with {{ customer_name }}
  2. Listen for response
  3. Based on response:
     - Confirmation -> confirm_person()
     - Denial -> handle_wrong_person()
     - Request -> schedule_callback(date, time)
```

## Handling Edge Cases

Document specific scenarios:

```yaml
prompt: |
  # Edge Case Handling

  ## Customer Questions Legitimacy
  If customer asks "How do I know this is real?":
  - Provide callback number: {{ authority_contact }}
  - Explain: "You can call us back at this number to verify"
  - Do NOT proceed until customer is comfortable

  ## Background Noise
  If unable to hear clearly:
  - Ask: "I'm having trouble hearing you. Could you repeat that?"
  - After 2 attempts: Offer callback

  ## Customer Angry
  If customer is upset:
  - Remain calm and professional
  - Acknowledge: "I understand this may be frustrating"
  - If escalating: call escalate(reason="aggressive_customer")
```

## Guardrails Section

Explicit restrictions prevent mistakes:

```yaml
prompt: |
  # Guardrails

  ## NEVER Do
  - NEVER discuss account balance before verification
  - NEVER reveal call purpose to third parties
  - NEVER make promises you cannot keep
  - NEVER provide legal or financial advice
  - NEVER argue with the customer

  ## ALWAYS Do
  - ALWAYS verify identity before discussing details
  - ALWAYS offer callback option if customer is busy
  - ALWAYS be respectful regardless of customer tone
  - ALWAYS log the call outcome
```

## Conversation Flow Guidance

Provide clear decision paths:

```yaml
prompt: |
  # Conversation Flow

  START -> Greet customer
    |
    v
  ASK: "Am I speaking with {{ customer_name }}?"
    |
    +-- YES -> confirm_person() -> END
    |
    +-- NO / Wrong number -> handle_wrong_person() -> END
    |
    +-- Third party -> handle_third_party() -> END
    |
    +-- Callback request -> schedule_callback() -> END
    |
    +-- Question about legitimacy -> Provide {{ authority_contact }}
        |
        +-- Continue conversation
```

## YAML File Structure

Complete prompt file example:

```yaml
# prompts/prompt01_introduction.yaml

version: "1.0"
agent_id: introduction
metadata:
  tags: [introduction, identity_confirmation]
  author: "voice-agent-generator"
  created: "2025-01-15"

prompt: |
  # Identity
  You are {{ agent_name }}, a professional agent from {{ authority }}.

  # Output Rules
  - Keep responses under 25 words
  - No emojis, markdown, or special formatting
  - Spell out numbers naturally (e.g., "oh-one-one" not "011")
  - Sound professional, calm, and respectful

  # Goal
  Confirm you are speaking with {{ customer_name }}.

  # Opening Line
  "Good day, this is {{ agent_name }} calling from {{ authority }}. May I speak with {{ customer_name }}?"

  # Response Handling
  - If caller confirms identity (yes, speaking, that's me) -> call confirm_person()
  - If wrong number (wrong number, not me) -> call handle_wrong_person()
  - If third party (not here, I'm their spouse) -> call handle_third_party(relationship)
  - If callback request -> call schedule_callback(date, time)
  - If questions legitimacy -> Provide {{ authority_contact }} and re-ask

  # Guardrails
  - NEVER discuss account details before verification
  - NEVER reveal call purpose to third parties
  - Stay focused only on confirming identity
```

## Prompt Versioning

Support A/B testing with versions:

```yaml
# prompts/_versions.yaml

versions:
  v1:
    description: "Baseline professional tone"
  v2:
    description: "Warmer, more empathetic tone"

defaults:
  prompt01_introduction: v1
  prompt02_verification: v1
  prompt03_main: v1

metrics:
  v1:
    success_rate: 0.72
    avg_duration: 180
  v2:
    success_rate: 0.78
    avg_duration: 165
```

Alternate versions use `_{version}` suffix:
- `prompt01_introduction.yaml` (v1, default)
- `prompt01_introduction_v2.yaml` (v2, empathetic)
