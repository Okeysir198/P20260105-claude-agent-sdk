"""
Debt Collection Multi-Agent System

LiveKit voice agent for debt collection with POPI compliance.
Agent flow: Introduction -> Verification -> Negotiation -> Payment -> Closing
"""

# ============================================
# IMPORTS
# ============================================
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
import yaml

from livekit.agents import AgentServer, JobContext, cli, AutoSubscribe, RoomOutputOptions
from livekit.agents.voice import AgentSession
from livekit.agents.voice.events import FunctionToolsExecutedEvent
from livekit.plugins import deepgram, openai, silero, cartesia, assemblyai
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from dotenv import load_dotenv

_current_dir = Path(__file__).parent
sys.path.insert(0, str(_current_dir))
sys.path.insert(0, str(_current_dir.parent))

load_dotenv(_current_dir.parent / ".env", override=True)

# Custom TTS plugins
from livekit_custom_plugins import chatterbox_tts

# Agent imports
from sub_agents import INTRODUCTION, create_agents
from shared_state import UserData, DebtorProfile, CallState, get_test_debtor
from business_rules.config import AUTHORITIES, SCRIPT_TYPES
from utils.id_generator import generate_session_id

# ============================================
# CONFIGURATION
# ============================================
logger = logging.getLogger("debt-collection-agent")

config_path = Path(__file__).parent / "agent.yaml"
CONFIG = yaml.safe_load(config_path.read_text()) if config_path.exists() else {}

# Server
DEFAULT_PORT = 8083
MAX_TOOL_STEPS = 5


# ============================================
# STT FACTORY
# ============================================
def create_stt():
    """Create STT instance from config."""
    stt_cfg = CONFIG["stt"]
    provider = stt_cfg["provider"]

    if provider == "assemblyai":
        return assemblyai.STT()
    return deepgram.STT(model=stt_cfg["model"])


# ============================================
# TTS FACTORY
# ============================================
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
    # chatterbox_tts
    return chatterbox_tts.TTS(
        api_url=cfg["api_url"],
        audio_prompt_path=cfg["audio_prompt_path"],
        exaggeration=cfg["exaggeration"],
        cfg_weight=cfg["cfg_weight"],
        normalize_text=cfg["normalize_text"],
    )


# ============================================
# SERVER & ENTRYPOINT
# ============================================
agent_port = int(os.getenv("AGENT_PORT", str(DEFAULT_PORT)))
server = AgentServer(port=agent_port)


@server.rtc_session(agent_name=CONFIG.get("id", "debt_collection-agent"))
async def entrypoint(ctx: JobContext):
    """Multi-agent debt collection workflow entrypoint."""

    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    participant = await ctx.wait_for_participant()
    logger.info(f"Participant connected: {participant.identity}")

    # Load debtor data from job metadata or use test data
    metadata = json.loads(ctx.job.metadata) if ctx.job.metadata else get_test_debtor()
    debtor_data = metadata.get("debtor", {})
    script_type = metadata.get("script_type", "ratio1_inflow")

    # Initialize state
    debtor = DebtorProfile(**debtor_data)
    script_config = SCRIPT_TYPES.get(script_type, SCRIPT_TYPES["ratio1_inflow"])
    authority_info = AUTHORITIES[script_config.get("authority", "cartrack")]
    call_state = CallState(
        script_type=script_type,
        authority=authority_info["name"],
        authority_contact=authority_info["contact"],
    )

    userdata = UserData(debtor=debtor, call=call_state)
    userdata.session_id = generate_session_id()
    userdata.job_context = ctx
    logger.info(f"Session ID: {userdata.session_id}")

    # Create all agents using factory
    userdata.agents = create_agents(userdata)
    logger.info(f"Initialized {len(userdata.agents)} agents")

    # Create session with configurable STT/TTS
    llm_cfg = CONFIG.get("llm", {})

    session = AgentSession[UserData](
        userdata=userdata,
        llm=openai.LLM(
            model=llm_cfg.get("model", "gpt-4o-mini"),
            temperature=llm_cfg.get("temperature", 0.7),
            parallel_tool_calls=False,
        ),
        stt=create_stt(),
        tts=create_tts(),
        vad=silero.VAD.load(),
        turn_detection=MultilingualModel(),
        max_tool_steps=MAX_TOOL_STEPS,
    )

    # Register event handler BEFORE session.start() to capture all tool calls
    # Note: .on() requires sync callback, so we create async task inside
    def on_tool_executed(event: FunctionToolsExecutedEvent):
        async def _publish_tool_calls():
            logger.info(f"[TOOL_EVENT] function_tools_executed triggered with {len(event.function_calls)} calls")
            try:
                for call, output in event.zipped():
                    logger.info(f"[TOOL_EVENT] Publishing tool call: {call.name}")
                    payload = json.dumps({
                        "type": "tool_call",
                        "id": call.call_id,
                        "name": call.name,
                        "arguments": json.loads(call.arguments),
                        "result": output.output if output else None,
                        "is_error": output.is_error if output else False,
                        "timestamp": int(event.created_at * 1000)  # Convert to milliseconds for frontend
                    })
                    await ctx.room.local_participant.send_text(
                        payload,
                        topic="lk.tool_calls"
                    )
                    logger.info(f"[TOOL_EVENT] Successfully published tool call: {call.name}")
            except Exception as e:
                logger.error(f"Failed to publish tool call event: {e}", exc_info=True)

        asyncio.create_task(_publish_tool_calls())

    session.on("function_tools_executed", on_tool_executed)

    await session.start(
        agent=userdata.agents[INTRODUCTION],
        room=ctx.room,
        room_output_options=RoomOutputOptions(sync_transcription=False),
    )


# ============================================
# CLI
# ============================================
if __name__ == "__main__":
    cli.run_app(server)
