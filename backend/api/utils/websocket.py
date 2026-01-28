"""WebSocket utility functions."""

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect


async def close_with_error(
    websocket: WebSocket,
    code: int,
    reason: str,
    raise_disconnect: bool = True
) -> None:
    """Close WebSocket connection with error code and optionally raise disconnect.

    Args:
        websocket: The WebSocket connection to close.
        code: The close code to send.
        reason: The reason string for the close.
        raise_disconnect: If True, raises WebSocketDisconnect after closing.

    Raises:
        WebSocketDisconnect: If raise_disconnect is True.
    """
    await websocket.close(code=code, reason=reason)
    if raise_disconnect:
        raise WebSocketDisconnect(code=code, reason=reason)
