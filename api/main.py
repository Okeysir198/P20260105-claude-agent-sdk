"""FastAPI application main entry point."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.routers import health, sessions, conversations, configuration
from api.services.session_manager import SessionManager
from api.services.conversation_service import ConversationService

logger = logging.getLogger(__name__)


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

    logger.info("Services initialized successfully")

    yield

    # Shutdown - cleanup all active sessions
    logger.info(f"Shutting down {settings.app_name}")

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
