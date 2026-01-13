# Common Failure Patterns

Guide to identifying and fixing common prompt failures in voice agents.

## 1. Verbosity Issues

### Symptoms
- Responses exceed 3 sentences
- User interrupts frequently
- Test transcripts show long monologues
- "Response too long" failures in evals

### Example Failure
```
User: What time do you close?
Agent: Thank you for your question about our operating hours. We understand that
knowing when we're open is important for planning your visit. Our store is
open Monday through Friday from 9 AM to 6 PM, Saturday from 10 AM to 4 PM,
and we are closed on Sunday for staff rest days. Is there anything else I
can help you with regarding our schedule?
```

### Root Cause
- Missing explicit length constraints
- Over-explaining simple queries
- Adding unnecessary pleasantries

### Fix
Add explicit word/sentence limits in prompt:

```yaml
# Style
- Keep responses under 20 words
- Answer the question directly, then stop
- No preamble or filler phrases
```

**Fixed Response:**
```
We're open nine to six, Monday through Friday. Saturdays ten to four. Closed Sundays.
```

---

## 2. Formatting Issues

### Symptoms
- Markdown symbols in speech output (*, #, -, etc.)
- TTS reads "asterisk" or "hashtag"
- JSON objects spoken literally
- Lists read as "dash item one, dash item two"

### Example Failure
```
User: What are my options?
Agent: Here are your options:
- **Basic**: $50/month
- **Standard**: $100/month
- **Premium**: $200/month
```

### Root Cause
- Prompt doesn't explicitly prohibit formatting
- LLM defaults to markdown for structure
- Copy-pasted content from web sources

### Fix
Add explicit formatting prohibition:

```yaml
# Output Formatting
- Plain conversational speech only
- NEVER use markdown, bullets, asterisks, or special characters
- NEVER output JSON, code, or structured data
- Use verbal transitions: "first... second... third..."
```

**Fixed Response:**
```
You have three options. Basic is fifty dollars a month. Standard is one hundred.
Premium is two hundred. Which interests you?
```

---

## 3. Tool Usage Issues

### Symptoms
- Tools not called when they should be
- Wrong tools called
- Missing required parameters
- Tool called at wrong time in conversation

### Example Failure
```
User: Book me an appointment for Tuesday at 2pm
Agent: Sure, I can help you book that appointment for Tuesday at 2 PM.
(Tool not called - just acknowledged)
```

### Root Cause
- Missing explicit trigger conditions
- Ambiguous tool descriptions
- No required-before-calling instructions

### Fix
Add explicit tool trigger conditions:

```yaml
# Tools
- book_appointment: CALL IMMEDIATELY when user provides date and time
  - Required: date, time
  - Do NOT call if date or time is missing - ask first
  - After calling: confirm the booking details

# Response Handling
- If user says "book", "schedule", or "appointment" with date/time -> call book_appointment()
- If user requests booking without time -> ask "What time works for you?"
```

**Fixed Response:**
```
Agent: (calls book_appointment with date=Tuesday, time=14:00)
Got it, I've booked you for Tuesday at two PM. You'll get a confirmation shortly.
```

---

## 4. Tone Issues

### Symptoms
- Responses sound robotic or scripted
- Too formal for casual interactions
- Lacks empathy in sensitive situations
- User disengagement

### Example Failure
```
User: I'm really frustrated, my order hasn't arrived
Agent: I understand. Please provide your order number so I can look up
the status of your shipment.
```

### Root Cause
- Missing empathy instructions
- Over-prioritizing task completion
- No emotional acknowledgment guidance

### Fix
Add tone and empathy guidance:

```yaml
# Style
- Acknowledge emotions before problem-solving
- Use warm, natural language
- Match the user's energy level
- Say "I'm sorry to hear that" when appropriate

# Response Handling
- If user expresses frustration -> acknowledge first, then help
- If user is upset -> validate feelings before asking for details
```

**Fixed Response:**
```
Oh no, I'm really sorry your order hasn't shown up. That's frustrating.
Let me look into this right away. What's your order number?
```

---

## 5. Missing Information Issues

### Symptoms
- Agent doesn't answer the actual question
- Important details omitted
- User has to repeat or clarify

### Example Failure
```
User: How much does shipping cost to California?
Agent: We offer several shipping options including standard, express, and overnight delivery.
```

### Root Cause
- Prompt lacks specificity guidance
- No instruction to answer directly
- Vague goal definition

### Fix
Add direct-answer instructions:

```yaml
# Goal
Answer the user's specific question with relevant details

# Style
- Answer the question asked, not a related question
- Include specific numbers, dates, or facts when known
- If you don't have the info, say so and offer alternatives

# Response Handling
- If user asks about cost -> provide the actual cost or range
- If cost varies -> state the range and ask clarifying questions
```

**Fixed Response:**
```
Shipping to California is eight ninety-five for standard, or fourteen ninety-five for express.
Which would you prefer?
```

---

## 6. Guardrail Violations

### Symptoms
- Agent discusses off-topic subjects
- Provides advice outside scope
- Makes promises it can't keep
- Shares information it shouldn't

### Example Failure
```
User: Can you recommend a good investment strategy?
Agent: For long-term investing, I'd suggest a diversified portfolio with
60% stocks and 40% bonds...
```

### Root Cause
- Missing or weak guardrails
- No redirect instructions
- Scope not clearly defined

### Fix
Add explicit guardrails with redirects:

```yaml
# Guardrails
- NEVER provide financial, legal, or medical advice
- NEVER make promises about outcomes
- NEVER share other customers' information
- Stay focused ONLY on [your service domain]

# Response Handling
- If asked about investments/legal/medical -> "I'm not qualified to advise on that.
  I'd recommend speaking with a professional. Is there anything about [our service]
  I can help with?"
```

**Fixed Response:**
```
I'm not able to give investment advice. You'd want to talk to a financial advisor
for that. Is there something about your account I can help with?
```

---

## Quick Diagnosis Table

| Failure Type | Key Indicator | Section to Fix |
|--------------|---------------|----------------|
| Verbosity | > 3 sentences | Style/Output Formatting |
| Formatting | Markdown/JSON in output | Output Formatting |
| Tool Issues | Missing/wrong tool calls | Tools/Response Handling |
| Tone Issues | Robotic, cold responses | Style |
| Missing Info | Didn't answer question | Goal/Response Handling |
| Guardrails | Off-topic responses | Guardrails |

## Analysis Template

When analyzing failures, fill out this template:

```
Failure ID: [test ID]
Category: [verbosity/formatting/tool/tone/missing-info/guardrail]
User Input: [what the user said]
Agent Output: [what the agent said]
Expected: [what should have happened]
Root Cause: [why it failed]
Fix: [specific prompt change needed]
Section: [which prompt section to modify]
```
