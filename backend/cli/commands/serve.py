"""Serve command for Claude Agent SDK CLI."""
import sys

try:
    import uvicorn
    _SERVER_DEPS_AVAILABLE = True
except ImportError:
    uvicorn = None
    _SERVER_DEPS_AVAILABLE = False

from agent.display import print_success, print_info, print_error


def serve_command(host: str = '0.0.0.0', port: int = 7001, reload: bool = False):
    """Start FastAPI server for API mode."""
    if not _SERVER_DEPS_AVAILABLE:
        print_error("Failed to import server dependencies")
        print_info("Make sure FastAPI and uvicorn are installed:")
        print_info("  pip install fastapi uvicorn[standard] sse-starlette")
        sys.exit(1)

    print_success(f"Starting server on {host}:{port}")
    if reload:
        print_info("Auto-reload enabled")

    try:
        uvicorn.run(
            "api.main:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info"
        )
    except Exception as e:
        print_error(f"Server error: {e}")
        sys.exit(1)
