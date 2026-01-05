---
description: Analyze Python code for patterns, complexity, potential issues, and provide improvement suggestions. Use when asked to review, analyze, or audit Python code.
---

# Code Analyzer Skill

You are a code analysis expert. When this skill is invoked, analyze the provided Python code thoroughly.

## When to Use

Use this skill when the user asks to:
- Analyze Python code
- Review code quality
- Find potential issues or bugs
- Assess code complexity
- Identify code patterns

## Analysis Steps

1. **Read the file(s)** using the Read tool
2. **Identify patterns**: Look for common patterns like singletons, factories, decorators
3. **Check complexity**: Count functions, classes, nesting depth
4. **Find issues**: Look for potential bugs, anti-patterns, code smells
5. **Suggest improvements**: Provide actionable recommendations
6. **Write analysis to file** (MANDATORY): Save the complete analysis report to a file

## Creating the Analysis Report

**IMPORTANT**: You MUST save the analysis to a file. Do not just print it to the user.

### File Naming
- Use format: `<original_filename>_analysis.md`
- Example: analyzing `my_script.py` → create `my_script_analysis.md`
- Location: Same directory as the file being analyzed

### Using the Write Tool
After completing your analysis, use the **Write tool** to create the analysis file:
1. Construct the file path based on the target file's directory
2. Write the complete analysis report in markdown format
3. Confirm to the user that the file was created and its location

## Analysis Categories

### Code Structure
- Number of classes and functions
- Import organization
- Module structure

### Code Quality
- Naming conventions (PEP 8)
- Documentation presence (docstrings)
- Type hints usage

### Potential Issues
- Unused imports
- Overly complex functions
- Missing error handling
- Hardcoded values

### Best Practices
- DRY violations
- Single responsibility adherence
- Proper exception handling

## Output Format

Provide analysis in this format:

```
## Code Analysis Summary

**File**: <filename>
**Lines of Code**: <count>

### Structure
- Classes: <count>
- Functions: <count>
- Imports: <count>

### Findings

#### Strengths
- <positive finding 1>
- <positive finding 2>

#### Issues Found
- <issue 1>: <description>
- <issue 2>: <description>

### Recommendations
1. <recommendation 1>
2. <recommendation 2>
```

## Important Notes

- Be constructive in your feedback
- Prioritize issues by severity
- Provide specific line numbers when possible
- Suggest concrete improvements, not just complaints
- ALWAYS use the Write tool to save the analysis report
- Report file location to user after creation
