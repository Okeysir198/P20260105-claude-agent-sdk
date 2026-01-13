# Phase 4: TUNE

Analyze failures and improve prompts.

## 4.1 Failure Analysis

### Group Failures by Sub-agent

```
Failures by Agent:
  verification (3 failures):
    - VER-002: ID validation edge case
    - VER-005: Wrong person handling
    - VER-008: Expired ID scenario

  resolution (2 failures):
    - RES-003: Escalation not triggered
    - RES-007: Refund limit exceeded
```

### Identify Failure Patterns

| Pattern | Symptoms | Root Cause |
|---------|----------|------------|
| **Missing instructions** | Agent doesn't know what to do | Prompt lacks scenario handling |
| **Unclear conditions** | Agent makes wrong decisions | Ambiguous if/then rules |
| **Missing guardrails** | Agent does forbidden actions | No explicit constraints |
| **Tool misuse** | Wrong tool or parameters | Poor tool descriptions |
| **Context loss** | Agent forgets earlier info | State not preserved |

### Analysis Questions

For each failure, ask:
1. What did the agent do?
2. What should it have done?
3. Why did it make the wrong choice?
4. What prompt change would fix this?

## 4.2 Prompt Improvement Strategy

### Read Current Prompt

```bash
cat {agent_path}/prompts/prompt0X_{sub_agent}.yaml
```

### Generate Improved Version

Create new version file: `prompts/prompt0X_{sub_agent}_v2.yaml`

### Types of Improvements

| Issue | Improvement Type | Example |
|-------|------------------|---------|
| Missing scenario | Add instruction block | "When user says X, do Y" |
| Wrong decision | Clarify conditions | "Only if X AND Y, then Z" |
| Forbidden action | Add guardrail | "NEVER do X under any circumstance" |
| Tool misuse | Improve tool docs | "Use tool X when condition Y" |

### Improvement Template

```yaml
# Added in v2:
# - Explicit handling for {failure_scenario}
# - Guardrail against {forbidden_action}
# - Clarified condition for {ambiguous_case}

instructions: |
  # Previous content preserved...

  ## New Section: {Failure Scenario} Handling

  When {condition}:
  1. {specific_action_1}
  2. {specific_action_2}
  3. {expected_outcome}

  ## Guardrails

  NEVER:
  - {forbidden_action_1}
  - {forbidden_action_2}
```

## 4.3 Version Registry

### Update `prompts/_versions.yaml`

```yaml
{sub_agent}:
  default: v2
  versions:
    v1:
      file: prompt0X_{sub_agent}.yaml
      created: 2025-01-01
      metrics:
        success_rate: 0.80
        tests_passed: 8
        tests_failed: 2
    v2:
      file: prompt0X_{sub_agent}_v2.yaml
      created: 2025-01-02
      parent: v1
      changes:
        - "Added handling for wrong person scenario"
        - "Clarified verification conditions"
        - "Added guardrail for PII disclosure"
      metrics: null  # Filled after testing
```

### Version Naming Convention

| Version | When to Use |
|---------|-------------|
| `v1` | Initial prompt |
| `v2`, `v3`... | Incremental improvements |
| `v1.1`, `v1.2`... | Minor tweaks to existing version |

## 4.4 Rollback Strategy

### When to Rollback

Rollback if new version:
- Has lower success rate than previous
- Introduces new failures in previously passing tests
- Causes agent behavior regression

### Rollback Process

```yaml
# In _versions.yaml
{sub_agent}:
  default: v1  # Reverted from v2
  versions:
    v1:
      metrics:
        success_rate: 0.80
    v2:
      metrics:
        success_rate: 0.75  # Worse!
      deprecated: true
      deprecation_reason: "Regression in success rate"
```

### Git Recovery

```bash
# If all else fails, restore from git
git checkout -- {agent_path}/prompts/
```

## 4.5 Incremental Changes

### Rule: One Problem at a Time

Each version should address ONE category of failures:
- v2: Fix wrong person handling
- v3: Add escalation triggers
- v4: Improve tool selection

### Why Incremental?

- Easier to attribute improvements
- Easier to rollback specific changes
- Better understanding of what works

## 4.6 Success Criteria

Phase 4 is complete when:
- [ ] All failures analyzed
- [ ] Patterns identified
- [ ] New prompt version(s) created
- [ ] Version registry updated
- [ ] Changes documented
- [ ] Ready for re-run in ITERATE phase

## Related Skills

- **prompt-improver**: Detailed prompt analysis and improvement patterns
