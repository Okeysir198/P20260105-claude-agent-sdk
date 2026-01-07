"""Unique agent ID generation.

Usage:
    generate_agent_id("debt-collection") -> "debt-collection-abc123"
    generate_sub_agent_id("debt-collection-abc123", "introduction") -> "introduction-abc123-def456"
    generate_session_id() -> "session-abc123def456"
"""
import hashlib
import uuid
from datetime import datetime


def generate_agent_id(base_name: str, length: int = 6) -> str:
    """Generate unique agent ID with hash suffix."""
    seed = f"{datetime.now().isoformat()}-{uuid.uuid4()}"
    suffix = hashlib.sha256(seed.encode()).hexdigest()[:length]
    return f"{base_name}-{suffix}"


def generate_sub_agent_id(parent_id: str, sub_agent_name: str) -> str:
    """Generate sub-agent ID derived from parent."""
    parent_suffix = parent_id.split("-")[-1]
    unique = hashlib.sha256(f"{parent_id}-{sub_agent_name}".encode()).hexdigest()[:6]
    return f"{sub_agent_name}-{parent_suffix}-{unique}"


def generate_session_id() -> str:
    """Generate unique session ID."""
    seed = f"{datetime.now().isoformat()}-{uuid.uuid4()}"
    return f"session-{hashlib.sha256(seed.encode()).hexdigest()[:12]}"
