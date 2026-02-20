# Media Tools MCP Server

OCR, STT, and TTS tools for the Claude Agent SDK.

## Overview

This MCP server provides tools for:
- **OCR**: Extract text from images and PDFs using GLM-OCR
- **STT**: Transcribe audio using Whisper V3 Turbo or Nemotron Speech
- **TTS**: Synthesize speech using Kokoro, Supertonic, or Chatterbox engines

All services run as local Docker containers on localhost.

## Services

### OCR (Optical Character Recognition)
- **Service**: Ollama GLM-OCR
- **Port**: 18013
- **Features**: Vietnamese OCR, layout detection, semantic tagging
- **Formats**: PDF, PNG, JPG, JPEG, TIFF, BMP, WEBP

### STT (Speech-to-Text)
- **Whisper V3 Turbo** (Port 18050): High-accuracy, ~180-2200ms latency, multilingual
- **Nemotron Speech** (Port 18052): Ultra-low ~14-15ms TTFB, English only

### TTS (Text-to-Speech)
- **Kokoro** (Port 18034): Lightweight multi-language, WAV output
- **SupertonicTTS v1.1** (Port 18030): Deepgram Aura proxy, MP3 output
- **Chatterbox Turbo** (Port 18033): Voice cloning, requires reference audio

## Installation

The media tools require `httpx` for HTTP client operations:

```bash
cd backend
pip install httpx
```

## Configuration

### Environment Variables (Optional)

```bash
# OCR Service (optional - only if authentication is enabled)
VLLM_API_KEY=your_api_key

# TTS Service (uses "dummy" by default for local SupertonicTTS)
DEEPGRAM_API_KEY=dummy
```

### Service URLs

Default service URLs are defined in `config.py`:

```python
OCR_SERVICE_URL = "http://localhost:18013"
STT_WHISPER_URL = "http://localhost:18050"
STT_NEMOTRON_URL = "http://localhost:18052"
TTS_SUPERTONIC_URL = "http://localhost:18030"
TTS_CHATTERBOX_URL = "http://localhost:18033"
TTS_KOKORO_URL = "http://localhost:18034"
```

## Usage

### Agent Configuration

Media tools are automatically available to all agents via `_defaults` in `agents.yaml`:

```yaml
_defaults:
  tools:
    - mcp__media_tools__perform_ocr
    - mcp__media_tools__list_stt_engines
    - mcp__media_tools__transcribe_audio
    - mcp__media_tools__list_tts_engines
    - mcp__media_tools__synthesize_speech
```

### Tool Examples

#### OCR - Extract Text from Images/PDFs

```python
# Agent tool call
inputs = {
    "file_path": "document.pdf",  # Relative to session input directory
    "apply_vietnamese_corrections": False
}
result = await perform_ocr(inputs)
# Returns: {text, output_path, processing_time_ms, pages}
```

#### STT - Transcribe Audio

```python
# First, list available engines
engines = await list_stt_engines({})

# Then transcribe
inputs = {
    "file_path": "recording.wav",
    "engine": "whisper_v3_turbo",
    "language": "auto"  # or "en", "vi", etc.
}
result = await transcribe_audio(inputs)
# Returns: {text, output_path, engine, confidence, duration_ms, language}
```

#### TTS - Synthesize Speech

```python
# First, list available engines and voices
engines = await list_tts_engines({})

# Then synthesize
inputs = {
    "text": "Hello, world!",
    "engine": "kokoro",
    "voice": "af_heart",
    "speed": 1.0
}
result = await synthesize_speech(inputs)
# Returns: {audio_path, format, engine, voice, text, duration_ms}
```

## File Storage

Media tools use the existing `FileStorage` class for per-user, per-session file management:

- **Input files**: `data/{username}/files/{session_id}/input/`
- **Output files**: `data/{username}/files/{session_id}/output/`

All file paths in tool inputs are relative to the session's input directory.

## Per-User Isolation

The media tools use `contextvars` for thread-safe username isolation, following the same pattern as email tools:

```python
# In agent_options.py
def set_media_tools_username(username: str) -> None:
    """Set username context for media operations."""
    from agent.tools.media.mcp_server import set_username
    set_username(username)
```

## Testing

Run tests with pytest:

```bash
cd backend
pytest tests/test_media_tools.py -v
```

Tests include:
- Configuration validation
- Client initialization
- Tool registration
- FileStorage integration
- Service health checks (requires running services)

## Troubleshooting

### Services Not Available

If media tools show as unavailable:

1. Check Docker containers are running:
   ```bash
   docker ps | grep -E "18013|18050|18030|18033|18034"
   ```

2. Verify service health:
   ```bash
   curl http://localhost:18013/health  # OCR
   curl http://localhost:18050/health  # STT
   curl http://localhost:18034/health  # TTS
   ```

3. Check logs:
   ```bash
   docker logs <container_name>
   ```

### Import Errors

If `httpx` is not installed:

```bash
pip install httpx
```

The media tools will gracefully degrade if dependencies are missing, logging a warning at startup.

### File Not Found Errors

Ensure files are uploaded via the file upload API before processing:

```python
# Upload file first via API
POST /api/v1/files/upload

# Then reference in tool call by filename only
inputs = {"file_path": "document.pdf"}
```

## Architecture

```
agent/tools/media/
├── __init__.py              # Package init
├── config.py                # Service URLs and configuration
├── mcp_server.py            # MCP server registration
├── ocr_tools.py             # OCR tool implementations
├── stt_tools.py             # STT tool implementations
├── tts_tools.py             # TTS tool implementations
└── clients/
    ├── __init__.py
    ├── base_client.py       # Base HTTP client
    ├── ocr_client.py        # OCR service client
    ├── stt_client.py        # STT service client
    └── tts_client.py        # TTS service client
```

## See Also

- `backend/agent/tools/email/` - Email MCP server (same pattern)
- `backend/agent/core/file_storage.py` - File storage utilities
- `backend/agents.yaml` - Agent configuration with tool definitions
