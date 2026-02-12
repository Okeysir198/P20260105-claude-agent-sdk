"""Permission hooks for controlling agent tool access.

This module provides pre-tool-use hooks for restricting file operations and
bash commands to specific directories, enhancing security when using the
Claude Agent SDK.

The hooks implement a whitelist-based security model where:
- Read operations are always allowed (safe, read-only)
- Write/Edit operations are restricted to allowed directories
- Bash commands can be filtered by command patterns
- Bash file redirections can be controlled

Additionally provides an AskUserQuestion normalization hook that fixes
malformed input from the model/provider where the `questions` field is
sent as a JSON string instead of an array.

Typical usage:
    from agent.core.hook import create_permission_hook, create_ask_user_question_hook
    from claude_agent_sdk import ClaudeAgentOptions

    hook = create_permission_hook(
        allowed_directories=["/path/to/project", "/tmp"]
    )
    ask_hook = create_ask_user_question_hook()

    options = ClaudeAgentOptions(
        hooks={'PreToolUse': [ask_hook, hook]}
    )
"""
import json
import logging
import re
from typing import Any

from claude_agent_sdk import HookMatcher

logger = logging.getLogger(__name__)


# Default bash commands that are blocked for safety.
# These commands modify the filesystem and should use Write/Edit tools instead.
DEFAULT_BLOCKED_COMMANDS = [
    "rm ",      # Remove files/directories
    "mv ",      # Move/rename files
    "cp ",      # Copy files
    "mkdir ",   # Create directories
    "rmdir ",   # Remove directories
    "touch ",   # Create/modify file timestamps
]

# Extended list for strict sandbox mode - includes network operations
SANDBOX_BLOCKED_COMMANDS = DEFAULT_BLOCKED_COMMANDS + [
    "wget ",    # Download files from web
    "curl ",    # Transfer data (can write files)
]


def create_ask_user_question_hook() -> HookMatcher:
    """Create a pre-tool-use hook to normalize AskUserQuestion input.

    The model/provider sometimes sends the `questions` field as a JSON string
    instead of an array, e.g.:
        "questions": "\\n[{\\"question\\": ...}]"

    This causes the CLI to fail input validation before the can_use_tool
    callback is ever invoked. This hook intercepts the tool call at the
    PreToolUse stage and normalizes the questions field to an array.

    Returns:
        HookMatcher: A configured hook matcher for PreToolUse events.

    Example:
        ```python
        from agent.core.hook import create_ask_user_question_hook

        hook = create_ask_user_question_hook()
        options = ClaudeAgentOptions(
            hooks={'PreToolUse': [hook]}
        )
        ```
    """

    async def normalize_ask_user_question(
        input_data: dict[str, Any],
        _tool_use_id: str | None,
        _context: Any,
    ) -> dict[str, Any]:
        """Normalize AskUserQuestion tool input before execution.

        If the tool is AskUserQuestion and the `questions` field is a string,
        attempt to parse it as JSON and update the input with the parsed array.

        For all other tools, passes through without modification.

        Args:
            input_data: Dictionary containing:
                - tool_name: Name of the tool being invoked
                - tool_input: Parameters passed to the tool
            _tool_use_id: Unique identifier for this tool use (unused)
            _context: Execution context (unused)

        Returns:
            Empty dict to pass through, or dict with hookSpecificOutput
            containing updatedInput to fix the questions field.
        """
        tool_name = input_data.get('tool_name', '')
        logger.info(
            "[PreToolUse Hook] normalize_ask_user_question called: tool_name=%s, tool_use_id=%s",
            tool_name, _tool_use_id
        )

        # Only intercept AskUserQuestion
        if tool_name != "AskUserQuestion":
            return {}

        tool_input = input_data.get('tool_input', {})
        questions = tool_input.get('questions')

        # If questions is already a list (correct format), pass through
        if isinstance(questions, list):
            logger.debug(
                "AskUserQuestion hook: questions is already a list with %d items",
                len(questions)
            )
            return {}

        # If questions is a string, try to parse it as JSON
        if isinstance(questions, str):
            logger.info(
                "AskUserQuestion hook: questions is a string, attempting JSON parse. "
                "Raw value (first 200 chars): %s",
                questions[:200]
            )
            parsed = _parse_questions_string(questions)
            if parsed is not None:
                logger.info(
                    "AskUserQuestion hook: successfully parsed questions string into list with %d items",
                    len(parsed)
                )
                # Build updated input with parsed questions
                updated_input = {**tool_input, "questions": parsed}
                return {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "allow",
                        "updatedInput": updated_input,
                    }
                }
            else:
                logger.warning(
                    "AskUserQuestion hook: failed to parse questions string as JSON, "
                    "passing through unchanged"
                )
                return {}

        # If questions is None or unexpected type, pass through and let
        # downstream validation handle it
        logger.warning(
            "AskUserQuestion hook: questions field has unexpected type %s, passing through",
            type(questions).__name__
        )
        return {}

    return HookMatcher(hooks=[normalize_ask_user_question])  # type: ignore[list-item]


def _parse_questions_string(raw: str) -> list[dict[str, Any]] | None:
    """Attempt to parse a questions string into a list of question dicts.

    Handles common malformed formats:
    - Direct JSON array: '[{"question": "..."}]'
    - Whitespace-prefixed: '\\n[{"question": "..."}]'
    - Wrapped in extra quotes

    Args:
        raw: The raw string value of the questions field.

    Returns:
        Parsed list of question dicts, or None if parsing fails.
    """
    if not raw or not raw.strip():
        logger.debug("_parse_questions_string: empty or whitespace-only string")
        return None

    stripped = raw.strip()

    # Try direct JSON parse
    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, list):
            return parsed
        logger.warning(
            "_parse_questions_string: parsed JSON is not a list, got %s",
            type(parsed).__name__
        )
        return None
    except (json.JSONDecodeError, TypeError) as e:
        logger.debug("_parse_questions_string: direct JSON parse failed: %s", e)

    # Try unwrapping extra string escaping (double-encoded JSON)
    try:
        unwrapped = json.loads(f'"{stripped}"') if not stripped.startswith('"') else json.loads(stripped)
        if isinstance(unwrapped, str):
            inner_parsed = json.loads(unwrapped)
            if isinstance(inner_parsed, list):
                logger.info("_parse_questions_string: successfully parsed double-encoded JSON")
                return inner_parsed
    except (json.JSONDecodeError, TypeError):
        pass

    logger.warning("_parse_questions_string: all parse attempts failed for string (first 200 chars): %s", stripped[:200])
    return None


def create_permission_hook(
    allowed_directories: list[str] | None = None,
    block_bash_commands: list[str] | None = None,
    allow_bash_redirection: bool = False,
) -> HookMatcher:
    """Create a pre-tool-use hook for controlling agent permissions.

    This function creates a hook that intercepts tool calls before execution
    and applies security restrictions. The hook is designed to be composable
    with other hooks in the Claude Agent SDK.

    Security Model:
        - Whitelist: Only directories in allowed_directories permit writes
        - Read-only: Read tool is always permitted (safe operation)
        - Command filtering: Specific bash command patterns can be blocked
        - Redirection control: Bash > and >> operators can be restricted

    Args:
        allowed_directories: List of absolute directory paths where file
            operations (Write, Edit) are permitted. Paths are matched using
            startswith(), so "/home/user/project" allows writes to any file
            under that directory tree.
            Defaults to [PROJECT_ROOT, "/tmp"] for convenience.

        block_bash_commands: List of bash command prefixes to block.
            Each string is matched against the beginning of command tokens.
            For example, "rm " blocks "rm file.txt" but not "rm" as a
            standalone word in a larger command.
            Defaults to ["rm ", "mv ", "cp ", "mkdir ", "rmdir ", "touch "].

        allow_bash_redirection: Controls bash output redirection (>, >>).
            When False (default), redirections are only allowed to:
            - /dev/null, /dev/zero, etc. (device files)
            - Files within allowed_directories
            When True, all redirections are permitted.

    Returns:
        HookMatcher: A configured hook matcher for PreToolUse events that
        can be passed to ClaudeAgentOptions.

    Example - Basic usage with project directory:
        ```python
        from agent.core.hook import create_permission_hook

        hook = create_permission_hook(
            allowed_directories=["/home/user/myproject", "/tmp"]
        )
        ```

    Example - Custom command blocking:
        ```python
        hook = create_permission_hook(
            allowed_directories=["/safe/dir"],
            block_bash_commands=["rm ", "mv ", "dd ", "mkfs "]
        )
        ```

    Example - Allow bash redirection:
        ```python
        hook = create_permission_hook(
            allowed_directories=["/workspace"],
            allow_bash_redirection=True
        )
        ```

    Note:
        When using agents with `with_permissions: true` in agents.yaml, this hook
        is automatically configured with sensible defaults based on the
        agent's cwd and allowed_directories.
    """
    from agent import PROJECT_ROOT

    # Apply default allowed directories if not specified
    # Default provides safe access to project files and temporary storage
    if allowed_directories is None:
        allowed_directories = [str(PROJECT_ROOT), "/tmp"]

    # Apply default blocked commands if not specified
    if block_bash_commands is None:
        block_bash_commands = DEFAULT_BLOCKED_COMMANDS.copy()

    async def pre_tool_use_hook(
        input_data: dict[str, Any],
        _tool_use_id: str | None,
        _context: Any,
    ) -> dict[str, Any]:
        """Validate and control tool execution before it runs.

        This is the actual hook function that gets called for each tool use.
        It inspects the tool name and input, then returns either an empty
        dict (allow) or a dict with 'decision' and 'systemMessage' (block).

        Args:
            input_data: Dictionary containing:
                - tool_name: Name of the tool being invoked
                - tool_input: Parameters passed to the tool
            _tool_use_id: Unique identifier for this tool use (unused)
            _context: Execution context (unused)

        Returns:
            Empty dict to allow the tool, or dict with:
                - decision: "block" to prevent execution
                - systemMessage: Explanation shown to the agent
        """
        tool_name = input_data.get('tool_name', '')
        tool_input = input_data.get('tool_input', {})

        # Read operations are always safe - no restrictions
        if tool_name == "Read":
            return {}

        # Check Write and Edit operations against allowed directories
        if tool_name in ["Write", "Edit"]:
            file_path = tool_input.get("file_path", "")

            # Allow if the file path starts with any allowed directory
            for allowed_dir in allowed_directories:
                # Normalize with trailing / to prevent prefix confusion
                # e.g., /data/admin/files/ should not match /data/admin/files_evil/
                normalized_dir = allowed_dir if allowed_dir.endswith('/') else allowed_dir + '/'
                if file_path.startswith(normalized_dir) or file_path == allowed_dir.rstrip('/'):
                    return {}

            # Block writes outside allowed directories
            return {
                'decision': 'block',
                'systemMessage': (
                    f'Write/Edit access denied: {file_path}\n'
                    f'Allowed directories: {", ".join(allowed_directories)}'
                )
            }

        # Check Bash commands for dangerous operations
        if tool_name == "Bash":
            command = tool_input.get("command", "")

            # Check for blocked command patterns
            for pattern in block_bash_commands:
                if pattern in command:
                    return {
                        'decision': 'block',
                        'systemMessage': (
                            f'Bash command blocked: {command}\n'
                            f'Blocked patterns: {", ".join(block_bash_commands)}\n'
                            f'Use Write/Edit tools for file operations.'
                        )
                    }

            # Check for file redirection if not allowed
            if not allow_bash_redirection:
                # Pattern matches: > file, >> file, with optional whitespace
                redirect_pattern = r'(?:>\s?|\>\>\s?)([^\s&|;]+)'
                redirected_files = re.findall(redirect_pattern, command)

                for file_path in redirected_files:
                    # Strip quotes from the path
                    file_path = file_path.strip('"').strip("'")

                    # Always allow redirection to device files (/dev/null, etc.)
                    if file_path.startswith("/dev/"):
                        continue

                    # Check if the file is within allowed directories
                    # Normalize with trailing / for safe prefix matching
                    is_allowed = any(
                        file_path.startswith(
                            allowed_dir if allowed_dir.endswith('/') else allowed_dir + '/'
                        )
                        for allowed_dir in allowed_directories
                    )

                    if not is_allowed:
                        return {
                            'decision': 'block',
                            'systemMessage': (
                                f'Bash redirection denied: {file_path}\n'
                                f'Can only redirect to: {", ".join(allowed_directories)}'
                            )
                        }

            # Allow the bash command
            return {}

        # Allow all other tools (Grep, Glob, Task, Skill, WebSearch, etc.)
        # These tools are either read-only or have their own safety measures
        return {}

    return HookMatcher(hooks=[pre_tool_use_hook])  # type: ignore[list-item]


def create_sandbox_hook(
    sandbox_dir: str,
    additional_allowed_dirs: list[str] | None = None,
) -> HookMatcher:
    """Create a strict sandbox hook for maximum security.

    This is a convenience wrapper around create_permission_hook that creates
    a more restrictive environment suitable for untrusted operations. It
    blocks additional commands like wget and curl that could download
    arbitrary content.

    Use Cases:
        - Running untrusted code or scripts
        - Sandboxed test environments
        - Limited access for specific agent tasks
        - Evaluation/testing scenarios

    Args:
        sandbox_dir: The primary sandbox directory where all file operations
            are allowed. This should be an absolute path to an isolated
            directory.

        additional_allowed_dirs: Optional list of additional directories to
            allow access to. Common use case is adding "/tmp" for temporary
            file operations.

    Returns:
        HookMatcher: A configured hook matcher with strict sandbox settings.

    Example - Basic sandbox:
        ```python
        hook = create_sandbox_hook(sandbox_dir="/sandbox/workspace")
        ```

    Example - Sandbox with temp access:
        ```python
        hook = create_sandbox_hook(
            sandbox_dir="/sandbox/workspace",
            additional_allowed_dirs=["/tmp"]
        )
        ```

    Example - Project-relative sandbox:
        ```python
        from agent import PROJECT_ROOT

        hook = create_sandbox_hook(
            sandbox_dir=str(PROJECT_ROOT / "tests" / "sandbox"),
            additional_allowed_dirs=["/tmp"]
        )
        ```
    """
    allowed_dirs = [sandbox_dir]
    if additional_allowed_dirs:
        allowed_dirs.extend(additional_allowed_dirs)

    return create_permission_hook(
        allowed_directories=allowed_dirs,
        block_bash_commands=SANDBOX_BLOCKED_COMMANDS,
        allow_bash_redirection=False
    )


def get_permission_info() -> str:
    """Get information about permission hooks and their usage.

    Provides a formatted help text describing the available permission hooks,
    their configuration options, and usage examples. Useful for documentation
    or interactive help systems.

    Returns:
        Formatted string with hook documentation.
    """
    return """
Permission Hooks Module
=======================

This module provides hooks for controlling agent tool access, implementing
a whitelist-based security model for file and command operations.

Available Hooks
---------------

1. create_permission_hook()
   Configurable permission hook with fine-grained control:
   - allowed_directories: List of paths where writes are permitted
   - block_bash_commands: List of command prefixes to block
   - allow_bash_redirection: Control > and >> operators

2. create_sandbox_hook()
   Convenience function for strict sandbox environments:
   - Single primary sandbox directory
   - Blocks additional commands (wget, curl)
   - No bash redirection outside sandbox

Usage Examples
--------------

Example 1: Restrict to project and temp directories
    from agent.core.hook import create_permission_hook
    from claude_agent_sdk import ClaudeAgentOptions

    hook = create_permission_hook(
        allowed_directories=["/path/to/project", "/tmp"]
    )

    options = ClaudeAgentOptions(
        hooks={'PreToolUse': [hook]}
    )

Example 2: Strict sandbox mode
    from agent.core.hook import create_sandbox_hook

    hook = create_sandbox_hook(
        sandbox_dir="/path/to/sandbox",
        additional_allowed_dirs=["/tmp"]
    )

Example 3: Custom bash command blocking
    hook = create_permission_hook(
        allowed_directories=["/safe/dir"],
        block_bash_commands=["rm ", "mv ", "dd ", "mkfs "]
    )

Security Features
-----------------
- Blocks Write/Edit outside allowed directories
- Blocks configurable bash commands (rm, mv, cp, mkdir, touch by default)
- Blocks bash redirection to files outside allowed directories
- Always allows Read operations (safe, read-only access)
- Allows safe bash commands (ls, cat, grep, echo, pwd, cd, etc.)

Default Blocked Commands
------------------------
- rm: Remove files/directories
- mv: Move/rename files
- cp: Copy files
- mkdir: Create directories
- rmdir: Remove directories
- touch: Create/modify file timestamps

Additional Sandbox Blocked Commands
-----------------------------------
- wget: Download files from web
- curl: Transfer data (can write files)
"""
