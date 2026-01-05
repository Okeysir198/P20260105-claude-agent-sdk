#!/usr/bin/env python3
"""Subagent definitions for continuous conversation session.

Provides specialized subagents for common development tasks.
Each subagent has a specific role, system prompt, and tool access.
"""

from claude_agent_sdk import AgentDefinition


# Specialized prompts for each subagent
RESEARCHER_PROMPT = """You are a research specialist. Your role is to:

1. Find and gather relevant information from the codebase
2. Identify patterns, dependencies, and relationships
3. Summarize findings clearly and concisely
4. Provide citations (file paths, line numbers) for all findings

Focus on accuracy and completeness. Do not make assumptions about code you haven't read.
Be thorough in your exploration and provide comprehensive summaries."""


CODE_REVIEWER_PROMPT = """You are a code review specialist. Your task is to:

1. Review code for:
   - Security vulnerabilities (injection, hardcoded secrets, auth issues)
   - Performance issues (O(n^2) loops, unnecessary allocations)
   - Code quality (naming, complexity, duplication)
   - Best practices violations

2. Provide clear, actionable feedback with:
   - Severity: critical/high/medium/low
   - Location: file path and line number
   - Description: Clear explanation
   - Fix: Specific remediation steps

Be thorough but constructive. Focus on important issues first."""


FILE_ASSISTANT_PROMPT = """You are a file system assistant. Your role is to:

1. Help users navigate and explore the codebase
2. Find files by name or pattern
3. Search for content within files
4. Summarize file contents
5. Identify project structure

Be efficient and provide clear, organized results. When searching, be thorough
and check multiple potential locations."""


def create_subagents() -> dict[str, AgentDefinition]:
    """Create specialized subagents for development tasks.

    Returns:
        Dictionary mapping agent names to AgentDefinition instances.

    Available agents:
        - researcher: For code exploration and analysis
        - reviewer: For code review and quality checks
        - file_assistant: For file navigation and search
    """
    return {
        "researcher": AgentDefinition(
            description="Research specialist for finding and analyzing code. "
                       "Use for gathering information, understanding patterns, "
                       "and exploring the codebase thoroughly.",
            prompt=RESEARCHER_PROMPT,
            tools=["Skill", "Read", "Grep", "Glob"],
            model="sonnet"  # Use shorthand: sonnet, opus, or haiku
        ),

        "reviewer": AgentDefinition(
            description="Code review specialist for analyzing code quality, "
                       "security, and performance. Use for comprehensive code reviews "
                       "and identifying potential issues.",
            prompt=CODE_REVIEWER_PROMPT,
            tools=["Skill", "Read", "Grep", "Glob"],
            model="sonnet"  # Use shorthand: sonnet, opus, or haiku
        ),

        "file_assistant": AgentDefinition(
            description="File system assistant for navigating, searching, "
                       "and exploring the codebase. Use for file operations, "
                       "finding files, and understanding project structure.",
            prompt=FILE_ASSISTANT_PROMPT,
            tools=["Skill", "Read", "Grep", "Glob", "Bash"],
            model="haiku"  # Use shorthand: faster model for simple tasks
        )
    }


def get_agents_info() -> list[dict]:
    """Get agent information for display.

    Returns:
        List of dictionaries with agent name and focus description.
    """
    return [
        {"name": "researcher", "focus": "Code exploration and analysis"},
        {"name": "reviewer", "focus": "Code review and quality checks"},
        {"name": "file_assistant", "focus": "File navigation and search"}
    ]
