"""
Model Provider Factory

Reusable factory functions for LLM, STT, and TTS providers.
All local TTS/STT servers use Deepgram-compatible API with custom base_url.

Usage:
    from model_provider import create_llm, create_stt, create_tts

    llm = create_llm(config)
    stt = create_stt(config)
    tts = create_tts(config)
"""

from livekit.plugins import deepgram, cartesia, assemblyai, openai


def create_llm(config: dict, parallel_tool_calls: bool = False):
    """Create LLM instance from config.

    Args:
        config: Full agent config dict containing 'llm' section
        parallel_tool_calls: Whether to allow parallel tool calls (default: False)

    Config format:
        llm:
          provider: openai  # Options: openai
          model: gpt-4o-mini
          temperature: 0.7
    """
    llm_cfg = config.get("llm", {})

    return openai.LLM(
        model=llm_cfg.get("model", "gpt-4o-mini"),
        temperature=llm_cfg.get("temperature", 0.7),
        parallel_tool_calls=parallel_tool_calls,
    )


def build_model_with_params(model: str, **params) -> str:
    """Encode parameters in model name string.

    Format: model_name;param1=value1;param2=value2
    Example: am_adam;speed=1.2;language=en-us

    This workaround is needed because deepgram.TTS plugin adds its own
    query params with '?' which breaks URLs that already have query params.
    """
    param_parts = [f"{k}={v}" for k, v in params.items() if v is not None]
    if param_parts:
        return f"{model};{';'.join(param_parts)}"
    return model


def create_stt(config: dict):
    """Create STT instance from config.

    Args:
        config: Full agent config dict containing 'stt' section

    Config format:
        stt:
          provider: deepgram  # Options: deepgram, deepgram_cloud, assemblyai, whisper_v3_turbo_stt, etc.
          model: nova-2
          whisper_v3_turbo_stt:
            base_url: ws://localhost:18020/stream
            language: en
    """
    stt_cfg = config.get("stt", {})
    provider = stt_cfg.get("provider", "deepgram")
    cfg = stt_cfg.get(provider, {})

    # Cloud services
    if provider == "assemblyai":
        return assemblyai.STT()
    if provider == "deepgram_cloud":
        return deepgram.STT(model=cfg.get("model", "nova-2"))

    # Local STT servers (Deepgram-compatible)
    if provider in ["whisper_v3_turbo_stt", "faster_whisper_stt", "nemotron_speech_stt"]:
        return deepgram.STT(
            base_url=cfg.get("base_url"),
            language=cfg.get("language", "en"),
        )

    # Default to deepgram cloud
    return deepgram.STT(model=stt_cfg.get("model", "nova-2"))


def create_tts(config: dict):
    """Create TTS instance from config.

    All local TTS servers use Deepgram-compatible API via deepgram.TTS plugin.
    Custom parameters are encoded in the model name (e.g., 'am_adam;speed=1.2').

    Args:
        config: Full agent config dict containing 'tts' section

    Config format:
        tts:
          provider: supertonic_tts  # Options: cartesia, kokoro_tts, chatterbox_tts, supertonic_tts
          cartesia:
            model: sonic-2
            voice: 794f9389-aac1-45b6-b726-9d9369183238
            speed: 1.0
            language: en
          supertonic_tts:
            base_url: http://localhost:18017/v1/speak
            model: M1
            speed: 1.2
            total_steps: 5
            silence_duration: 0.3
    """
    tts_cfg = config.get("tts", {})
    provider = tts_cfg.get("provider", "supertonic_tts")
    cfg = tts_cfg.get(provider, {})

    if provider == "cartesia":
        return cartesia.TTS(
            model=cfg.get("model", "sonic-2"),
            voice=cfg.get("voice", "794f9389-aac1-45b6-b726-9d9369183238"),
            speed=cfg.get("speed", 1.0),
            language=cfg.get("language", "en"),
        )

    # All local TTS servers use Deepgram-compatible API
    if provider == "supertonic_tts":
        base_url = cfg.get("base_url")
        model_with_params = build_model_with_params(
            cfg.get("model", "M3"),
            total_steps=cfg.get("total_steps"),
            speed=cfg.get("speed"),
            silence_duration=cfg.get("silence_duration"),
            language=cfg.get("language"),
        )
        return deepgram.TTS(base_url=base_url, model=model_with_params)

    if provider == "kokoro_tts":
        base_url = cfg.get("base_url")
        model_with_params = build_model_with_params(
            cfg.get("model", "am_adam"),
            speed=cfg.get("speed"),
            language=cfg.get("language"),
        )
        return deepgram.TTS(base_url=base_url, model=model_with_params)

    if provider == "chatterbox_tts":
        base_url = cfg.get("base_url")
        model_with_params = build_model_with_params(
            cfg.get("model", "default"),
            voice=cfg.get("voice"),
            exaggeration=cfg.get("exaggeration"),
            cfg_weight=cfg.get("cfg_weight"),
            language=cfg.get("language"),
        )
        return deepgram.TTS(base_url=base_url, model=model_with_params)

    if provider == "chatterbox_turbo_tts":
        base_url = cfg.get("base_url")
        model_with_params = build_model_with_params(
            cfg.get("model", "default"),
            voice=cfg.get("voice"),
            repetition_penalty=cfg.get("repetition_penalty"),
            language=cfg.get("language"),
        )
        return deepgram.TTS(base_url=base_url, model=model_with_params)

    # Default to supertonic_tts
    return deepgram.TTS(
        base_url="http://localhost:18017/v1/speak",
        model="M3",
    )
