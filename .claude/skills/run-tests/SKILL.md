---
name: run-tests
description: Run relevant tests based on recent changes or specific modules
---

# Run Tests

Intelligently runs tests based on what you're working on.

## Usage

- Run all tests: `/run-tests`
- Test specific router: `/run-tests websocket`
- Test with coverage: `/run-tests --coverage`
- Run failed tests only: `/run-tests --failed`

## Implementation

1. Detect recent changes (git diff or specified module)
2. Map files to test files:
   - `backend/api/routers/websocket.py` → `backend/tests/test_websocket*.py`
   - `backend/api/routers/sessions.py` → `backend/tests/test_api_agent_selection.py`
3. Run pytest with appropriate filters
4. Display results summary

## Commands

```bash
# All tests
cd backend && python -m pytest tests/ -v

# Specific test file
cd backend && python -m pytest tests/test_websocket_timing.py -v

# With coverage
cd backend && python -m pytest tests/ --cov=api --cov=cli --cov-report=term-missing

# Failed only
cd backend && python -m pytest tests/ --lf
```
