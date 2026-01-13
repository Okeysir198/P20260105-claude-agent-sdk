# TTS Optimization Best Practices

Checklist for optimizing voice agent prompts for text-to-speech output.

> **Note on Realtime Models**: If your agent uses a realtime native speech model
> (e.g., OpenAI Realtime API, Gemini Live API), most of these formatting rules
> may be unnecessary as the model handles speech output directly. These rules
> primarily apply to STT-LLM-TTS pipelines where the LLM outputs text that is
> then converted to speech.

## Output Format Rules

### Plain Text Only

- NO markdown (no **, *, #, -, [], etc.)
- NO JSON objects or arrays
- NO code blocks or backticks
- NO bullet points or numbered lists
- NO tables or structured data
- NO emojis or special characters

**Bad:**
```
Here are your options:
- Option A: $100
- Option B: $200
```

**Good:**
```
You have two options. Option A costs one hundred dollars. Option B costs two hundred dollars.
```

### Keep Responses Brief

- 1-3 sentences maximum for most responses
- Ask one question at a time
- Avoid long monologues or explanations
- Let the user guide the conversation depth

**Bad:**
```
Thank you for calling. I'm here to help you today with whatever you need.
We have a wide range of services including account management, billing inquiries,
technical support, and general information. How can I assist you?
```

**Good:**
```
Hi, thanks for calling. How can I help you today?
```

## Number Formatting

### Spell Out Numbers

- "one thousand" not "1000"
- "twenty-three" not "23"
- "fifteen percent" not "15%"
- "two point five" not "2.5"

### Phone Numbers

Spell out with natural pauses:

- "five five five, one two three, four five six seven" not "555-123-4567"
- Group digits naturally (3-3-4 or 3-4-4 patterns)

**Bad:** "Call 555-123-4567"

**Good:** "Call five five five, one two three, four five six seven"

### Currency

- "one hundred dollars" not "$100"
- "fifty cents" not "$0.50"
- "twenty-five dollars and ninety-nine cents" not "$25.99"

### Dates

- "January fifteenth, twenty twenty-four" not "1/15/2024"
- "March third" not "3/3"

### Time

- "three thirty in the afternoon" not "3:30 PM"
- "nine o'clock in the morning" not "9:00 AM"

## Email and URL Handling

### Email Addresses

Spell out completely:

- "john at example dot com" not "john@example.com"
- "support at company dot org" not "support@company.org"

### URLs

- Omit "https://" and "www."
- "example dot com slash help" not "https://www.example.com/help"
- For complex URLs, consider saying "I'll send you the link"

## Acronyms and Abbreviations

### Avoid Unclear Acronyms

Spell out or use full words:

- "as soon as possible" not "ASAP" (unless commonly understood)
- "United States" not "U.S."
- "okay" not "OK"

### Common Safe Acronyms

These are generally safe to use as-is:
- NASA, FBI, CEO, ATM, PIN, ID

### Industry-Specific

Only use if the caller has demonstrated familiarity:
- API, SDK, DNS, etc.

## Conversational Flow

### One Question at a Time

**Bad:**
```
Can you tell me your name, phone number, and email address?
```

**Good:**
```
What's your name?
(wait for response)
Thanks. What's the best phone number to reach you?
(wait for response)
And your email address?
```

### Natural Transitions

Use verbal cues instead of visual formatting:

**Bad:**
```
Your options are:
1. Basic plan
2. Standard plan
3. Premium plan
```

**Good:**
```
You have three options. First, the basic plan. Second, the standard plan.
And third, the premium plan. Which would you like to hear more about?
```

### Acknowledgment Words

Use natural acknowledgments:
- "Got it"
- "Sure thing"
- "Okay"
- "Let me check on that"

## Prompt Template Section

Add this to your prompts:

```yaml
# Output Formatting
- Respond in plain conversational speech only
- Keep responses under three sentences
- Never use markdown, lists, or special formatting
- Spell out all numbers naturally
- Spell out phone numbers digit by digit with pauses
- Spell out email addresses: "name at domain dot com"
- Ask only one question at a time
```

## Quick Reference Checklist

Before deploying a prompt, verify:

- [ ] No markdown syntax anywhere
- [ ] Response length limit specified (e.g., "under 25 words")
- [ ] Numbers spelled out rule included
- [ ] Phone format rule included
- [ ] Email format rule included
- [ ] One question at a time rule included
- [ ] No JSON/structured data in responses
- [ ] Natural transition phrases used
