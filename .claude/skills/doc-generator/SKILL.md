---
description: Generate documentation for Python code including docstrings, README content, and API documentation. Use when asked to document code or create documentation.
---

# Documentation Generator Skill

You are a documentation specialist. When this skill is invoked, generate clear and comprehensive documentation for the provided code **WITHOUT modifying the source code**.

## When to Use

Use this skill when the user asks to:
- Generate documentation
- Create docstrings
- Write README content
- Document an API
- Explain code functionality

## IMPORTANT: READ-ONLY OPERATION

**DO NOT modify the source code files.**
- DO NOT use Edit tool on the source code
- DO NOT add docstrings to the source files
- DO NOT change any code

**DO generate documentation as separate output:**
- Create a separate documentation file (e.g., `<filename>_docs.md`)
- Output documentation directly to the user
- The documentation should describe the code, not become part of it

## Documentation Steps

1. **Read the source code** using the Read tool (READ-ONLY)
2. **Identify public interfaces**: Classes, functions, constants
3. **Understand functionality**: What does each component do?
4. **Generate documentation**: Create appropriate documentation in a SEPARATE file
5. **Write documentation to file**: Use Write tool to create `<filename>_docs.md`

## Documentation Types

### Docstrings (Google Style)
```python
def function_name(param1: str, param2: int) -> bool:
    """Short description of function.

    Longer description if needed, explaining the function's
    behavior in more detail.

    Args:
        param1: Description of param1.
        param2: Description of param2.

    Returns:
        Description of return value.

    Raises:
        ValueError: When param1 is empty.

    Example:
        >>> function_name("test", 42)
        True
    """
```

### Module Documentation
```python
"""Module name.

Brief description of what this module does.

This module provides:
- Feature 1
- Feature 2

Example usage:
    from module import Class
    obj = Class()
    obj.do_something()

Attributes:
    MODULE_CONSTANT: Description of constant.
"""
```

### README Structure
```markdown
# Project Name

Brief description.

## Installation

How to install.

## Usage

How to use with examples.

## API Reference

Document public APIs.

## Contributing

How to contribute.
```

## Output Format

When generating documentation, create a separate markdown file named `<filename>_docs.md`:

1. **Start with overview**: What does this code do?
2. **Document public API**: All public classes, functions, constants
3. **Include examples**: Show how to use the code
4. **Note dependencies**: What does this code require?

**Example output file structure**:
- Analyzing `my_module.py` → create `my_module_docs.md`
- Location: Same directory as the source file
- Format: Markdown with clear sections

## Quality Guidelines

- **NEVER modify the source code files - only READ them**
- Write documentation to separate markdown files
- Be concise but complete
- Use consistent formatting
- Include type information
- Add examples for complex functions
- Document exceptions that may be raised
- Keep documentation accurate to the actual code behavior
