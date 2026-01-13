# Prompt Improvement Report

**Agent:** debt_collection
**Date:** 2026-01-06
**Version:** v1 -> v2
**Author:** prompt-improver

---

## Executive Summary

Improved the introduction and negotiation agent prompts to address tool calling failures and verbosity issues. Added explicit tool trigger conditions and response length limits. Expected success rate improvement from 72% to 85%.

---

## Failure Analysis

### Failures Addressed

| Test ID | Expected Behavior | Actual Behavior | Root Cause |
|---------|-------------------|-----------------|------------|
| INT-002 | Call `handle_wrong_person` tool | Apologized but no tool call | Missing explicit trigger condition |
| NEG-005 | Keep response under 25 words | Response was 78 words | No word limit in prompt |
| NEG-008 | Spell out dollar amount | Said "$2,500" literally | Missing TTS formatting rule |
| PAY-003 | Call `process_payment` after confirmation | Just acknowledged payment | Ambiguous tool trigger |

### Failure Patterns Identified

1. **Tool Missing (4 occurrences)**
   - Frequency: 4 of 12 failures
   - Affected section: Response Handling
   - Example transcript:
     ```
     User: Sorry, wrong number.
     Agent: I apologize for the mix-up. Thank you for your time.
     Expected: Should call handle_wrong_person() tool
     ```

2. **Verbosity (3 occurrences)**
   - Frequency: 3 of 12 failures
   - Affected section: Output Formatting
   - Example transcript:
     ```
     User: How much do I owe?
     Agent: I appreciate you asking about your outstanding balance. I understand
     that managing finances can be challenging, and I'm here to help you through
     this process. According to our records, your current outstanding amount is
     two thousand five hundred dollars, which has been overdue for forty-five days.
     Is there anything specific about this balance you'd like to discuss?
     Expected: Keep under 25 words
     ```

3. **Formatting (2 occurrences)**
   - Frequency: 2 of 12 failures
   - Affected section: Output Formatting
   - Agent said "$2,500" instead of "two thousand five hundred dollars"

---

## Changes Made

### Section: Tools / Response Handling

**Change Type:** modification

**Before:**
```yaml
tools:
  - handle_wrong_person: Use when person denies being the target
```

**After:**
```yaml
tools:
  - handle_wrong_person:
      description: Handle case when caller is not the intended person
      trigger: CALL IMMEDIATELY when user says "wrong number", "don't know them",
               "never heard of them", or denies being the named person
      after_call: End conversation politely
```

**Rationale:** Explicit trigger phrases ensure the LLM knows exactly when to invoke the tool.

### Section: Output Formatting

**Change Type:** addition

**Before:**
```yaml
# (No output formatting section)
```

**After:**
```yaml
output_formatting:
  - Keep all responses under 25 words
  - Respond in plain conversational speech only
  - NEVER use markdown, lists, or special characters
  - Spell out all currency: "two thousand five hundred dollars" not "$2,500"
  - Spell out phone numbers digit by digit with pauses
  - Ask only one question at a time
```

**Rationale:** TTS reads special characters literally. Word limits prevent agent monologues.

### Section: Style

**Change Type:** modification

**Before:**
```yaml
style:
  - Be professional and courteous
```

**After:**
```yaml
style:
  - Be professional and courteous
  - Acknowledge emotions before problem-solving
  - Answer questions directly, then stop
  - No preamble or filler phrases like "I appreciate you asking"
```

**Rationale:** Reduces verbosity while maintaining empathy.

---

## Improvement Categories

- [x] Clarity: Made tool trigger conditions explicit
- [ ] Structure: No structural changes
- [x] Tone: Added empathy acknowledgment guidance
- [x] Tool Usage: Added explicit trigger phrases for all tools

---

## Expected Impact

| Metric | Before (v1) | Expected (v2) |
|--------|-------------|---------------|
| Success Rate | 72% | 85% |
| Avg Turn Count | 4.2 | 3.5 |
| Tool Call Accuracy | 65% | 90% |

### Specific Improvements Expected

1. **INT-002**: Should now pass - explicit "wrong number" trigger added
2. **NEG-005**: Should now pass - 25 word limit enforced
3. **NEG-008**: Should now pass - currency spelling rule added
4. **PAY-003**: Should now pass - explicit confirmation trigger added

---

## Regression Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Responses too terse | Medium | Monitor user satisfaction in A/B test |
| Tool over-triggering | Low | Test with edge cases before promotion |
| Reduced personalization | Low | Empathy instructions preserved |

### Tests to Monitor

- [x] INT-001: Person confirms identity (ensure still passes)
- [x] NEG-001: Initial offer acceptance (ensure still passes)
- [x] PAY-001: Standard payment flow (ensure still passes)

---

## Validation Plan

1. **Unit Tests**: Run targeted tests for addressed failures
   ```bash
   cd agents/debt_collection
   python -m pytest eval/ -k "INT-002 or NEG-005 or NEG-008 or PAY-003" --prompt-version=v2
   ```

2. **Regression Tests**: Run full test suite
   ```bash
   python -m pytest eval/ --prompt-version=v2
   ```

3. **A/B Comparison**:
   - Control: v1
   - Treatment: v2
   - Sample size: 100 conversations
   - Duration: 48 hours

---

## Rollback Plan

If v2 shows degraded performance:

1. Update `_versions.yaml` defaults back to v1
2. Document failure modes for next iteration
3. Create v3 addressing new issues

---

## Appendix

### Files Modified

- `prompts/prompt01_introduction_v2.yaml` - New version with tool triggers
- `prompts/prompt03_negotiation_v2.yaml` - Added TTS formatting rules
- `prompts/_versions.yaml` - Updated metrics and defaults

### Automation Scripts Used

```bash
# Analyze failures
python scripts/analyze_failures.py eval/results.json --verbose

# Calculate baseline metrics
python scripts/calculate_metrics.py eval/results.json

# Compare after running v2 evals
python scripts/compare_versions.py prompts/_versions.yaml --v1 v1 --v2 v2 --format markdown
```

### Related Documentation

- [tts-optimization.md](../references/tts-optimization.md) - TTS best practices applied
- [failure-patterns.md](../references/failure-patterns.md) - Failure categorization reference

---

*Generated by prompt-improver skill*
