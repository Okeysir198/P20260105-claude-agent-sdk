---
name: voice-agent-workflow
description: End-to-end voice agent development lifecycle. Orchestrates build, test, run, tune, and iterate phases for complete agent development.
triggers: ["build and test agent", "complete agent development", "full agent workflow", "end-to-end agent", "agent lifecycle", "build test tune", "create and test agent"]
---

# Voice Agent Workflow Skill

Orchestrate the complete voice agent development lifecycle: BUILD, TEST, RUN, TUNE, and ITERATE phases in a single cohesive workflow.

## When to Use

- User wants to create AND test an agent in one session
- User asks for "complete agent development"
- User mentions "build and test", "end-to-end", or "full workflow"
- User wants automated prompt tuning based on test results
- User requests iterative improvement until a success target is met

## Workflow Overview

```
+-------+     +------+     +-----+     +------+     +---------+
| BUILD | --> | TEST | --> | RUN | --> | TUNE | --> | ITERATE |
+-------+     +------+     +-----+     +------+     +---------+
    |             |            |           |             |
    v             v            v           v             v
 Generate     Create       Execute     Analyze       Re-run
 agent        eval/        tests       failures      tests
 structure    folder       and save    and improve   until
              and cases    results     prompts       target met
```

## Phase Summaries

### Phase 1: BUILD

Generate the voice agent structure based on user requirements.

**Key Actions:**
1. Gather requirements (domain, sub-agents, tools, tone, constraints)
2. Create directory structure: `sub_agents/`, `tools/`, `state/`, `prompts/`
3. Generate core files: `agent.yaml`, `agents.py`, `shared_state.py`
4. Validate Python syntax

**Details:** See [references/phase1-build.md](references/phase1-build.md)

### Phase 2: TEST

Create the evaluation framework and test cases.

**Key Actions:**
1. Create `eval/` directory with `testcases/` and `results/`
2. Copy framework files (`run_test.py`, `run_eval.py`, etc.)
3. Generate `eval_config.yaml`
4. Create test cases for each sub-agent
5. Generate E2E test cases for multi-agent flows

**Details:** See [references/phase2-test.md](references/phase2-test.md)

### Phase 3: RUN

Execute the test suite and capture results.

**Key Actions:**
1. Run tests: `python run_eval.py --all`
2. Capture results to `eval/results/`
3. Parse and report summary statistics
4. Categorize failures by sub-agent

**Details:** See [references/phase3-run.md](references/phase3-run.md)

### Phase 4: TUNE

Analyze failures and improve prompts.

**Key Actions:**
1. Group failures by sub-agent
2. Identify patterns (missing instructions, unclear conditions, etc.)
3. Generate improved prompt versions
4. Update version registry (`prompts/_versions.yaml`)

**Details:** See [references/phase4-tune.md](references/phase4-tune.md)

### Phase 5: ITERATE

Re-run tests and continue until target is met.

**Key Actions:**
1. Re-run all tests
2. Compare metrics to previous iteration
3. Check convergence criteria
4. Generate final report

**Convergence Criteria:**

| Condition | Action |
|-----------|--------|
| Target met (default 90%) | Complete successfully |
| Max iterations reached (default 3) | Report best version |
| Plateau (no improvement for 2 iterations) | Report plateau |
| Regression (success rate dropped) | Rollback and stop |

**Details:** See [references/phase5-iterate.md](references/phase5-iterate.md)

## Quick Start Example

**User:** "Create a restaurant booking agent and test it"

```
Phase 1: BUILD
  [x] Gathered requirements: booking domain, 3 sub-agents
  [x] Created restaurant_booking/
  [x] Generated 12 files
  [x] Validated syntax: all clean

Phase 2: TEST
  [x] Created eval/ folder
  [x] Copied framework files
  [x] Generated 18 test cases
  [x] Created simulated user config

Phase 3: RUN (Iteration 1)
  [x] Executed 18 tests
  [x] Results: 14/18 passed (78%)
  [x] Saved to eval/results/

Phase 4: TUNE
  [x] Analyzed 4 failures
  [x] Pattern: Missing confirmation handling
  [x] Generated greeting_v2.yaml
  [x] Updated _versions.yaml

Phase 5: ITERATE (Iteration 2)
  [x] Re-ran 18 tests
  [x] Results: 17/18 passed (94%)
  [x] Target met!

COMPLETE: restaurant_booking agent at 94% success rate
```

## Configuration

Copy `templates/workflow_config.yaml.template` to configure:

```yaml
iterate:
  target_success_rate: 0.90
  max_iterations: 3
  min_improvement: 0.02
  rollback_on_regression: true
```

See [templates/workflow_config.yaml.template](templates/workflow_config.yaml.template) for full options.

## Templates

| Template | Purpose |
|----------|---------|
| `templates/workflow_config.yaml.template` | Workflow parameters configuration |
| `templates/iteration_log.yaml.template` | Track iteration history and metrics |

## Integration with Other Skills

| Skill | Phase Used | Concepts Applied |
|-------|------------|------------------|
| `voice-agent-generator` | BUILD | Directory structure, file templates |
| `eval-generator` | TEST | Eval folder, test case format |
| `prompt-improver` | TUNE | Failure analysis, version registry |

## Key Commands

```bash
# Run all tests
cd {agent_path}/eval && python run_eval.py --all

# Run specific tests
python run_test.py --tags unit
python run_test.py --file testcases/agent01_{sub_agent}.yaml

# Validate syntax
python -m py_compile {agent_path}/agents.py
```

## Final Report Format

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

Recommendations:
  1. Add more test data variations
  2. Consider increasing timeout for complex flows
```

## Success Criteria

Workflow is successful when:
1. Agent directory exists with all required files
2. Eval folder exists with valid tests
3. At least one test run completed
4. Final success rate reported
5. Version registry reflects current state

## Limitations

- Does not deploy the agent (out of scope)
- Does not integrate with external CI/CD
- Prompt improvements are suggestions (may need manual refinement)
- Maximum 3 iterations by default (adjustable via config)
