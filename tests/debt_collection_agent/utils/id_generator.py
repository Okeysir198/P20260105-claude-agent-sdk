"""Session ID generation utilities."""

import random
import string
from datetime import datetime


def generate_session_id() -> str:
    """
    Generate a unique session ID.

    Returns:
        Session ID string in format: SESSION_YYYYMMDD_HHMMSS_XXXX
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"SESSION_{timestamp}_{random_str}"
