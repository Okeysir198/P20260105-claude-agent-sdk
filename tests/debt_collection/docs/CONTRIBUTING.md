# Contributing Guide

## Development Workflow

### Setting Up Development Environment

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd livekit-backend/agents/debt_collection
   ```

2. **Create Python virtual environment:**
   ```bash
   cd ../../..  # Go to livekit-backend directory
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

5. **Verify installation:**
   ```bash
   cd agents/debt_collection
   python agents.py --help
   ```

### Running Locally

**Start the agent:**
```bash
# From livekit-backend/agents/debt_collection
python agents.py dev
```

**Run tests:**
```bash
cd eval
python run_tests.py
```

**Run specific test:**
```bash
python run_tests.py --test "Person confirms identity"
```

**Interactive testing:**
```bash
python run_tests.py --interactive
```

---

## Code Style Guidelines

### Python Style Guide

We follow **PEP 8** with some project-specific conventions.

#### General Principles

1. **Readability over cleverness** - Write code that's easy to understand
2. **Explicit over implicit** - Be clear about what code does
3. **Flat over nested** - Avoid deep nesting (max 3 levels)
4. **DRY (Don't Repeat Yourself)** - Extract common patterns
5. **YAGNI (You Aren't Gonna Need It)** - Don't add unused features

#### Formatting

**Line Length:**
- Maximum 100 characters per line
- Break long lines at logical points

**Indentation:**
- 4 spaces (no tabs)
- Continuation lines aligned with opening delimiter

**Imports:**
```python
# Standard library
import json
import logging
from pathlib import Path

# Third-party
from livekit.agents import AgentServer
from livekit.plugins import openai

# Local
from shared_state import UserData
from tools import get_tools_by_names
```

**Blank Lines:**
- Two blank lines between top-level functions/classes
- One blank line between methods
- One blank line to separate logical sections within functions

#### Naming Conventions

```python
# Constants (module level)
MAX_TOOL_STEPS = 5
DEFAULT_PORT = 8083

# Classes
class DebtorProfile:
    pass

class PaymentAgent(BaseAgent):
    pass

# Functions and methods
def get_agent_tools(agent_id: str) -> list:
    pass

async def entrypoint(ctx: JobContext):
    pass

# Variables
user_data = UserData(debtor=debtor, call=call_state)
script_config = SCRIPT_TYPES[script_type]

# Private methods/functions (single underscore)
def _internal_helper():
    pass

# Type aliases
RunContext_T = RunContext[UserData]
```

#### Type Hints

Always use type hints for function signatures:

```python
from typing import Optional, Dict, List, Any

def validate_bank_details(
    bank_name: str,
    account_number: str,
    branch_code: str
) -> Dict[str, Any]:
    """Validate South African bank details."""
    pass

def get_script_config(script_type: str) -> Optional[Dict[str, Any]]:
    """Get configuration for a specific script type."""
    return SCRIPT_TYPES.get(script_type)
```

#### Docstrings

Use Google-style docstrings:

```python
def calculate_discount(
    balance: float,
    script_type: str,
    payment_type: str
) -> float:
    """Calculate discount amount based on script type and payment type.

    Args:
        balance: Outstanding balance amount
        script_type: Script type identifier (e.g., 'prelegal_150')
        payment_type: Payment type ('settlement' or 'installment')

    Returns:
        Discount amount in Rands

    Raises:
        ValueError: If script_type is unknown or discount not applicable
    """
    pass
```

#### Error Handling

Be explicit about error handling:

```python
# Good
try:
    debtor = DebtorProfile(**debtor_data)
except TypeError as e:
    logger.error(f"Invalid debtor data: {e}", exc_info=True)
    raise ValueError(f"Invalid debtor data structure: {e}") from e

# Avoid bare except
# Bad
try:
    debtor = DebtorProfile(**debtor_data)
except:  # Don't do this
    pass
```

#### Logging

Use structured logging with appropriate levels:

```python
import logging

logger = logging.getLogger("debt-collection-agent")

# Use appropriate log levels
logger.debug("Detailed information for debugging")
logger.info("General informational messages")
logger.warning("Warning messages for unexpected situations")
logger.error("Error messages for failures", exc_info=True)
logger.critical("Critical failures requiring immediate attention")

# Include context
logger.info(f"User {user_id} verified {len(verified_fields)} fields")
logger.error(f"Failed to initialize agent: {e}", exc_info=True)
```

---

## Testing Requirements

### Unit Tests

**Location:** `testcases/agent0X_*.yaml`

**Structure:**
```yaml
- name: "Test name"
  description: "What this test validates"
  tags: [unit, agent_name]
  input: "User input message"
  expected_tool: "tool_name"
  expected_state:
    field_name: expected_value
  assertions:
    - type: tool_called
      tool: tool_name
    - type: state_changed
      field: field_name
      value: expected_value
```

**Example:**
```yaml
- name: "Person confirms identity"
  description: "Test that person confirmation triggers correct tool and handoff"
  tags: [unit, introduction]
  input: "Yes, this is John Smith speaking"
  expected_tool: "confirm_person"
  expected_state:
    person_confirmed: true
    person_type: "self"
  assertions:
    - type: tool_called
      tool: confirm_person
    - type: handoff_triggered
      next_agent: verification
```

### Integration Tests

**E2E Flow Tests:**

```yaml
# testcases/agent00_e2e_flow.yaml
- name: "Complete successful payment flow"
  description: "Full flow from introduction to payment confirmation"
  tags: [e2e, integration]
  steps:
    - agent: introduction
      input: "Yes, I'm John"
      expected_tool: confirm_person

    - agent: verification
      input: "My ID number is 8501125678901"
      expected_tool: verify_field

    - agent: negotiation
      input: "I accept the settlement offer"
      expected_tool: accept_arrangement

    - agent: payment
      input: "My bank is Standard Bank, account 1234567890"
      expected_tool: capture_immediate_debit

    - agent: closing
      input: "No, thank you"
      expected_tool: end_call
```

### Running Tests

```bash
# Run all tests
cd eval
python run_tests.py

# Run specific test file
python run_tests.py --file agent01_introduction.yaml

# Run by tag
python run_tests.py --tags unit,verification

# Run specific test
python run_tests.py --test "Person confirms identity"

# Interactive mode
python run_tests.py --interactive
```

### Test Coverage Requirements

- **New features:** Must include unit tests for all tools and functions
- **Bug fixes:** Must include regression test reproducing the bug
- **Agents:** Each agent must have minimum 5 test cases covering happy path and edge cases
- **Tools:** Each tool must have minimum 3 test cases (success, validation error, edge case)

---

## Documentation Standards

### Code Documentation

**Module-Level Docstrings:**

```python
"""
Module name and brief description.

This module provides functionality for X, Y, and Z.
It is used by agents A and B for purpose P.

Key Features:
- Feature 1 description
- Feature 2 description
- Feature 3 description

Usage:
    from module_name import function_name

    result = function_name(arg1, arg2)
"""
```

**Function/Method Documentation:**

```python
def process_payment(
    amount: float,
    method: str,
    userdata: UserData
) -> Dict[str, Any]:
    """Process payment arrangement and update call state.

    This function validates payment details, applies business rules,
    logs the payment capture event, and updates the call state.

    Args:
        amount: Payment amount in Rands (must be positive)
        method: Payment method ('debit_order', 'debicheck', 'once_off')
        userdata: Session user data containing debtor and call state

    Returns:
        Dictionary containing:
            - success (bool): Whether processing succeeded
            - payment_id (str): Generated payment ID
            - next_step (str): Next action to take

    Raises:
        ValueError: If amount is negative or method is invalid
        ValidationError: If bank details are missing

    Example:
        >>> result = process_payment(1500.0, 'debicheck', userdata)
        >>> print(result['success'])
        True
    """
    pass
```

**Class Documentation:**

```python
@dataclass
class PaymentArrangement:
    """Payment arrangement details for debt collection.

    This dataclass represents a negotiated payment arrangement,
    including amount, schedule, method, and discount information.

    Attributes:
        amount: Payment amount in Rands
        date: Payment date (ISO format YYYY-MM-DD)
        method: Payment method identifier
        discount_applied: Whether discount was applied
        discount_percentage: Discount percentage (0-100)

    Example:
        >>> arrangement = PaymentArrangement(
        ...     amount=1500.0,
        ...     date="2025-01-15",
        ...     method="debicheck"
        ... )
    """
    amount: float
    date: str
    method: str
    discount_applied: bool = False
    discount_percentage: float = 0.0
```

### README Files

Each subdirectory should have a README.md explaining:

1. **Purpose:** What this directory contains
2. **Structure:** Organization of files
3. **Usage:** How to use the components
4. **Examples:** Code examples showing usage

**Example:**

```markdown
# Tools Package

## Purpose

Contains all function tools used by agents in the debt collection workflow.
Tools are organized by agent phase and registered in the central TOOL_REGISTRY.

## Structure

- `common_tools.py` - Cross-agent tools (callbacks, escalation, handoffs)
- `tool01_introduction.py` - Identity confirmation tools
- `tool02_verification.py` - POPI verification tools
- `tool03_negotiation.py` - Payment arrangement tools
- `tool04_payment.py` - Payment processing tools
- `tool05_closing.py` - Call closure tools

## Adding New Tools

1. Create function with `@function_tool` decorator
2. Register in `TOOL_REGISTRY`
3. Add to agent configuration in `agent.yaml`
4. Create test cases in `testcases/`

## Example

\`\`\`python
from livekit.agents import function_tool
from shared_state import UserData

@function_tool
async def my_new_tool(
    ctx: RunContext[UserData],
    param1: str,
    param2: int
) -> str:
    """Tool description for LLM.

    Args:
        param1: Description of param1
        param2: Description of param2
    """
    # Implementation
    return "Result"
\`\`\`
```

---

## Pull Request Process

### Before Creating PR

1. **Code Quality:**
   - [ ] Code follows style guidelines
   - [ ] No linting errors (`flake8` or `pylint`)
   - [ ] Type hints added for all functions
   - [ ] Docstrings added for all public functions/classes

2. **Testing:**
   - [ ] All tests pass locally
   - [ ] New tests added for new features
   - [ ] Test coverage maintained or improved
   - [ ] Manual testing completed

3. **Documentation:**
   - [ ] README updated if needed
   - [ ] Docstrings complete and accurate
   - [ ] CLAUDE.md updated if architecture changed
   - [ ] CHANGELOG updated with changes

4. **Cleanup:**
   - [ ] No debugging code (print statements, commented code)
   - [ ] No hardcoded values (use config or constants)
   - [ ] No unused imports or variables
   - [ ] Git history clean (squash WIP commits)

### Creating the PR

1. **Branch Naming:**
   ```
   feature/add-new-agent
   fix/verification-bug
   refactor/discount-calculator
   docs/update-architecture
   ```

2. **PR Title:**
   ```
   Clear, concise description of change

   Examples:
   - Add Cancellation Agent for subscription cancellations
   - Fix fuzzy matching threshold for voice input
   - Refactor discount calculation to use tiered system
   - Update deployment documentation with K8s examples
   ```

3. **PR Description Template:**
   ```markdown
   ## Summary

   Brief description of what this PR does and why.

   ## Changes

   - Change 1
   - Change 2
   - Change 3

   ## Testing

   - [ ] Unit tests added/updated
   - [ ] Integration tests added/updated
   - [ ] Manual testing completed

   ## Checklist

   - [ ] Code follows style guidelines
   - [ ] Tests pass locally
   - [ ] Documentation updated
   - [ ] No breaking changes (or documented if necessary)

   ## Related Issues

   Closes #123
   Fixes #456
   ```

### PR Review Process

**For Authors:**
1. Respond to all review comments
2. Make requested changes or provide justification
3. Mark conversations as resolved once addressed
4. Request re-review after changes

**For Reviewers:**
1. Review code within 24 hours
2. Provide constructive feedback
3. Approve if changes look good
4. Request changes if issues found

**Review Checklist:**
- [ ] Code is readable and maintainable
- [ ] Logic is correct and handles edge cases
- [ ] Error handling is appropriate
- [ ] Tests are comprehensive
- [ ] Documentation is clear
- [ ] No security vulnerabilities
- [ ] Performance is acceptable
- [ ] No unnecessary complexity

### Merging

**Requirements:**
- At least 1 approval from maintainer
- All tests passing (CI/CD)
- No merge conflicts
- Branch up to date with main

**Merge Strategy:**
- Use "Squash and merge" for feature branches
- Use "Rebase and merge" for hotfixes
- Delete branch after merge

---

## Git Workflow

### Branching Strategy

```
main (production-ready code)
  ├── develop (integration branch)
  │   ├── feature/new-feature
  │   ├── fix/bug-fix
  │   └── refactor/code-improvement
  └── hotfix/critical-fix
```

### Commit Messages

Follow **Conventional Commits** format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code refactoring
- `docs`: Documentation changes
- `test`: Test additions/changes
- `chore`: Build process, dependencies, etc.
- `perf`: Performance improvements
- `style`: Code style changes (formatting)

**Examples:**
```
feat(negotiation): Add two-tier discount for recently_suspended_120

Implement two-tier discount structure (50% settlement OR 40% installment)
with campaign deadline calculation for recently suspended accounts.

Closes #234

---

fix(verification): Correct fuzzy matching threshold for ID numbers

Lower fuzzy matching threshold from 0.9 to 0.8 to account for voice
input variations in ID number verification.

Fixes #456

---

docs(architecture): Update component diagrams with mermaid

Replace text-based diagrams with mermaid diagrams for better
visualization and maintainability.
```

### Commit Frequency

- **Commit often:** Small, logical commits are better than large monolithic ones
- **One change per commit:** Each commit should represent one logical change
- **Working code:** Each commit should leave the codebase in a working state

---

## Code Review Guidelines

### What to Look For

**1. Correctness:**
- Does the code do what it's supposed to do?
- Are edge cases handled?
- Are there any logical errors?

**2. Clarity:**
- Is the code easy to understand?
- Are variable/function names descriptive?
- Is the logic straightforward?

**3. Consistency:**
- Does it follow project conventions?
- Is the style consistent with existing code?
- Are naming patterns followed?

**4. Efficiency:**
- Are there obvious performance issues?
- Can anything be simplified?
- Are there unnecessary computations?

**5. Safety:**
- Is input validated?
- Are errors handled properly?
- Are there security vulnerabilities?

### Providing Feedback

**Good Feedback:**
```
"Consider extracting this logic into a separate function for reusability:

```python
def calculate_monthly_payment(total: float, months: int) -> float:
    return total / months
```

This would make the code more testable and easier to maintain."
```

**Avoid:**
```
"This is wrong."
"Why did you do it this way?"
```

**Instead:**
```
"I think there might be an issue here. If `months` is 0, this will raise a ZeroDivisionError. Should we add validation?"

"Could you explain the reasoning behind this approach? I'm wondering if we could simplify it by..."
```

### Responding to Feedback

**Good Response:**
```
"Good catch! I've added validation to check for zero months and raise ValueError with a descriptive message. Updated in commit abc1234."
```

**If Disagreeing:**
```
"I understand your concern. I chose this approach because [reasoning]. However, I'm open to alternatives. What do you think about [alternative approach]?"
```

---

## Release Process

### Version Numbering

Follow **Semantic Versioning** (semver):

```
MAJOR.MINOR.PATCH

Example: 1.2.3

MAJOR: Breaking changes
MINOR: New features (backward compatible)
PATCH: Bug fixes (backward compatible)
```

### Pre-Release Checklist

- [ ] All tests passing
- [ ] Documentation updated
- [ ] CHANGELOG updated
- [ ] Version number incremented
- [ ] Release notes drafted
- [ ] Security audit completed
- [ ] Performance benchmarks run
- [ ] Backward compatibility verified

### Release Steps

1. **Create release branch:**
   ```bash
   git checkout -b release/v1.2.0
   ```

2. **Update version numbers:**
   - `__version__` in relevant files
   - Documentation references
   - CHANGELOG.md

3. **Final testing:**
   ```bash
   python run_tests.py
   ```

4. **Create release commit:**
   ```bash
   git commit -m "chore: Bump version to 1.2.0"
   ```

5. **Merge to main:**
   ```bash
   git checkout main
   git merge release/v1.2.0
   ```

6. **Create tag:**
   ```bash
   git tag -a v1.2.0 -m "Release version 1.2.0"
   git push origin v1.2.0
   ```

7. **Publish release notes** on GitHub

---

## Getting Help

### Communication Channels

- **Issues:** Report bugs or request features via GitHub Issues
- **Discussions:** Ask questions in GitHub Discussions
- **Code Review:** Request review in pull requests
- **Documentation:** Check CLAUDE.md and docs/ directory

### Issue Templates

**Bug Report:**
```markdown
## Bug Description

Clear description of the bug

## Steps to Reproduce

1. Step 1
2. Step 2
3. Step 3

## Expected Behavior

What should happen

## Actual Behavior

What actually happens

## Environment

- Python version:
- LiveKit SDK version:
- OS:

## Logs

```
Relevant log output
```
```

**Feature Request:**
```markdown
## Feature Description

Clear description of the proposed feature

## Use Case

Why is this feature needed?

## Proposed Solution

How should this be implemented?

## Alternatives Considered

Other approaches considered

## Additional Context

Any other relevant information
```

---

## Contributor License Agreement

By contributing to this project, you agree that your contributions will be licensed under the same license as the project.
