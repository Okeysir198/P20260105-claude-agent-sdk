---
name: prompt-improver
description: >
  Analyze eval results and improve voice agent prompts for better TTS output.
  Triggers: "improve prompts", "tune prompts", "optimize for speech",
  "fix prompt issues", "TTS optimization", "prompt failures"
---

# Prompt Improver Skill

Analyze evaluation failures and improve LiveKit voice agent prompts following TTS best practices.

## When to Use

- After running evals and seeing failures in `eval/results/`
- When prompts produce responses that sound bad when spoken
- To optimize prompts for text-to-speech output
- To fix tool usage issues or tone problems

## Prerequisites

1. Agent must have `eval/` folder with test results
2. Agent must have `prompts/` folder with versioned prompts
3. Agent must have `prompts/_versions.yaml` for version tracking

## Improvement Workflow

Follow this cycle: **Analyze -> Improve -> Validate**

```
[Run Evals] -> [Analyze Failures] -> [Identify Patterns] -> [Update Prompts]
                                                                   |
     [Validate & Compare] <- [Update _versions.yaml] <-------------+
```

---

## Automation Scripts

Three scripts are provided in `templates/scripts/` to automate the improvement workflow.

### 1. Analyze Failures

Parse eval results and categorize failures by pattern:

```bash
# Basic analysis
python templates/scripts/analyze_failures.py eval/results.json

# Verbose output with examples
python templates/scripts/analyze_failures.py eval/results.json --verbose

# Output to JSON for programmatic use
python templates/scripts/analyze_failures.py eval/results.json --json

# Save structured results
python templates/scripts/analyze_failures.py eval/results.json --output failures.json
```

**Output includes:**
- Failure categories (tool_missing, formatting, verbosity, tone, etc.)
- Count and percentage per category
- Affected test IDs
- Example failures with excerpts
- Fix suggestions per category

### 2. Calculate Metrics

Calculate success rate and detailed metrics from results:

```bash
# Text report (default)
python templates/scripts/calculate_metrics.py eval/results.json

# JSON output
python templates/scripts/calculate_metrics.py eval/results.json --format json

# YAML output
python templates/scripts/calculate_metrics.py eval/results.json --format yaml

# Summary only
python templates/scripts/calculate_metrics.py eval/results.json --summary-only

# Save to file
python templates/scripts/calculate_metrics.py eval/results.json --output metrics.json
```

**Output includes:**
- Total/passed/failed counts
- Success rate (decimal and percentage)
- Average score and latency
- Breakdown by tag, sub-agent, and source file
- List of failed test IDs

### 3. Compare Versions

Compare metrics across prompt versions:

```bash
# Compare v1 and v2 (default)
python templates/scripts/compare_versions.py prompts/_versions.yaml

# Compare specific versions
python templates/scripts/compare_versions.py prompts/_versions.yaml --v1 v1 --v2 v3

# Compare specific prompt
python templates/scripts/compare_versions.py prompts/_versions.yaml --prompt prompt01_agent

# Markdown report
python templates/scripts/compare_versions.py prompts/_versions.yaml --format markdown

# Save comparison
python templates/scripts/compare_versions.py prompts/_versions.yaml --output comparison.md
```

**Output includes:**
- Metrics for each version side-by-side
- Percentage change with improvement indicators
- Recommendation (promote/keep/evaluate)
- Version descriptions and status

---

## Step-by-Step Process

### Step 1: Analyze Evaluation Results

Run the analyze script on your results:

```bash
python templates/scripts/analyze_failures.py eval/results.json --verbose
```

Or use the Read tool to examine failure logs:

```
Read eval/results/latest.json
Read eval/results/failures/
```

Look for:
- Which tests failed and why
- Common patterns across failures
- Transcript excerpts showing issues

### Step 2: Identify Failure Patterns

The analyze script categorizes failures automatically. Common patterns:

| Pattern | Symptoms | Solution |
|---------|----------|----------|
| tool_missing | Expected tool not called | Add explicit trigger conditions |
| tool_wrong | Wrong tool or parameters | Clarify when each tool applies |
| formatting | Markdown, lists, JSON in output | Add "plain text only" instruction |
| verbosity | Responses > 3 sentences | Add explicit word limits |
| tone | Too formal, not empathetic | Adjust style section |
| missing_info | Didn't address question | Improve response handling section |
| guardrail | Off-topic responses | Add explicit boundaries |

See `references/failure-patterns.md` for detailed guidance.

### Step 3: Read Current Prompt Version

Use Read tool to examine the current prompt:

```
Read prompts/prompt01_agent.yaml
Read prompts/_versions.yaml
```

Or calculate current metrics:

```bash
python templates/scripts/calculate_metrics.py eval/results.json
```

### Step 4: Generate Improved Version

Create a new versioned prompt file using Write tool:

```
Write prompts/prompt01_agent_v2.yaml
```

Apply improvements following TTS best practices from `references/tts-optimization.md`:

**Identity Section:**
- Start with "You are {name}, a {role}..."
- Define clear responsibilities

**Output Format Section (Critical):**
- Plain text only, NO markdown/JSON/code blocks
- Keep responses brief: 1-3 sentences max
- Spell out numbers: "one thousand" not "1000"
- Spell out phone numbers: "five five five, one two three four"
- Spell out emails: "john at example dot com"

**Tools Section:**
- Add explicit trigger conditions for each tool
- Example: "CALL tool_name IMMEDIATELY when user mentions X"
- Specify required parameters and post-call behavior

**Goals Section:**
- Single clear objective
- Prioritized sub-goals

**Guardrails Section:**
- Explicit boundaries
- Redirect phrases for out-of-scope topics

### Step 5: Update Version Registry

Use Edit tool to update `prompts/_versions.yaml`:

```yaml
versions:
  v1:
    description: "Baseline professional prompts"
    created: "2024-01-15"
    status: previous
  v2:
    description: "Improved empathetic tone, TTS-optimized"
    created: "2024-01-20"
    status: active
    changes:
      - "Added explicit word limits"
      - "Removed markdown formatting"
      - "Improved tool trigger conditions"

defaults:
  prompt01_agent: v2

metrics:
  prompt01_agent:
    v1: {evaluations: 50, success_rate: 0.72}
    v2: {evaluations: 0, success_rate: null}
```

### Step 6: Validate Changes

Run targeted tests on the new version:

```bash
cd agent_directory
pytest eval/ -k "failing_test_name" --prompt-version=v2
```

Then calculate metrics and compare:

```bash
# Calculate new metrics
python templates/scripts/calculate_metrics.py eval/results.json

# Compare versions
python templates/scripts/compare_versions.py prompts/_versions.yaml --v1 v1 --v2 v2
```

---

## Output

After improving prompts, provide:

1. **Summary of changes** - What was modified and why
2. **Files modified** - List of prompt files updated
3. **Metrics comparison** - Before/after success rates
4. **Next steps** - How to validate the improvements

See `templates/example_improvement_report.md` for a complete example.

---

## TTS Optimization Quick Reference

From `references/tts-optimization.md`:

**Numbers:**
- "one thousand" not "1000"
- "twenty-three" not "23"

**Phone Numbers:**
- "five five five, one two three, four five six seven" not "555-123-4567"

**Currency:**
- "one hundred dollars" not "$100"
- "twenty-five ninety-nine" not "$25.99"

**Emails:**
- "john at example dot com" not "john@example.com"

**Formatting:**
- NO markdown (**, *, #, -)
- NO JSON or code blocks
- Use verbal transitions: "first... second... third..."

**Length:**
- Keep responses under 25 words
- One question at a time
- No preamble or filler phrases

---

## Reference Files

- `references/tts-optimization.md` - TTS best practices checklist
- `references/failure-patterns.md` - Common failure categories and fixes
- `references/versioning-strategy.md` - Version workflow and metrics
- `templates/example_improvement_report.md` - Example improvement report
- `templates/scripts/` - Automation scripts

---

## Example Improvement

**Before (v1):**
```yaml
tools:
  - handle_wrong_person: Use when person denies being the target
```

**After (v2):**
```yaml
tools:
  - handle_wrong_person:
      trigger: CALL IMMEDIATELY when user says "wrong number",
               "don't know them", or denies being the named person
      after_call: End conversation politely

output_formatting:
  - Keep responses under 25 words
  - Spell out currency: "two thousand dollars" not "$2,000"
```

---

## Tips

- Make one category of changes per version for easier A/B testing
- Always preserve the previous version, never overwrite
- Document the rationale for each change in _versions.yaml
- Monitor regression in areas not targeted by improvements
- Use automation scripts to track metrics consistently
- Exit code from scripts indicates pass/fail (for CI integration)
