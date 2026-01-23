---
name: add-agent
description: Create a new agent with proper YAML structure, following project conventions
disable-model-invocation: true
---

# Add New Agent

Creates a new agent entry in `backend/agent/agents.yaml` following the project's conventions:
- Unique ID format: `{name}-{unique_suffix}`
- Appends system_prompt to claude_code preset (doesn't replace)
- Includes default tools from `_defaults` section
- Proper model and permission settings

## Usage

Run this skill to create a new agent:
```
/add-agent "Agent Name" "Description of what it does"
```

## Implementation

1. Read `backend/agent/agents.yaml` to understand current structure
2. Generate unique ID: `echo "{name}-$(openssl rand -hex 4)"`
3. Prompt for:
   - Agent name
   - Description
   - System prompt (instructions appended to claude_code)
   - Tools (default: Read, Write, Edit, Bash, Grep, Glob, Skill, Task)
   - Model (default: sonnet)
   - Permission mode (default: acceptEdits)
4. Append new entry to `agents.yaml`
5. Validate YAML syntax
6. Show diff and confirm before saving

## Template

```yaml
{{agent_id}}:
  name: "{{agent_name}}"
  description: "{{description}}"
  system_prompt: |
    {{system_prompt_instructions}}
  tools:
    - Skill
    - Task
    - Read
    - Write
    - Edit
    - Bash
    - Grep
    - Glob
  model: sonnet
  permission_mode: acceptEdits
  include_partial_messages: true
  setting_sources:
    - project
  cwd: null
  disallowed_tools: []
  mcp_servers: {}
  allowed_directories:
    - /tmp
  with_permissions: true
```
