"""Session ID generation utilities."""

import time


def generate_pending_session_id() -> str:
    """Generate a unique pending session ID based on timestamp.

    Returns:
        A unique session ID string with 'pending-' prefix and millisecond timestamp.
    """
    return f"pending-{int(time.time() * 1000)}"
