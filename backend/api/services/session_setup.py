"""Shared session setup logic for WebSocket and platform workers."""
import logging
import uuid
from dataclasses import dataclass

from agent.core.agent_options import set_email_tools_username, set_media_tools_username, set_media_tools_session_id
from agent.core.file_storage import FileStorage
from agent.core.storage import SessionData

logger = logging.getLogger(__name__)

# Email tools initialization
try:
    from agent.tools.email.mcp_server import initialize_email_tools
except ImportError:
    logger.warning("Email tools initialization function not available")
    initialize_email_tools = None


@dataclass
class SessionSetupResult:
    """Result of resolving session setup parameters."""
    cwd_id: str
    permission_folders: list[str]
    file_storage: FileStorage
    session_cwd: str


def resolve_session_setup(
    username: str,
    existing_session: SessionData | None,
    resume_session_id: str | None,
) -> SessionSetupResult:
    """Resolve cwd_id, permission_folders, and create FileStorage for a session.

    For resumed sessions, uses the stored cwd_id and permission_folders.
    For new sessions, generates a fresh UUID-based cwd_id.

    Also sets the email tools username context for per-user credential lookup.

    Args:
        username: Authenticated username for storage isolation.
        existing_session: Existing session data if resuming, or None.
        resume_session_id: Session ID being resumed, or None for new sessions.

    Returns:
        SessionSetupResult with resolved cwd_id, permission_folders,
        FileStorage instance, and session working directory path.
    """
    if resume_session_id and existing_session:
        cwd_id = existing_session.cwd_id or resume_session_id
        permission_folders = existing_session.permission_folders or ["/tmp"]
    else:
        cwd_id = str(uuid.uuid4())
        permission_folders = ["/tmp"]

    file_storage = FileStorage(username=username, session_id=cwd_id)
    session_cwd = str(file_storage.get_session_dir())

    set_email_tools_username(username)
    set_media_tools_username(username)
    set_media_tools_session_id(cwd_id)

    if initialize_email_tools is not None:
        initialize_email_tools(username)

    return SessionSetupResult(
        cwd_id=cwd_id,
        permission_folders=permission_folders,
        file_storage=file_storage,
        session_cwd=session_cwd,
    )
