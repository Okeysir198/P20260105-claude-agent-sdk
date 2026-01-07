# Phase 5: ITERATE

Re-run tests and continue until target is met.

## 5.1 Re-run Tests

After TUNE phase improvements:

```bash
cd {agent_path}/eval && python run_eval.py --all
```

## 5.2 Compare Metrics

### Track Improvement Across Iterations

```
Iteration 1: 80% success rate (20/25)
Iteration 2: 88% success rate (22/25) [+8%]
Iteration 3: 92% success rate (23/25) [+4%]
```

### Update Metrics in Version Registry

```yaml
{sub_agent}:
  default: v2
  versions:
    v1:
      metrics:
        success_rate: 0.80
    v2:
      metrics:
        success_rate: 0.88  # Updated after iteration 2
```

## 5.3 Convergence Criteria

Stop iterating when ANY condition is met:

| Condition | Description | Action |
|-----------|-------------|--------|
| **Target Met** | Success rate >= target (default 90%) | Complete workflow successfully |
| **Max Iterations** | N iterations reached (default 3) | Report best version achieved |
| **No Improvement** | Same rate for 2 consecutive iterations | Report plateau |
| **Regression** | Success rate decreased | Rollback and stop |

### Configurable Parameters

```yaml
# In workflow_config.yaml
iterate:
  target_success_rate: 0.90
  max_iterations: 3
  min_improvement: 0.02  # Minimum improvement per iteration
  plateau_threshold: 2    # Iterations without improvement
  rollback_on_regression: true
```

## 5.4 Handling Plateaus

### Plateau Detection

```python
# Pseudo-code for plateau detection
iteration_history = [
    {"iteration": 1, "success_rate": 0.80},
    {"iteration": 2, "success_rate": 0.85},
    {"iteration": 3, "success_rate": 0.85},  # No improvement
]

recent_rates = [h["success_rate"] for h in iteration_history[-2:]]
if len(set(recent_rates)) == 1:
    print("Plateau detected")
```

### Plateau Actions

1. **Accept current state** - If close to target, may be acceptable
2. **Try different approach** - Different prompt strategy
3. **Review test expectations** - Tests may be unrealistic
4. **Flag for manual review** - Some issues need human insight

## 5.5 Handling Regressions

### Regression Detection

If iteration N success rate < iteration N-1:

```
Iteration 2: 88% success rate
Iteration 3: 82% success rate  # REGRESSION!
```

### Regression Response

1. **Automatic rollback** - Revert to previous prompt version
2. **Log regression** - Document what change caused it
3. **Stop iteration** - Don't continue with worse version
4. **Report finding** - Inform user about the regression

## 5.6 Final Report

### Success Report

```
Workflow Complete!

Agent: {agent_name}
Path: {agent_path}

Final Metrics:
  Success Rate: 92%
  Iterations: 3
  Tests Passed: 23/25

Prompt Versions:
  - greeting: v2 (improved)
  - verification: v3 (improved)
  - resolution: v1 (unchanged)

Remaining Failures:
  - E2E-002: Edge case timeout (known limitation)
  - VER-005: Unusual ID format (needs data fix)

Recommendations:
  1. Add more test data variations for ID formats
  2. Consider increasing timeout for complex flows
```

### Plateau Report

```
Workflow Stopped: Plateau Reached

Agent: {agent_name}
Final Success Rate: 85%
Target: 90%

Plateau Details:
  - Iterations 2 and 3 both at 85%
  - No improvement from prompt changes

Persistent Failures:
  - VER-003: Complex edge case (may need tool change)
  - E2E-001: Timeout issue (infrastructure)

Recommendations:
  1. Review if 85% is acceptable for deployment
  2. Consider tool-level changes for VER-003
  3. Investigate timeout root cause
```

## 5.7 Iteration Log

### Log Format

Track all iterations in `eval/results/iteration_log.yaml`:

```yaml
iterations:
  - number: 1
    timestamp: "2025-01-01T10:00:00Z"
    success_rate: 0.80
    tests_passed: 20
    tests_failed: 5
    changes: ["initial"]

  - number: 2
    timestamp: "2025-01-01T11:30:00Z"
    success_rate: 0.88
    tests_passed: 22
    tests_failed: 3
    changes:
      - "greeting_v2: Added wrong person handling"
      - "verification_v2: Clarified ID format rules"
    improvement: 0.08

  - number: 3
    timestamp: "2025-01-01T13:00:00Z"
    success_rate: 0.92
    tests_passed: 23
    tests_failed: 2
    changes:
      - "verification_v3: Added escalation trigger"
    improvement: 0.04
    status: "target_met"

final_status: "success"
final_success_rate: 0.92
total_iterations: 3
```

## 5.8 Recovery from Bad State

### If Agent is Broken

```bash
# Reset prompts to last known good
git checkout -- {agent_path}/prompts/

# Or restore specific version from registry
# Update _versions.yaml to use v1 for all agents
```

### If Tests Won't Run

```bash
# Verify framework files
python -m py_compile {agent_path}/eval/run_test.py
python -m py_compile {agent_path}/eval/run_eval.py

# Check eval_config.yaml imports
python -c "import yaml; yaml.safe_load(open('{agent_path}/eval/eval_config.yaml'))"
```

## 5.9 Success Criteria

Phase 5 is complete when:
- [ ] Final success rate calculated
- [ ] Version registry reflects final state
- [ ] Iteration log saved
- [ ] Final report generated
- [ ] Recommendations documented

## Related Skills

- All phases work together in this final phase
