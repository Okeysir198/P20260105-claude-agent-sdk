"""Health check router."""

from dataclasses import dataclass
from fastapi import APIRouter, Request
from typing import Optional

router = APIRouter()


@dataclass
class PoolStatsResponse:
    """Response model for pool statistics."""
    pool_size: int
    available_clients: int
    busy_clients: int
    total_acquisitions: int


@dataclass
class SessionStatsResponse:
    """Response model for session statistics."""
    total_sessions: int
    active_sessions: int
    expired_sessions: int
    pool_utilization: float


@router.get("/health")
async def health_check() -> dict[str, str]:
    """
    Health check endpoint.

    Returns:
        dict: Health status response
    """
    return {"status": "healthy"}


@router.get("/stats/pool", response_model=PoolStatsResponse)
async def get_pool_stats(request: Request) -> PoolStatsResponse:
    """Get client pool statistics.

    Returns statistics about the session manager's client pool utilization.

    Args:
        request: FastAPI request object with app state

    Returns:
        PoolStatsResponse with current pool metrics
    """
    session_manager = request.app.state.session_manager
    sessions = session_manager.list_sessions()

    # Calculate pool statistics from active sessions
    total_sessions = len(sessions)
    active_count = sum(1 for s in sessions if s.status == "active")
    idle_count = sum(1 for s in sessions if s.status == "idle")

    return PoolStatsResponse(
        pool_size=total_sessions,
        available_clients=idle_count,
        busy_clients=active_count,
        total_acquisitions=sum(s.turn_count for s in sessions),
    )


@router.get("/stats/sessions", response_model=SessionStatsResponse)
async def get_session_stats(request: Request) -> SessionStatsResponse:
    """Get session statistics.

    Returns comprehensive statistics about session management including
    active, expired, and pool utilization metrics.

    Args:
        request: FastAPI request object with app state

    Returns:
        SessionStatsResponse with current session metrics
    """
    session_manager = request.app.state.session_manager
    sessions = session_manager.list_sessions()

    # Count active vs idle sessions
    active_count = sum(1 for s in sessions if s.status == "active")
    idle_count = sum(1 for s in sessions if s.status == "idle")
    total_active = len(sessions)

    # Calculate pool utilization (active / total capacity)
    from api.services.session_manager import MAX_SESSIONS
    pool_utilization = round((total_active / MAX_SESSIONS) * 100, 2) if MAX_SESSIONS > 0 else 0.0

    # Count expired sessions (those that would be cleaned up)
    from datetime import datetime
    from api.services.session_manager import SESSION_TTL_SECONDS
    now = datetime.now()
    expired_count = sum(
        1 for s in sessions
        if (now - s.last_accessed_at).total_seconds() > SESSION_TTL_SECONDS
    )

    return SessionStatsResponse(
        total_sessions=total_active,
        active_sessions=active_count,
        expired_sessions=expired_count,
        pool_utilization=pool_utilization,
    )
