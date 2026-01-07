# Permission Hooks Guide

The `agent.core.hook` module provides reusable permission control hooks for the Claude Agent SDK.

## 📁 Files Created

1. **`agent/core/hook.py`** - Core permission hook implementation
2. **`agent/core/options.py`** - Updated with hook integration
3. **`agent/core/__init__.py`** - Updated exports
4. **`tests/test_hooks_example.py`** - Usage examples

## 🎯 Features

### Security Controls

✅ **File Operation Restrictions**
- Write/Edit tools only work in allowed directories
- Read operations allowed everywhere (read-only access)

✅ **Bash Command Control**
- Blocks dangerous commands: `rm`, `mv`, `cp`, `mkdir`, `rmdir`, `touch`
- Allows safe commands: `ls`, `cat`, `grep`, `echo`, `pwd`, `cd`

✅ **Bash Redirection Control**
- Blocks file redirection (`>`, `>>`) outside allowed directories
- Allows `/dev/null` redirection (common for error output)

## 🚀 Usage Examples

### Example 1: Enhanced Options with Permissions

```python
from agent.core import create_enhanced_options

# Create options with permission hooks
options = create_enhanced_options(
    with_permissions=True,
    allowed_directories=["/path/to/tests", "/tmp"]
)

# Use with SDK client
from claude_agent_sdk import ClaudeSDKClient

client = ClaudeSDKClient(options=options)
```

### Example 2: Sandbox Mode (Maximum Security)

```python
from agent.core import create_sandbox_options
from agent import PROJECT_ROOT

# Create strict sandbox
options = create_sandbox_options(
    sandbox_dir=str(PROJECT_ROOT / "tests"),
    additional_allowed_dirs=["/tmp"]
)

client = ClaudeSDKClient(options=options)
```

### Example 3: Custom Permission Hooks

```python
from agent.core import create_permission_hook
from claude_agent_sdk import ClaudeAgentOptions

# Create custom hook
hook = create_permission_hook(
    allowed_directories=["/safe/folder"],
    block_bash_commands=["rm ", "dd ", "mkfs"],
    allow_bash_redirection=False
)

# Use with SDK options
options = ClaudeAgentOptions(
    hooks={'PreToolUse': [hook]}
)
```

### Example 4: Sandbox Hook

```python
from agent.core import create_sandbox_hook

# Create strict sandbox hook
hook = create_sandbox_hook(
    sandbox_dir="/path/to/sandbox",
    additional_allowed_dirs=["/tmp"]
)

options = ClaudeAgentOptions(
    hooks={'PreToolUse': [hook]}
)
```

## 📚 API Reference

### `create_permission_hook()`

Create a configurable pre-tool-use hook for permissions.

**Parameters:**
- `allowed_directories` (list[str] | None): Directories where file operations are allowed. Defaults to [project_root, "/tmp"].
- `block_bash_commands` (list[str] | None): Bash command patterns to block. Defaults to ["rm ", "mv ", "cp ", "mkdir ", "rmdir ", "touch "].
- `allow_bash_redirection` (bool): Whether to allow bash redirection. Default: False.

**Returns:** `HookMatcher`

### `create_sandbox_hook()`

Create a strict sandbox hook for maximum security.

**Parameters:**
- `sandbox_dir` (str): Primary sandbox directory for all operations.
- `additional_allowed_dirs` (list[str] | None): Additional directories to allow.

**Returns:** `HookMatcher`

### `create_enhanced_options()`

Create SDK options with skills, subagents, and optional permissions.

**Parameters:**
- `resume_session_id` (str | None): Session ID to resume.
- `with_permissions` (bool): Add permission hooks. Default: False.
- `allowed_directories` (list[str] | None): Directories for file operations. Only used when with_permissions=True.

**Returns:** `ClaudeAgentOptions`

### `create_sandbox_options()`

Create SDK options with strict sandbox permissions.

**Parameters:**
- `sandbox_dir` (str): Primary sandbox directory.
- `additional_allowed_dirs` (list[str] | None): Additional allowed directories.
- `resume_session_id` (str | None): Session ID to resume.

**Returns:** `ClaudeAgentOptions`

## 🔒 Security Best Practices

1. **Always use sandbox mode** for untrusted code or user input
2. **Restrict to minimal directories** - only allow access to what's necessary
3. **Test permissions** before deploying to production
4. **Monitor hook behavior** - the hooks will log when operations are blocked
5. **Use `/tmp` for temporary files** - it's designed for temporary data

## 🧪 Testing

Run the example test file to see the hooks in action:

```bash
python tests/test_hooks_example.py
```

This will demonstrate:
- Creating options with permissions
- Sandbox mode
- Custom hooks
- Permission information
- Live testing with SDK client

## 📖 Related Documentation

- [Python SDK Hooks Guide](https://platform.claude.com/docs/en/agent-sdk/python#hook-matcher)
- [PreToolUse Hook Reference](https://platform.claude.com/docs/en/agent-sdk/python#hook-matcher)
- [Agent SDK Overview](https://platform.claude.com/docs/en/agent-sdk/overview)

## 🎓 Summary

The permission hooks module provides a reusable, configurable way to control agent access to files and directories. It integrates seamlessly with the existing SDK options and can be used to create secure sandboxed environments for testing and production use.
