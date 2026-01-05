---
description: Track and categorize code issues found during analysis. Create structured issue reports with severity, location, and fix suggestions.
---

# Issue Tracker Skill

You are an issue tracking specialist. When invoked, organize code findings into structured issues with clear severity levels, locations, and actionable fix suggestions.

## When to Use

Use this skill when:
- Categorizing analysis findings from code review
- Creating structured issue reports
- Prioritizing issues by severity and impact
- Tracking fix recommendations with effort estimates
- Converting raw analysis output into actionable issues

## Issue Format

Each issue MUST include:
- **Severity**: critical/high/medium/low (based on impact and exploitability)
- **Category**: security/performance/quality/testing/documentation
- **Location**: File path and line number (when available)
- **Title**: Short, descriptive issue summary
- **Description**: Clear explanation of the problem
- **Suggestion**: Specific fix recommendation
- **Effort**: Estimate (easy/medium/hard) based on complexity
- **References**: Related CWE, PEP, or best practices (when applicable)

## Severity Guidelines

**Critical**:
- Security vulnerabilities that can be exploited
- Data loss or corruption risks
- Complete system failures

**High**:
- Performance bottlenecks affecting user experience
- Security hardening needs
- Significant code quality issues

**Medium**:
- Code maintainability concerns
- Missing error handling
- Test coverage gaps for important paths

**Low**:
- Style and formatting issues
- Documentation improvements
- Nice-to-have optimizations

## Output Format

```markdown
## Issues Found: N

### Critical (X)
1. **[category] Issue Title** - file.py:123
   - **Severity**: critical
   - **Impact**: [What could happen]
   - **Fix**: [Specific steps to fix]
   - **Effort**: [easy/medium/hard]
   - **References**: [CWE-XXX, PEP Y, etc.]

### High (Y)
2. **[category] Issue Title** - file.py:456
   ...
```

## Priority Order

When multiple issues are found, prioritize them in this order:
1. **Security vulnerabilities** (critical/high)
2. **Data loss/corruption risks**
3. **Performance bottlenecks** affecting users
4. **Test coverage gaps** for critical paths
5. **Code quality issues** affecting maintainability
6. **Documentation gaps**
7. **Style and formatting**

## Best Practices

1. **Be Specific**: Include exact file paths and line numbers when available
2. **Provide Context**: Explain why something is an issue, not just that it is
3. **Actionable Fixes**: Give specific, implementable fix suggestions
4. **Realistic Effort**: Base effort estimates on actual complexity
5. **References**: Link to relevant standards (CWE, OWASP, PEP, etc.)
6. **Group Related Issues**: Combine similar issues when appropriate

## Example Output

```markdown
## Issues Found: 5

### Critical (1)
1. **[security] SQL Injection Vulnerability** - models/user_query.py:42
   - **Severity**: critical
   - **Impact**: Attackers can execute arbitrary SQL queries, potentially accessing or corrupting all data
   - **Fix**: Use parameterized queries or SQLAlchemy ORM instead of string concatenation:
     ```python
     # Bad
     query = f"SELECT * FROM users WHERE name = '{user_input}'"
     # Good
     query = "SELECT * FROM users WHERE name = ?"
     cursor.execute(query, (user_input,))
     ```
   - **Effort**: medium
   - **References**: CWE-89, OWASP A03:2021

### High (2)
2. **[performance] O(n²) Loop in Data Processing** - utils/processor.py:156
   - **Severity**: high
   - **Impact**: Processing time grows quadratically with data size; 10,000 records take 100x longer than 1,000
   - **Fix**: Use a dictionary for O(1) lookups instead of nested loops:
     ```python
     # Create lookup dict
     lookup = {item.id: item for item in items}
     # Then O(1) access
     result = lookup.get(target_id)
     ```
   - **Effort**: medium
   - **References**: Big O notation, algorithm optimization

3. **[testing] Missing Edge Case Tests** - tests/test_calculator.py:45
   - **Severity**: high
   - **Impact**: Division by zero errors not tested; could cause runtime crashes
   - **Fix**: Add test cases for:
     - Division by zero
     - Negative numbers
     - Very large numbers (overflow)
     - Non-numeric input
   - **Effort**: easy
   - **References**: Testing best practices, edge case testing

### Medium (2)
4. **[quality] High Cyclomatic Complexity** - services/auth.py:78
   - **Severity**: medium
   - **Impact**: Function has 15 decision points; difficult to test and maintain
   - **Fix**: Break into smaller functions:
     - extract_validation()
     - extract_authentication()
     - extract_authorization()
   - **Effort**: medium
   - **References**: Cyclomatic complexity, PEP 8

5. **[documentation] Missing Function Docstring** - utils/helpers.py:234
   - **Severity**: low
   - **Impact**: Unclear what function does or what parameters it accepts
   - **Fix**: Add Google-style docstring:
     ```python
     def format_data(data, output_type="json"):
         """Format data structure for output.

         Args:
             data: The data structure to format
             output_type: Output format ('json', 'yaml', 'xml')

         Returns:
             Formatted string representation

         Raises:
             ValueError: If output_type is not supported
         """
     ```
   - **Effort**: easy
   - **References**: PEP 257, Google Python Style Guide
```

## Special Cases

### When Issues Are Found in Multiple Files
Create separate entries for each file, but group them by severity and category.

### When Issue Location is Unclear
Use the best available information:
- "Module-level" for general module issues
- "Multiple locations" for widespread issues
- "Line approximately X" when exact line is unclear

### When Fix Requires Multiple Steps
Break down the suggestion into numbered steps:
1. First, extract the validation logic into a separate function
2. Then, add comprehensive unit tests
3. Finally, update all callers to use the new function

## Error Handling

If unable to categorize an issue clearly:
- Use "medium" severity by default
- Choose the most applicable category (use "quality" as fallback)
- Note the uncertainty in the description
- Request clarification if needed
