"""Permission hooks for controlling agent tool access.

Provides pre-tool-use hooks for restricting file operations and bash commands
to specific directories, plus an AskUserQuestion normalization hook that fixes
malformed input where `questions` is sent as a JSON string instead of an array.
"""
import logging
import re
from typing import Any

from claude_agent_sdk import HookMatcher
from api.utils.questions import normalize_questions_field

logger = logging.getLogger(__name__)


DEFAULT_BLOCKED_COMMANDS = ["rm ", "mv ", "cp ", "mkdir ", "rmdir ", "touch "]

SANDBOX_BLOCKED_COMMANDS = DEFAULT_BLOCKED_COMMANDS + ["wget ", "curl "]


def create_ask_user_question_hook() -> HookMatcher:
    """Create a pre-tool-use hook to normalize AskUserQuestion input.

    The model sometimes sends the `questions` field as a JSON string instead
    of an array. This hook normalizes it before validation rejects it.
    """

    async def normalize_ask_user_question(
        input_data: dict[str, Any],
        _tool_use_id: str | None,
        _context: Any,
    ) -> dict[str, Any]:
        tool_name = input_data.get('tool_name', '')
        logger.debug("PreToolUse hook: tool_name=%s, tool_use_id=%s", tool_name, _tool_use_id)

        if tool_name != "AskUserQuestion":
            return {}

        tool_input = input_data.get('tool_input', {})
        questions = tool_input.get('questions')

        if isinstance(questions, list):
            return {}

        if isinstance(questions, str):
            logger.info("AskUserQuestion: questions is string, parsing. First 200 chars: %s", questions[:200])
            parsed = normalize_questions_field(questions, context="PreToolUse_hook")
            if parsed:
                logger.info("AskUserQuestion: parsed %d questions from string", len(parsed))
                return {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "allow",
                        "updatedInput": {**tool_input, "questions": parsed},
                    }
                }
            logger.warning("AskUserQuestion: failed to parse questions string, passing through")
            return {}

        logger.warning("AskUserQuestion: unexpected questions type %s, passing through", type(questions).__name__)
        return {}

    return HookMatcher(hooks=[normalize_ask_user_question])  # type: ignore[list-item]


def create_permission_hook(
    allowed_directories: list[str] | None = None,
    block_bash_commands: list[str] | None = None,
    allow_bash_redirection: bool = False,
) -> HookMatcher:
    """Create a pre-tool-use hook for controlling agent permissions.

    Whitelist-based security: Read is always allowed, Write/Edit restricted
    to allowed_directories, and specific bash command patterns can be blocked.

    Args:
        allowed_directories: Directories where Write/Edit are permitted.
            Defaults to [PROJECT_ROOT, "/tmp"].
        block_bash_commands: Bash command prefixes to block.
            Defaults to DEFAULT_BLOCKED_COMMANDS.
        allow_bash_redirection: Allow bash > and >> operators. Default False.
    """
    from agent import PROJECT_ROOT

    if allowed_directories is None:
        allowed_directories = [str(PROJECT_ROOT), "/tmp"]
    if block_bash_commands is None:
        block_bash_commands = DEFAULT_BLOCKED_COMMANDS.copy()

    async def pre_tool_use_hook(
        input_data: dict[str, Any],
        _tool_use_id: str | None,
        _context: Any,
    ) -> dict[str, Any]:
        """Return empty dict to allow, or dict with 'decision'/'systemMessage' to block."""
        tool_name = input_data.get('tool_name', '')
        tool_input = input_data.get('tool_input', {})

        if tool_name == "Read":
            return {}

        if tool_name in ["Write", "Edit"]:
            file_path = tool_input.get("file_path", "")

            for allowed_dir in allowed_directories:
                normalized_dir = allowed_dir if allowed_dir.endswith('/') else allowed_dir + '/'
                if file_path.startswith(normalized_dir) or file_path == allowed_dir.rstrip('/'):
                    return {}

            return {
                'decision': 'block',
                'systemMessage': (
                    f'Write/Edit access denied: {file_path}\n'
                    f'Allowed directories: {", ".join(allowed_directories)}'
                )
            }

        if tool_name == "Bash":
            command = tool_input.get("command", "")

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

            if not allow_bash_redirection:
                redirect_pattern = r'(?:>\s?|\>\>\s?)([^\s&|;]+)'
                redirected_files = re.findall(redirect_pattern, command)

                for file_path in redirected_files:
                    file_path = file_path.strip('"').strip("'")

                    if file_path.startswith("/dev/"):
                        continue

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

            return {}

        return {}

    return HookMatcher(hooks=[pre_tool_use_hook])  # type: ignore[list-item]


def create_sandbox_hook(
    sandbox_dir: str,
    additional_allowed_dirs: list[str] | None = None,
) -> HookMatcher:
    """Create a strict sandbox hook that also blocks wget/curl.

    Args:
        sandbox_dir: Primary sandbox directory for all file operations.
        additional_allowed_dirs: Extra directories to allow (e.g. ["/tmp"]).
    """
    allowed_dirs = [sandbox_dir]
    if additional_allowed_dirs:
        allowed_dirs.extend(additional_allowed_dirs)

    return create_permission_hook(
        allowed_directories=allowed_dirs,
        block_bash_commands=SANDBOX_BLOCKED_COMMANDS,
        allow_bash_redirection=False
    )
