"""Shared session setup logic for WebSocket and platform workers."""
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path

from agent import PROJECT_ROOT
from agent.core.agent_options import set_email_tools_username, set_media_tools_username, set_media_tools_session_id
from agent.core.file_storage import FileStorage
from agent.core.storage import SessionData

logger = logging.getLogger(__name__)


@dataclass
class SessionIdsResult:
    """Lightweight result from resolve_session_ids — no disk I/O."""
    cwd_id: str
    permission_folders: list[str]
    session_cwd: str  # Computed path string (directory NOT created yet)


@dataclass
class SessionSetupResult:
    """Result of resolving session setup parameters."""
    cwd_id: str
    permission_folders: list[str]
    file_storage: FileStorage
    session_cwd: str


def _compute_session_cwd(username: str, cwd_id: str, base_path: str = "data") -> str:
    """Compute session working directory path without creating it on disk."""
    bp = Path(base_path)
    if not bp.is_absolute():
        bp = PROJECT_ROOT / bp
    return str(bp / username / "files" / cwd_id)


def resolve_session_ids(
    username: str,
    existing_session: SessionData | None,
    resume_session_id: str | None,
) -> SessionIdsResult:
    """Resolve cwd_id, permission_folders, and compute session_cwd path (no disk I/O)."""
    if resume_session_id and existing_session:
        cwd_id = existing_session.cwd_id or resume_session_id
        permission_folders = existing_session.permission_folders or ["/tmp"]
    else:
        cwd_id = str(uuid.uuid4())
        permission_folders = ["/tmp"]

    session_cwd = _compute_session_cwd(username, cwd_id)

    return SessionIdsResult(
        cwd_id=cwd_id,
        permission_folders=permission_folders,
        session_cwd=session_cwd,
    )


def create_session_resources(
    username: str,
    cwd_id: str,
    permission_folders: list[str] | None = None,
) -> SessionSetupResult:
    """Create session resources: FileStorage and set context vars."""
    if permission_folders is None:
        permission_folders = ["/tmp"]

    file_storage = FileStorage(username=username, session_id=cwd_id)
    session_cwd = str(file_storage.get_session_dir())
    file_storage._ensure_directories()

    set_email_tools_username(username)
    set_media_tools_username(username)
    set_media_tools_session_id(cwd_id)

    return SessionSetupResult(
        cwd_id=cwd_id,
        permission_folders=permission_folders,
        file_storage=file_storage,
        session_cwd=session_cwd,
    )


def resolve_session_setup(
    username: str,
    existing_session: SessionData | None,
    resume_session_id: str | None,
) -> SessionSetupResult:
    """Convenience function that runs both resolve_session_ids and create_session_resources."""
    ids = resolve_session_ids(username, existing_session, resume_session_id)
    return create_session_resources(username, ids.cwd_id, ids.permission_folders)
