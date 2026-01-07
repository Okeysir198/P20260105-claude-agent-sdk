# Debt Collection Voice Agent

A production-ready multi-agent voice assistant for debt collection calls, built with LiveKit Agents SDK 1.2+.

## 📁 Structure

```
debt_collection_agent/
├── agent.yaml                 # Configuration (LLM, STT, TTS, sub-agents)
├── agents.py                  # Main entrypoint with AgentServer
├── shared_state.py            # UserData container
├── state/                     # State management
│   ├── __init__.py
│   ├── types.py               # Enums (PersonType, PaymentMethod, CallOutcome)
│   ├── profile.py             # Immutable DebtorProfile (frozen=True)
│   └── session.py             # Mutable CallState
├── sub_agents/                # Agent classes
│   ├── __init__.py
│   ├── base_agent.py          # BaseAgent with context preservation
│   ├── factory.py             # create_agents() factory
│   ├── agent01_introduction.py
│   ├── agent02_verification.py
│   ├── agent03_negotiation.py
│   ├── agent04_payment.py
│   └── agent05_closing.py
├── tools/                     # Tool functions
│   ├── __init__.py            # TOOL_REGISTRY and get_tools_by_names()
│   ├── common_tools.py        # schedule_callback, escalate, end_call
│   ├── tool01_introduction.py
│   ├── tool02_verification.py
│   ├── tool03_negotiation.py
│   ├── tool04_payment.py
│   └── tool05_closing.py
├── prompts/                   # YAML prompts with Mustache templates
│   ├── __init__.py            # load_prompt(), format_prompt()
│   ├── prompt01_introduction.yaml
│   ├── prompt02_verification.yaml
│   ├── prompt03_negotiation.yaml
│   ├── prompt04_payment.yaml
│   └── prompt05_closing.yaml
├── business_rules/            # Domain-specific rules
│   └── __init__.py
└── utils/                     # Utilities
    ├── __init__.py
    └── id_generator.py        # generate_session_id()
```

## 🚀 Usage

### Running the Agent

```bash
# Run the agent server
cd debt_collection_agent
python agents.py

# Or specify custom port
AGENT_PORT=8084 python agents.py
```

### Connecting to the Agent

The agent will connect to LiveKit room and listen for incoming calls.

## 🔧 Configuration

### LLM Configuration

Edit `agent.yaml`:

```yaml
llm:
  provider: openai
  model: gpt-4o-mini
  temperature: 0.2
```

### TTS Configuration

```yaml
tts:
  provider: supertonic_tts
  supertonic_tts:
    api_url: http://localhost:18012
    voice_style: M1
    speed: 1.2
```

### STT Configuration

```yaml
stt:
  provider: deepgram
  model: nova-2
```

## 📋 Agent Workflow

1. **Introduction** - Confirm speaking with correct person
2. **Verification** - Verify identity with 2 data points
3. **Negotiation** - Explain debt, offer settlement/installment options
4. **Payment** - Capture payment arrangement details
5. **Closing** - Wrap up call, update contact details

## 🛠️ Customization

### Adding New Tools

1. Create tool in `tools/toolXX_<phase>.py`
2. Add to `TOOL_REGISTRY` in `tools/__init__.py`
3. Add to agent's `tools` list in `agent.yaml`

### Modifying Prompts

Edit prompt YAML files in `prompts/` directory. Use Mustache syntax for variables:

```yaml
prompt: |
  You are the Introduction Agent.
  Greet {{debtor_name}} professionally.
```

### Adding New Agents

1. Create agent class in `sub_agents/agentXX_<name>.py`
2. Add to `AGENT_CLASSES` in `sub_agents/factory.py`
3. Add entry to `sub_agents` in `agent.yaml`
4. Create corresponding prompt and tools

## 📊 State Management

### Immutable Profile (DebtorProfile)
- Customer details from database
- Loaded once per session
- Use `frozen=True` dataclass

### Mutable Session (CallState)
- Tracks call progress
- Verification status
- Payment arrangements
- Call notes and outcomes

### UserData Container
- Aggregates profile + session
- Agent references for handoffs
- Session metadata

## 🔍 Key Features

- **Context Preservation**: Chat history preserved across agent handoffs
- **Silent Handoffs**: Seamless agent transitions without announcements
- **Tool Call Events**: Real-time tool execution logging via data channels
- **POPI Compliance**: Privacy-aware identity verification
- **Flexible Payment Options**: Settlement discounts and installment plans

## 🧪 Testing

```bash
# Validate Python syntax
python -m py_compile agents.py shared_state.py

# Test imports
python -c "from shared_state import UserData; print('Import successful')"
```

## 📝 Notes

- Agent ID: `debt-collection-agent-a3f8e2` (random suffix for uniqueness)
- Default port: 8083 (override with `AGENT_PORT` env var)
- Uses supertonic_tts by default (configure in agent.yaml)
- Requires LiveKit room connection via job metadata

## 🤝 Support

For issues or questions, refer to:
- LiveKit Agents SDK docs: https://docs.livekit.io/agents
- Reference implementation: `../ref/debt_collection/`
