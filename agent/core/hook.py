"""Permission hooks for controlling agent tool access.

Provides pre-tool-use hooks for restricting file operations and bash commands
to specific directories, enhancing security when using the Claude Agent SDK.
"""
import re
from typing import Any

from claude_agent_sdk import HookMatcher


def create_permission_hook(
    allowed_directories: list[str] | None = None,
    block_bash_commands: list[str] | None = None,
    allow_bash_redirection: bool = False,
) -> HookMatcher:
    """Create a pre-tool-use hook for controlling agent permissions.

    This hook restricts:
    - Write/Edit operations to allowed directories only
    - Bash file manipulation commands (rm, mv, cp, mkdir, touch)
    - Bash redirections to files outside allowed directories

    Args:
        allowed_directories: List of directories where file operations are allowed.
            Defaults to [current working directory, "/tmp"] for convenience.
        block_bash_commands: List of bash command patterns to block.
            Defaults to ["rm ", "mv ", "cp ", "mkdir ", "rmdir ", "touch "].
        allow_bash_redirection: Whether to allow bash redirection (>, >>) to files.
            When False, redirects are only allowed to /dev/null.

    Returns:
        Configured HookMatcher for PreToolUse events.

    Example:
        ```python
        from agent import PROJECT_ROOT

        # Default: allows cwd and /tmp
        hook = create_permission_hook()

        # Custom: specific directories
        hook = create_permission_hook(
            allowed_directories=[str(PROJECT_ROOT / "tests"), "/tmp"],
            block_bash_commands=["rm ", "mv ", "cp "]
        )

        # Use with SDK options
        options = ClaudeAgentOptions(
            hooks={'PreToolUse': [hook]}
        )
        ```

    Note:
        When called via `create_enhanced_options(with_permissions=True)`,
        the default automatically uses the option's cwd and /tmp.
    """
    from agent import PROJECT_ROOT

    if allowed_directories is None:
        # Default to project root (current working directory) and /tmp
        # This provides a safe default that allows working in the project
        # while preventing writes to system directories
        allowed_directories = [str(PROJECT_ROOT), "/tmp"]

    if block_bash_commands is None:
        block_bash_commands = ["rm ", "mv ", "cp ", "mkdir ", "rmdir ", "touch "]

    async def pre_tool_use_hook(
        input_data: dict[str, Any],  # type: ignore[no-any-unimported]
        _tool_use_id: str | None,
        _context: Any,  # type: ignore[no-any-unimported]
    ) -> dict[str, Any]:
        """Hook to validate and control tool execution before it runs."""
        tool_name = input_data.get('tool_name', '')
        tool_input = input_data.get('tool_input', {})

        # Always allow read operations
        if tool_name == "Read":
            return {}

        # Check file write operations
        if tool_name in ["Write", "Edit"]:
            file_path = tool_input.get("file_path", "")

            # Allow if in any of the allowed directories
            if any(file_path.startswith(allowed_dir) for allowed_dir in allowed_directories):
                return {}

            # Block writes outside allowed directories
            return {
                'decision': 'block',
                'systemMessage': (
                    f'❌ Write/Edit access denied: {file_path}\n'
                    f'Allowed directories: {", ".join(allowed_directories)}'
                )
            }

        # For bash commands, check for dangerous operations
        if tool_name == "Bash":
            command = tool_input.get("command", "")

            # Block file manipulation commands
            if any(pattern in command for pattern in block_bash_commands):
                return {
                    'decision': 'block',
                    'systemMessage': (
                        f'❌ Bash command blocked: {command}\n'
                        f'Blocked commands: {", ".join(block_bash_commands)}\n'
                        f'Use Write/Edit tools for file operations.'
                    )
                }

            # Check for file redirection patterns (>, >>) that write files
            if not allow_bash_redirection:
                redirect_pattern = r'(?:>\s?|\>\>\s?)([^\s&|;]+)'
                redirected_files = re.findall(redirect_pattern, command)

                if redirected_files:
                    for file_path in redirected_files:
                        # Remove quotes if present
                        file_path = file_path.strip('"').strip("'")

                        # Allow /dev/null (common for error redirection)
                        if file_path.startswith("/dev/"):
                            continue

                        # Check if file is in allowed directories
                        if not any(file_path.startswith(allowed_dir) for allowed_dir in allowed_directories):
                            return {
                                'decision': 'block',
                                'systemMessage': (
                                    f'❌ Bash redirection denied: {file_path}\n'
                                    f'Can only redirect to: {", ".join(allowed_directories)}'
                                )
                            }

            # Allow other bash commands
            return {}

        # Allow all other tools (Grep, Glob, Task, Skill, etc.)
        return {}

    return HookMatcher(hooks=[pre_tool_use_hook])  # type: ignore[list-item]


def create_sandbox_hook(
    sandbox_dir: str,
    additional_allowed_dirs: list[str] | None = None,
) -> HookMatcher:
    """Create a strict sandbox hook for maximum security.

    This is a convenience function that creates a permission hook with
    a single sandbox directory and optional additional directories.

    Args:
        sandbox_dir: The primary sandbox directory for all operations.
        additional_allowed_dirs: Optional list of additional directories to allow.

    Returns:
        Configured HookMatcher for PreToolUse events.

    Example:
        ```python
        from agent import PROJECT_ROOT

        # Create sandbox in tests directory only
        hook = create_sandbox_hook(
            sandbox_dir=str(PROJECT_ROOT / "tests"),
            additional_allowed_dirs=["/tmp"]
        )
        ```
    """
    allowed_dirs = [sandbox_dir]
    if additional_allowed_dirs:
        allowed_dirs.extend(additional_allowed_dirs)

    return create_permission_hook(
        allowed_directories=allowed_dirs,
        block_bash_commands=["rm ", "mv ", "cp ", "mkdir ", "rmdir ", "touch ", "wget ", "curl "],
        allow_bash_redirection=False
    )


def get_permission_info() -> str:
    """Get information about permission hooks and their usage.

    Returns:
        String describing available permission hooks and their configuration.
    """
    return """
Permission Hooks Module
======================

This module provides hooks for controlling agent tool access:

1. create_permission_hook()
   - Configure allowed directories for file operations
   - Block dangerous bash commands
   - Control bash redirection behavior

2. create_sandbox_hook()
   - Create a strict sandbox with a single directory
   - Maximum security for untrusted operations

Usage Examples:
--------------

Example 1: Restrict to tests directory and /tmp
    from agent.core.hook import create_permission_hook
    from claude_agent_sdk import ClaudeAgentOptions

    hook = create_permission_hook(
        allowed_directories=["/path/to/tests", "/tmp"]
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
        block_bash_commands=["rm ", "mv ", "dd ", "mkfs"]
    )

Security Features:
-----------------
✓ Blocks Write/Edit outside allowed directories
✓ Blocks dangerous bash commands (rm, mv, cp, mkdir, touch)
✓ Blocks bash redirection to files outside allowed dirs
✓ Always allows Read operations anywhere (read-only access)
✓ Allows safe bash commands (ls, cat, grep, echo, pwd, cd)
"""
