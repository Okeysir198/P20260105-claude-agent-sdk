# LiveKit SDK 1.2+ Patterns

Reference patterns for LiveKit Agents SDK 1.2+.

## Agent Class

Agents inherit from `livekit.agents.voice.Agent`:

```python
from livekit.agents.voice import Agent, RunContext

class MyAgent(Agent):
    """Agent with instructions and tools."""

    def __init__(self, instructions: str, tools: list, **kwargs):
        super().__init__(
            instructions=instructions,
            tools=tools,
            **kwargs,
        )

    async def on_enter(self) -> None:
        """Called when agent becomes active."""
        # Access session state
        userdata = self.session.userdata

        # Optionally modify chat context
        chat_ctx = self.chat_ctx.copy()
        chat_ctx.add_message(role="system", content="Additional context...")
        await self.update_chat_ctx(chat_ctx)
```

## AgentSession

Sessions manage conversation state and provider instances:

```python
from livekit.agents.voice import AgentSession

session = AgentSession[UserData](
    userdata=userdata,
    llm=openai.LLM(
        model="gpt-4o-mini",
        temperature=0.7,
        parallel_tool_calls=False,
    ),
    stt=deepgram.STT(model="nova-2"),
    tts=cartesia.TTS(
        model="sonic-2",
        voice="voice-id-here",
    ),
    vad=silero.VAD.load(),
    turn_detection=MultilingualModel(),
    max_tool_steps=5,
)

await session.start(
    agent=start_agent,
    room=ctx.room,
    room_output_options=RoomOutputOptions(sync_transcription=False),
)
```

## STT Factory Pattern

Create STT from configuration:

```python
from livekit.plugins import deepgram, assemblyai

def create_stt():
    """Create STT instance from config."""
    stt_cfg = CONFIG["stt"]
    provider = stt_cfg["provider"]

    if provider == "assemblyai":
        return assemblyai.STT()
    return deepgram.STT(model=stt_cfg["model"])
```

## LLM Factory Pattern

Create LLM from configuration:

```python
from livekit.plugins import openai

def create_llm():
    """Create LLM instance from config."""
    llm_cfg = CONFIG["llm"]
    return openai.LLM(
        model=llm_cfg.get("model", "gpt-4o-mini"),
        temperature=llm_cfg.get("temperature", 0.2),
        parallel_tool_calls=False,
    )
```

## TTS Factory Pattern

Create TTS from configuration with multiple provider support:

```python
from livekit.plugins import cartesia

def create_tts():
    """Create TTS instance from config."""
    tts_cfg = CONFIG["tts"]
    provider = tts_cfg["provider"]
    cfg = tts_cfg[provider]

    if provider == "cartesia":
        return cartesia.TTS(
            model=cfg["model"],
            voice=cfg["voice"],
            speed=cfg["speed"],
            language=cfg["language"],
        )
    if provider == "kokoro_tts":
        from livekit_custom_plugins import kokoro_tts
        return kokoro_tts.TTS(
            api_url=cfg["api_url"],
            voice=cfg["voice"],
            speed=cfg["speed"],
            normalize_text=cfg["normalize_text"],
        )
    if provider == "supertonic_tts":
        from livekit_custom_plugins import supertonic_tts
        return supertonic_tts.TTS(
            api_url=cfg["api_url"],
            voice_style=cfg["voice_style"],
            speed=cfg["speed"],
            total_step=cfg["total_step"],
            silence_duration=cfg["silence_duration"],
        )
    # chatterbox_tts (default)
    from livekit_custom_plugins import chatterbox_tts
    return chatterbox_tts.TTS(
        api_url=cfg["api_url"],
        audio_prompt_path=cfg["audio_prompt_path"],
        exaggeration=cfg["exaggeration"],
        cfg_weight=cfg["cfg_weight"],
        normalize_text=cfg["normalize_text"],
    )
```

## Entrypoint Pattern

Main entry with JobContext:

```python
from livekit.agents import AgentServer, JobContext, cli, AutoSubscribe, RoomOutputOptions

server = AgentServer(port=8083)

@server.rtc_session(agent_name="my-agent")
async def entrypoint(ctx: JobContext):
    """Agent entrypoint."""

    # Connect to room
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    participant = await ctx.wait_for_participant()

    # Load metadata
    metadata = json.loads(ctx.job.metadata) if ctx.job.metadata else {}

    # Initialize state
    userdata = UserData(...)
    userdata.job_context = ctx

    # Create agents
    userdata.agents = create_agents(userdata)

    # Create and start session
    session = AgentSession[UserData](
        userdata=userdata,
        llm=create_llm(CONFIG),
        stt=create_stt(CONFIG),
        tts=create_tts(CONFIG),
    )

    await session.start(
        agent=userdata.agents["introduction"],
        room=ctx.room,
    )

if __name__ == "__main__":
    cli.run_app(server)
```

## agent.yaml Configuration Structure

**IMPORTANT**: Agent ID must always have a random suffix (e.g., `my-agent-7b3f2a`).

```yaml
# ============================================
# AGENT IDENTITY
# ============================================
# NOTE: ID must always have a random suffix like -7b3f2a
id: my-agent-7b3f2a
name: My Agent
description: Agent purpose

# ============================================
# LLM CONFIGURATION
# ============================================
llm:
  provider: openai
  model: gpt-4o-mini
  temperature: 0.2

# ============================================
# STT CONFIGURATION
# ============================================
stt:
  provider: deepgram
  model: nova-2

# ============================================
# TTS CONFIGURATION
# ============================================
tts:
  provider: supertonic_tts  # Options: cartesia, chatterbox_tts, kokoro_tts, supertonic_tts
  cartesia:
    model: sonic-2
    voice: 794f9389-aac1-45b6-b726-9d9369183238
    speed: 1.0
    language: en
  chatterbox_tts:
    api_url: http://localhost:19810
    audio_prompt_path: voice/debt_voice.mp3
    exaggeration: 0.5
    cfg_weight: 0.5
    normalize_text: true
  kokoro_tts:
    api_url: http://localhost:18011
    voice: am_adam
    speed: 1.0
    normalize_text: true
  supertonic_tts:
    api_url: http://localhost:18012
    voice_style: M1
    speed: 1.2
    total_step: 5
    silence_duration: 0.3

# ============================================
# TEMPLATE VARIABLES
# ============================================
variables:
  default_agent_name: "Alex"

# ============================================
# SUB-AGENTS
# ============================================
sub_agents:
  - id: introduction
    name: Introduction Agent
    description: Confirms caller identity
    tools:
      - confirm_person
      - handle_wrong_person
    instructions: prompts/prompt01_introduction.yaml

  - id: main
    name: Main Agent
    description: Handles main conversation
    tools:
      - process_request
      - schedule_callback
    instructions: prompts/prompt02_main.yaml

# ============================================
# HANDOFFS
# ============================================
# Defines transitions between agents based on conversation outcomes.
# Each handoff specifies:
#   - source: The agent initiating the handoff
#   - target: The agent receiving control
#   - condition: When the handoff should occur (natural language for LLM)
#   - context: (optional) What information to pass to the next agent
handoffs:
  - source: introduction
    target: verification
    condition: Person confirmed identity (customer said yes/confirmed they are the right person)
    context: Pass customer name and confirmation status

  - source: introduction
    target: closing
    condition: Wrong person, third party, or customer unavailable
    context: Pass reason for closing (wrong_person, third_party, unavailable)

  - source: verification
    target: main
    condition: Identity verified successfully (at least 2 fields confirmed)
    context: Pass verification status and confirmed fields

  - source: verification
    target: closing
    condition: Verification failed after 3 attempts or callback requested
    context: Pass verification failure reason or callback request

  - source: main
    target: closing
    condition: Task completed, escalation requested, or callback scheduled
    context: Pass outcome (success, escalation, callback) and details

# ============================================
# OBSERVABILITY
# ============================================
observability:
  tracing_enabled: true
  log_level: INFO
```

## Handoff Configuration in agent.yaml

The `handoffs` section in `agent.yaml` defines transitions between sub-agents. This is documentation
for the LLM to understand when to trigger handoffs - the actual handoff is performed via tools.

### Handoff Structure

```yaml
handoffs:
  - source: <source_agent_id>      # Agent that initiates handoff
    target: <target_agent_id>      # Agent that receives control
    condition: <natural_language>  # When handoff should occur
    context: <what_to_pass>        # Optional: information to preserve
```

### Condition Writing Guidelines

Conditions should be clear, specific, and measurable:

**Good conditions:**
- "Person confirmed identity (customer said yes/confirmed they are the right person)"
- "Identity verified successfully (at least 2 fields confirmed)"
- "Payment arrangement accepted by customer"
- "Customer explicitly refuses to pay or requests escalation"

**Avoid vague conditions:**
- "When appropriate" (too vague)
- "If needed" (not specific)
- "Customer seems ready" (subjective)

### Context Passing Examples

Context helps the next agent continue the conversation smoothly:

```yaml
handoffs:
  # Pass verification results to negotiation
  - source: verification
    target: negotiation
    condition: Identity verified successfully
    context: Pass verification status, confirmed fields, and any flags (e.g., third_party_authorized)

  # Pass arrangement details to payment
  - source: negotiation
    target: payment
    condition: Payment arrangement accepted by customer
    context: Pass arrangement type (settlement/installment), amount, date, discount applied

  # Pass outcome to closing
  - source: payment
    target: closing
    condition: Payment arrangement confirmed
    context: Pass confirmation reference, payment method, next steps communicated
```

### Multi-Path Handoffs

An agent can have multiple handoff targets based on different outcomes:

```yaml
handoffs:
  # Happy path: continue to next step
  - source: verification
    target: main
    condition: Identity verified successfully

  # Failure path: go to closing
  - source: verification
    target: closing
    condition: Verification failed after 3 attempts

  # Callback path: schedule and close
  - source: verification
    target: closing
    condition: Customer requests callback
```

## Context Preservation During Handoffs

Transfer conversation context between agents:

```python
CHAT_CONTEXT_MAX_ITEMS = 6

async def on_enter(self) -> None:
    """Preserve context from previous agent."""
    userdata = self.session.userdata
    chat_ctx = self.chat_ctx.copy()

    # Copy history from previous agent
    if isinstance(userdata.prev_agent, Agent):
        prev_ctx = userdata.prev_agent.chat_ctx.copy(
            exclude_instructions=True,
            exclude_function_call=False,
        ).truncate(max_items=CHAT_CONTEXT_MAX_ITEMS)

        existing_ids = {item.id for item in chat_ctx.items}
        new_items = [
            item for item in prev_ctx.items
            if item.id not in existing_ids
        ]
        chat_ctx.items.extend(new_items)

    # Add current state
    chat_ctx.add_message(
        role="system",
        content=f"Current state:\n{userdata.summarize()}",
    )

    await self.update_chat_ctx(chat_ctx)
```

## Agent Transfer Pattern

Tools return Agent for silent handoff or (Agent, str) for announced:

```python
async def transfer_to_agent(
    agent_name: str,
    context: RunContext[UserData],
    silent: bool = False,
) -> tuple[Agent, str] | Agent:
    """Transfer to another agent."""
    userdata = context.userdata

    next_agent = userdata.agents[agent_name]
    userdata.prev_agent = context.session.current_agent

    if silent:
        return next_agent
    return (next_agent, f"Transferring to {agent_name}.")
```
