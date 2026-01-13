# Phase 3: RUN

Execute the test suite and capture results.

## 3.1 Running Tests

### Run All Tests

```bash
cd {agent_path}/eval && python run_eval.py --all 2>&1 | tee results/run_$(date +%Y%m%d_%H%M%S).log
```

### Run Specific Categories

```bash
# Unit tests only
python run_test.py --tags unit

# E2E tests only
python run_test.py --tags e2e

# Specific agent tests
python run_test.py --file testcases/agent01_{sub_agent}.yaml

# Single test case
python run_test.py --name "GRT-001"
```

### Run with Verbose Output

```bash
python run_test.py --all --verbose
```

## 3.2 Results Directory Structure

Results are saved to `eval/results/`:

```
eval/results/
  run_20250101_120000.log     # Full output log
  summary.json                 # Pass/fail counts
  failures/                    # Individual failure details
    TEST-001_failure.json
    TEST-002_failure.json
```

### Summary JSON Format

```json
{
  "timestamp": "2025-01-01T12:00:00Z",
  "total": 25,
  "passed": 20,
  "failed": 5,
  "skipped": 0,
  "success_rate": 0.80,
  "duration_seconds": 45.2,
  "by_agent": {
    "greeting": {"passed": 8, "failed": 1},
    "verification": {"passed": 7, "failed": 2},
    "resolution": {"passed": 5, "failed": 2}
  }
}
```

### Failure JSON Format

```json
{
  "test_name": "VER-002",
  "agent_id": "verification",
  "user_input": "My ID is ABC123",
  "expected": "contains_function_call: validate_id",
  "actual": "Agent asked for ID format clarification",
  "assertion_type": "contains_function_call",
  "full_response": "..."
}
```

## 3.3 Report Summary

Parse and display results:

```
Test Results Summary:
  Total: 25
  Passed: 20
  Failed: 5
  Success Rate: 80%

Results by Agent:
  greeting: 8/9 (89%)
  verification: 7/9 (78%)
  resolution: 5/7 (71%)

Failed Tests:
  - VER-002: ID validation edge case
  - VER-005: Wrong person handling
  - RES-003: Escalation not triggered
  - E2E-001: Full flow timeout
  - E2E-002: Handoff context lost
```

## 3.4 Common Issues

### Test Framework Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `ModuleNotFoundError` | Missing dependency | `pip install {module}` |
| `ImportError: AGENT_CLASSES` | Wrong import path | Check eval_config.yaml imports |
| `KeyError: 'test_data'` | Missing test data | Add default_test_data to test file |
| `TimeoutError` | LLM response too slow | Increase timeout in config |

### Test Failures

| Pattern | Likely Cause | Next Phase Action |
|---------|--------------|-------------------|
| All tests fail | Framework config issue | Fix eval_config.yaml |
| One agent fails all | Prompt fundamentally broken | Rewrite prompt in TUNE |
| Edge cases fail | Missing instructions | Add cases in TUNE |
| E2E fails | Handoff issues | Check handoff config |

## 3.5 Iteration Tracking

Log each run for iteration comparison:

```bash
# Append to iteration log
echo "Iteration $N: $(date) - Success rate: $RATE" >> results/iterations.log
```

## 3.6 Success Criteria

Phase 3 is complete when:
- [ ] Tests executed without framework errors
- [ ] Results saved to eval/results/
- [ ] Summary statistics calculated
- [ ] Failures categorized by agent
- [ ] Ready for TUNE phase analysis

## Related Skills

- **eval-generator**: Test runner implementation details
