"""FastAPI application main entry point."""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.routers import health, sessions, conversations, configuration
from api.services.session_manager import SessionManager, SESSION_TTL_SECONDS
from api.services.conversation_service import ConversationService

logger = logging.getLogger(__name__)

# Cleanup interval (run every 5 minutes)
CLEANUP_INTERVAL_SECONDS = 300


async def periodic_session_cleanup(session_manager: SessionManager) -> None:
    """Background task to periodically clean up expired sessions.

    Runs every CLEANUP_INTERVAL_SECONDS and removes sessions that have
    exceeded their TTL.
    """
    logger.info(f"Starting periodic session cleanup (interval={CLEANUP_INTERVAL_SECONDS}s, TTL={SESSION_TTL_SECONDS}s)")
    while True:
        try:
            await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
            cleaned_count = await session_manager.cleanup_expired_sessions()
            if cleaned_count > 0:
                logger.info(f"Periodic cleanup: removed {cleaned_count} expired session(s)")
            else:
                logger.debug("Periodic cleanup: no expired sessions found")
        except asyncio.CancelledError:
            logger.info("Periodic session cleanup task cancelled")
            break
        except Exception as e:
            logger.error(f"Error in periodic session cleanup: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info(f"Starting {settings.app_name} on {settings.host}:{settings.port}")

    # Initialize services
    session_manager = SessionManager()
    conversation_service = ConversationService(session_manager)

    # Store in app state for dependency injection
    app.state.session_manager = session_manager
    app.state.conversation_service = conversation_service

    # Start background cleanup task
    cleanup_task = asyncio.create_task(periodic_session_cleanup(session_manager))
    app.state.cleanup_task = cleanup_task

    logger.info("Services initialized successfully")

    yield

    # Shutdown - cancel cleanup task
    logger.info(f"Shutting down {settings.app_name}")
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass

    # Cleanup all active sessions

    active_sessions = session_manager.list_sessions()
    for session in active_sessions:
        try:
            await session_manager.close_session(session.session_id)
            logger.info(f"Closed session: {session.session_id}")
        except Exception as e:
            logger.error(f"Error closing session {session.session_id}: {e}")

    logger.info(f"Cleaned up {len(active_sessions)} session(s)")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
    debug=settings.debug,
)

# Add CORS middleware (allow all for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(
    sessions.router,
    prefix=f"{settings.api_v1_prefix}/sessions",
    tags=["Sessions"],
)
app.include_router(
    conversations.router,
    prefix=f"{settings.api_v1_prefix}/conversations",
    tags=["Conversations"],
)
app.include_router(
    configuration.router,
    prefix=f"{settings.api_v1_prefix}/config",
    tags=["Configuration"],
)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": "1.0.0",
        "docs": "/docs",
    }
