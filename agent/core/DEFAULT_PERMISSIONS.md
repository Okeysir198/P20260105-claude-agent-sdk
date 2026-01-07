# Default Permissions Summary

## ✅ Default Behavior

When using `create_enhanced_options(with_permissions=True)`, the default behavior is:

### Allowed Directories:
- **PROJECT_ROOT** (current working directory) - Full read/write/edit access
- **/tmp** (temporary folder) - Full read/write/edit access

### Blocked:
- Write/Edit operations **outside** PROJECT_ROOT and /tmp
- Bash file manipulation commands: `rm`, `mv`, `cp`, `mkdir`, `rmdir`, `touch`
- Bash redirection (`>`, `>>`) to files outside allowed directories

### Always Allowed:
- **Read operations** anywhere (read-only access to entire system)
- Safe bash commands: `ls`, `cat`, `grep`, `echo`, `pwd`, `cd`

## 📝 Usage Examples

### Example 1: Default Permissions (Recommended)

```python
from agent.core import create_enhanced_options

# Enable permissions with default (cwd + /tmp)
options = create_enhanced_options(with_permissions=True)

# This allows:
# - Write/Edit in project directory
# - Write/Edit in /tmp
# - Read anywhere
# - Blocks writes to system directories
```

### Example 2: Custom Directories

```python
# Custom allowed directories
options = create_enhanced_options(
    with_permissions=True,
    allowed_directories=[
        "/path/to/project",
        "/tmp",
        "/another/safe/path"
    ]
)
```

### Example 3: Sandbox Mode (Strict)

```python
from agent.core import create_sandbox_options

# Restrict to specific directory only
options = create_sandbox_options(
    sandbox_dir="/path/to/tests",
    additional_allowed_dirs=["/tmp"]
)
```

## 🔒 Why These Defaults?

### PROJECT_ROOT (cwd):
- ✅ Allows normal development work
- ✅ Agent can modify project files as needed
- ✅ Safe because it's within your project

### /tmp:
- ✅ Standard location for temporary files
- ✅ Agent can test code, create scratch files
- ✅ Safe because /tmp is designed for temporary data

### Read-Only Everywhere:
- ✅ Agent can explore your system to understand context
- ✅ Can read documentation, config files, etc.
- ✅ Cannot accidentally modify system files

## 🚀 Quick Start

```python
from agent.core import create_enhanced_options, ConversationSession

# Create options with safe default permissions
options = create_enhanced_options(with_permissions=True)

# Start a conversation session
session = ConversationSession(options=options)
await session.start()

# Your agent now has safe, controlled access to your project!
```

## 📊 Test Results

All tests pass with default permissions:
- ✅ Write to /tmp - **ALLOWED**
- ✅ Write to PROJECT_ROOT - **ALLOWED**
- ❌ Write to /home, /usr, /etc - **BLOCKED**
- ✅ Read anywhere - **ALLOWED**
- ❌ Bash `rm`, `mv`, `cp` - **BLOCKED**
- ✅ Bash `ls`, `cat`, `grep` - **ALLOWED**

## 🎓 Best Practices

1. **Always use `with_permissions=True`** for production code
2. **Test your permissions** before deploying
3. **Use sandbox mode** for untrusted code or user input
4. **Keep default settings** unless you have specific needs
5. **Monitor blocked operations** - hooks will report when actions are blocked
