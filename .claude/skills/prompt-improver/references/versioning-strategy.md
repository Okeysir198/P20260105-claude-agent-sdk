# Prompt Versioning Strategy

Guide for managing prompt versions, tracking metrics, and iterating on improvements.

## Version Naming Convention

### File Naming

```
prompts/
  prompt01_agent.yaml        # v1 (baseline)
  prompt01_agent_v2.yaml     # v2 (first improvement)
  prompt01_agent_v3.yaml     # v3 (second improvement)
  _versions.yaml             # Version registry
```

### Version Numbers

- **v1**: Baseline version - initial working prompt
- **v2**: First improvement - usually empathetic/conversational tone
- **v3+**: Iterative improvements based on test results

## Version Lifecycle

### 1. Baseline (v1)

The first working version of a prompt:

- Focus on functionality over polish
- Establish correct tool usage patterns
- Define basic guardrails
- Set initial response structure

### 2. First Improvement (v2)

Common improvements for v2:

- Add empathy and warmth
- Improve TTS optimization (number spelling, etc.)
- Tighten response length
- Add missing edge case handling

### 3. Iterative Improvements (v3+)

Based on eval results:

- Fix specific failure patterns
- Tune for edge cases
- A/B test alternative approaches
- Optimize for specific metrics

## _versions.yaml Structure

```yaml
# Prompt Version Registry
# Updated automatically by prompt-improver skill

versions:
  v1:
    description: "Baseline professional prompts"
    created: "2024-01-15"
    status: archived

  v2:
    description: "Empathetic tone, TTS-optimized output"
    created: "2024-01-20"
    status: previous
    changes:
      - "Added word count limits (under 25 words)"
      - "Added number spelling rules"
      - "Improved emotional acknowledgment"

  v3:
    description: "Improved tool trigger conditions"
    created: "2024-01-25"
    status: active
    changes:
      - "Added explicit tool trigger phrases"
      - "Fixed missing parameter validation"
      - "Added fallback for unclear requests"

# Default version per prompt
defaults:
  prompt01_introduction: v3
  prompt02_verification: v2
  prompt03_resolution: v3

# Metrics tracking
metrics:
  prompt01_introduction:
    v1:
      evaluations: 100
      success_rate: 0.72
      avg_turn_count: 4.2
      tool_accuracy: 0.65
    v2:
      evaluations: 100
      success_rate: 0.81
      avg_turn_count: 3.8
      tool_accuracy: 0.78
    v3:
      evaluations: 50
      success_rate: 0.88
      avg_turn_count: 3.5
      tool_accuracy: 0.92

  prompt02_verification:
    v1:
      evaluations: 100
      success_rate: 0.85
    v2:
      evaluations: 75
      success_rate: 0.91
```

## Metrics to Track

### Core Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| success_rate | % of test cases passing | > 85% |
| avg_turn_count | Average conversation turns | < 5 |
| tool_accuracy | % of correct tool calls | > 90% |

### Secondary Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| avg_response_length | Average words per response | < 30 |
| interruption_rate | % of responses interrupted | < 10% |
| clarification_rate | % requiring clarification | < 15% |

## Version Workflow

### Creating a New Version

1. **Analyze current version failures**
   ```
   Read eval/results/latest.json
   ```

2. **Identify patterns** using failure-patterns.md

3. **Create new version file**
   ```
   Copy prompt01_agent_v2.yaml -> prompt01_agent_v3.yaml
   ```

4. **Apply targeted fixes** (one category per version)

5. **Update _versions.yaml**
   - Add new version entry
   - Update default if ready for testing
   - Mark previous version as 'previous'

6. **Run validation**
   ```bash
   pytest eval/ --prompt-version=v3
   ```

### Promoting a Version

When a new version shows improvement:

1. Update status in _versions.yaml:
   ```yaml
   versions:
     v2:
       status: previous  # was active
     v3:
       status: active    # promoted
   ```

2. Update defaults:
   ```yaml
   defaults:
     prompt01_agent: v3
   ```

3. Archive old versions after 30 days with no use

### Rolling Back

If a new version underperforms:

1. Update defaults back to previous version:
   ```yaml
   defaults:
     prompt01_agent: v2  # rollback from v3
   ```

2. Keep v3 for analysis, mark as 'failed':
   ```yaml
   versions:
     v3:
       status: failed
       failure_reason: "Increased clarification rate by 20%"
   ```

3. Create v4 addressing the issues

## Best Practices

### One Change Category Per Version

Don't mix multiple types of changes:

**Bad:**
```yaml
v2:
  changes:
    - "Fixed verbosity"
    - "Added new tool"
    - "Changed greeting"
    - "Updated guardrails"
```

**Good:**
```yaml
v2:
  changes:
    - "Added word count limits"
    - "Removed filler phrases"
    - "Tightened response structure"
  # All focused on verbosity
```

### Document Rationale

Always explain why changes were made:

```yaml
v2:
  description: "TTS optimization for number handling"
  rationale: |
    v1 failed 12 tests related to phone number formatting.
    Users reported confusion when TTS read "555-1234" as
    "five hundred fifty-five dash one thousand two hundred thirty-four"
  changes:
    - "Added phone number spelling rule"
    - "Added example format in prompt"
```

### Preserve All Versions

Never delete or overwrite previous versions:

- Enables A/B testing
- Allows rollback
- Provides learning history
- Supports compliance requirements

### Test Before Promoting

Run full eval suite before changing defaults:

```bash
# Test new version
pytest eval/ --prompt-version=v3

# Compare with current
pytest eval/ --prompt-version=v2 --prompt-version=v3 --compare
```

## Version Comparison Template

When evaluating versions:

```markdown
## Version Comparison: v2 vs v3

### Metrics
| Metric | v2 | v3 | Change |
|--------|-----|-----|--------|
| success_rate | 0.81 | 0.88 | +8.6% |
| avg_turn_count | 3.8 | 3.5 | -7.9% |
| tool_accuracy | 0.78 | 0.92 | +17.9% |

### Changes Made
1. Added explicit tool trigger conditions
2. Improved parameter validation messaging
3. Added fallback for ambiguous requests

### Tests Fixed
- TEST-015: Now correctly calls book_appointment
- TEST-023: Asks for missing time before booking
- TEST-041: Handles "schedule something" gracefully

### Regressions
- None observed

### Recommendation
Promote v3 to active status
```
