# Phase 1: BUILD

Generate the voice agent structure based on user requirements.

## 1.1 Requirements Gathering

Ask the user for:

| Requirement | Question | Example |
|-------------|----------|---------|
| **Domain** | What is the agent's purpose? | Customer support, appointment booking |
| **Sub-agents** | What workflow stages are needed? | Greeting, verification, resolution |
| **Tools** | What actions should the agent perform? | lookup_order, schedule_callback |
| **Tone** | What personality should the agent have? | Professional, friendly, empathetic |
| **Constraints** | What should the agent NOT do? | Never discuss pricing without verification |

## 1.2 Directory Structure

Create the agent directory structure:

```bash
mkdir -p {agent_path}
mkdir -p {agent_path}/sub_agents
mkdir -p {agent_path}/tools
mkdir -p {agent_path}/state
mkdir -p {agent_path}/prompts
```

## 1.3 File Generation

Generate these files using the Write tool:

### Core Files
| File | Purpose |
|------|---------|
| `agent.yaml` | Configuration with sub-agents, tools, handoffs |
| `agents.py` | Entry point with STT/TTS factories |
| `shared_state.py` | UserData container |

### Sub-agents Module
| File | Purpose |
|------|---------|
| `sub_agents/__init__.py` | Package exports |
| `sub_agents/base_agent.py` | Base agent with context preservation |
| `sub_agents/factory.py` | AGENT_CLASSES and create_agents() |

### Tools Module
| File | Purpose |
|------|---------|
| `tools/__init__.py` | TOOL_REGISTRY pattern |

### State Module
| File | Purpose |
|------|---------|
| `state/types.py` | Domain enums |
| `state/profile.py` | Immutable profile |
| `state/session.py` | Mutable session state |

### Prompts Module
| File | Purpose |
|------|---------|
| `prompts/__init__.py` | load_prompt, format_prompt |
| `prompts/_versions.yaml` | Version registry |

## 1.4 Validation

Verify Python syntax for all generated files:

```bash
python -m py_compile {agent_path}/agents.py
python -m py_compile {agent_path}/sub_agents/factory.py
python -m py_compile {agent_path}/tools/__init__.py
```

## 1.5 Success Criteria

Phase 1 is complete when:
- [ ] All directories exist
- [ ] All files are generated
- [ ] Python syntax validation passes
- [ ] agent.yaml is valid YAML

## Related Skills

- **voice-agent-generator**: Provides detailed templates for each file type
