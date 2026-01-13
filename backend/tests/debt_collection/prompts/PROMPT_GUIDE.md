# LiveKit Voice Agent Prompt Guide

This guide documents best practices for writing prompts for LiveKit voice agents, based on the official [LiveKit Prompting Guide](https://docs.livekit.io/agents/build/prompting/).

---

## Overview

Effective instructions are a key part of any voice agent. Voice agents have unique considerations beyond traditional LLM prompting:

1. **Pipeline awareness**: When using STT-LLM-TTS pipeline, the LLM has no built-in understanding of its position in a voice pipeline
2. **Brevity requirement**: All voice agents must be instructed to be concise - users are not patient with long monologues
3. **Workflow approach**: Most use-cases require breaking the agent into smaller components using handoffs to achieve consistent behavior

---

## Prompt Structure (Recommended Sections)

LiveKit recommends using **Markdown format** as it's easy for both humans and machines to read.

### 1. Identity

Start with a clear description of the agent's identity.

```markdown
# Identity
You are [NAME], a [ROLE] for [COMPANY/PURPOSE].
Your primary responsibilities include [RESPONSIBILITIES].
```

**Example (Travel Agent):**
```markdown
# Identity
You are Aria, a friendly and knowledgeable travel assistant for Wanderlust Adventures.
Your primary responsibilities include helping customers plan trips, book flights and
accommodations, and providing travel recommendations.
```

---

### 2. Style

Define the conversational style and tone.

```markdown
# Style
- [Tone characteristics]
- [Communication style]
- [Interaction approach]
```

**Example:**
```markdown
# Style
- Be warm, professional, and conversational
- Use natural speech patterns with occasional filler words like "um" or "let me think"
- Match the user's energy level while maintaining professionalism
- Avoid jargon unless the user demonstrates familiarity
```

---

### 3. Output Formatting

Instruct formatting optimized for text-to-speech systems.

```markdown
# Output Formatting
- [Response length guidelines]
- [Number/date formatting rules]
- [Special entity handling]
```

**Example:**
```markdown
# Output Formatting
- Keep responses under 3 sentences unless providing detailed information
- Spell out numbers naturally: "twenty-three" not "23"
- Format phone numbers with pauses: "five five five, pause, one two three, pause, four five six seven"
- Spell email addresses: "john at example dot com"
- Use verbal punctuation when needed: "The options are, first, economy class, second, business class"
```

> **Note**: This section may be unnecessary if using a realtime native speech model.

---

### 4. Goals

Define the overall goal and workflow-specific objectives.

```markdown
# Goal
[Overall objective]

# Current Task
[Specific immediate goal for this agent/stage]
```

**Example (Travel Agent):**
```markdown
# Goal
Help customers plan and book their perfect trip by understanding their preferences,
providing personalized recommendations, and handling all booking logistics.

# Current Task
Gather the customer's travel preferences including destination, dates, budget,
and any special requirements.
```

---

### 5. Tools

Provide overview of tool usage patterns.

```markdown
# Tools
- [General tool interaction guidance]
- [When to use tools vs respond directly]
```

**Example:**
```markdown
# Tools
- Use function tools to perform actions and retrieve information
- Always confirm with the user before executing actions that make changes
- If a tool returns an error, explain the issue to the user and suggest alternatives
- Wait for tool results before continuing the conversation when information is needed
```

---

### 6. Guardrails

Define boundaries and limitations.

```markdown
# Guardrails
- [Scope limitations]
- [Prohibited topics/actions]
- [Fallback behavior]
```

**Example:**
```markdown
# Guardrails
- Only assist with travel-related inquiries
- Do not provide legal, medical, or financial advice
- If asked about topics outside your scope, politely redirect to travel assistance
- Never share personal opinions on political or religious matters
- If uncertain about information, acknowledge limitations rather than guessing
```

---

### 7. User Information

Include personalization data when available.

```markdown
# User Information
- Name: {{ user_name }}
- [Additional context]
```

**Example:**
```markdown
# User Information
- Name: {{ user_name }}
- Membership tier: {{ membership_tier }}
- Previous destinations: {{ past_trips }}
- Preferences: {{ travel_preferences }}
```

> **Tip**: Load user data via Job metadata during dispatch for personalization.

---

## Complete Example Template

```yaml
version: "1.0"
agent_id: example_agent
metadata:
  tags: [example, template]

prompt: |
  # Identity
  You are {{ agent_name }}, a [ROLE] for {{ company_name }}.
  Your primary responsibility is [MAIN_RESPONSIBILITY].

  # Style
  - Be [TONE_ADJECTIVES]
  - Use natural conversational speech patterns
  - Keep responses concise and focused
  - Match the user's communication style

  # Output Formatting
  - Keep responses under [X] words/sentences
  - Spell out numbers naturally
  - No emojis, markdown, or special formatting
  - Use verbal cues for lists: "first..., second..., third..."

  # Goal
  [OVERALL_OBJECTIVE]

  # Current Task
  [SPECIFIC_IMMEDIATE_OBJECTIVE]

  # Response Handling
  - If [CONDITION_1] → [ACTION_1]
  - If [CONDITION_2] → [ACTION_2]
  - If unclear → [CLARIFICATION_APPROACH]

  # Tools
  - Use [TOOL_1] to [PURPOSE_1]
  - Use [TOOL_2] to [PURPOSE_2]
  - Always confirm before [SIGNIFICANT_ACTIONS]

  # Guardrails
  - NEVER [PROHIBITED_ACTION_1]
  - NEVER [PROHIBITED_ACTION_2]
  - Stay focused only on [SCOPE]
  - If asked about [OUT_OF_SCOPE] → [REDIRECT_RESPONSE]

  # User Information
  - Name: {{ user_name }}
  - [Additional personalization fields]
```

---

## Standard Template for Fine-Tuning

When creating prompts for fine-tuning, follow this exact structure to ensure consistency:

```yaml
# ============================================
# PROMPT METADATA
# ============================================
version: "1.0"           # Prompt schema version
agent_id: agent_name     # Unique agent identifier
metadata:
  tags: [tag1, tag2]     # Searchable tags
  description: ""        # Brief description
  author: ""             # Creator name
  created: ""            # ISO date
  modified: ""           # ISO date

# ============================================
# PROMPT CONTENT
# ============================================
prompt: |
  # Identity
  You are {{ agent_name }}, a [ROLE] for {{ authority }}.

  # Style
  - [2-4 style directives]

  # Output Formatting
  - Keep responses under [N] words
  - [Specific formatting rules for domain]

  # Goal
  [Single clear objective statement]

  # Response Handling
  - If [condition] → [tool_call or response]
  - If [condition] → [tool_call or response]

  # Tools
  [Brief tool usage guidance if tools are assigned]

  # Guardrails
  - NEVER [prohibited action]
  - [Additional safety constraints]
```

### Fine-Tuning Requirements

1. **Consistent Structure**: Always include all sections in the same order
2. **Mustache Variables**: Use `{{ variable_name }}` for dynamic content
3. **Tool Integration**: Match tool names exactly as defined in `tools/__init__.py`
4. **Response Patterns**: Use clear condition → action mappings
5. **Measurable Constraints**: Use specific numbers (e.g., "under 25 words")

---

## Project-Specific Conventions

### Variable Naming
```yaml
# Standard variables (defined in agent.yaml and business_rules/config.py)
{{ agent_name }}        # Agent's display name
{{ authority }}         # Company/organization name
{{ authority_contact }} # Contact phone number
{{ debtor_name }}       # Customer name (for debt collection)
{{ account_number }}    # Reference number
```

### Version Naming
```
prompt01_introduction.yaml      # Base version (v1)
prompt01_introduction_v2.yaml   # Version 2 (empathetic)
prompt01_introduction_v3.yaml   # Version 3 (custom)
```

### Agent ID Format
```
introduction    # Matches sub_agent.id in agent.yaml
verification    # No prefix needed
negotiation     # Keep lowercase, snake_case
```

---

## Testing and Validation

### Unit Tests
Use LiveKit's built-in testing with pytest:

```python
from livekit.agents.testing import AgentTestRunner

async def test_greeting_behavior():
    runner = AgentTestRunner(MyAgent)
    result = await runner.run_conversation([
        "Hello",
    ])
    assert "welcome" in result.transcript.lower()
```

### Real-World Observability
- Monitor transcripts in production
- Use sessions as inspiration for new test cases
- Iterate prompts based on observed failures

### A/B Testing
Use `_versions.yaml` to track metrics:

```yaml
versions:
  v1:
    description: "Baseline - professional tone"
    metrics:
      call_completion_rate: 0.72
  v2:
    description: "Empathetic - softer approach"
    metrics:
      call_completion_rate: 0.78
```

---

## Common Pitfalls

| Issue | Solution |
|-------|----------|
| Long responses | Add explicit word limits: "under 25 words" |
| Ignoring tools | Add "You MUST call [tool] when [condition]" |
| Off-topic responses | Add strong guardrails: "NEVER discuss [topic]" |
| Robotic speech | Add style: "Use natural speech patterns" |
| Missing context | Use `{{ variables }}` for personalization |

---

## Resources

- [LiveKit Prompting Guide](https://docs.livekit.io/agents/build/prompting/)
- [LiveKit Workflows Guide](https://docs.livekit.io/agents/build/workflows/)
- [LiveKit Agent Testing](https://docs.livekit.io/agents/build/testing/)
- [Project README](../README.md)
- [Template Guide](../TEMPLATE_GUIDE.md)
