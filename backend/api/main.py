"""FastAPI application factory for Agent SDK API."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Configure root logger so application loggers (api.*, agent.*) output to console
logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s: %(message)s")

from api.config import API_CONFIG
from api.core.errors import SessionNotFoundError, APIError
from api.routers import health, sessions, conversations, configuration, websocket, auth, user_auth, files
from api.middleware.auth import APIKeyMiddleware
from api.db.user_database import init_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan handler for startup and shutdown events."""
    # Initialize user database
    init_database()

    yield
    # Shutdown - cleanup all background workers
    from api.services.session_manager import get_session_manager
    manager = get_session_manager()
    for session in manager._sessions.values():
        await session.shutdown()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.
    
    Returns:
        FastAPI: Configured FastAPI application instance
    """
    app = FastAPI(
        title="Agent SDK API",
        description="REST API for managing Claude Agent SDK sessions and conversations",
        version="0.1.0",
        lifespan=lifespan,
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=API_CONFIG["cors_origins"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*", "X-API-Key"],
    )

    # Add API key authentication middleware (after CORS)
    app.add_middleware(APIKeyMiddleware)
    
    # Include routers
    app.include_router(health.router, tags=["health"])
    app.include_router(
        auth.router,
        prefix="/api/v1",
        tags=["authentication"]
    )
    app.include_router(
        sessions.router,
        prefix="/api/v1",
        tags=["sessions"]
    )
    app.include_router(
        conversations.router,
        prefix="/api/v1",
        tags=["conversations"]
    )
    app.include_router(
        configuration.router,
        prefix="/api/v1/config",
        tags=["config"]
    )
    app.include_router(
        websocket.router,
        prefix="/api/v1",
        tags=["websocket"]
    )
    app.include_router(
        user_auth.router,
        prefix="/api/v1",
        tags=["user-auth"]
    )
    app.include_router(
        files.router,
        prefix="/api/v1",
        tags=["files"]
    )

    # Global exception handlers
    @app.exception_handler(SessionNotFoundError)
    async def session_not_found_handler(request: Request, exc: SessionNotFoundError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"message": exc.message, "session_id": exc.session_id}
        )

    @app.exception_handler(APIError)
    async def api_error_handler(request: Request, exc: APIError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"message": exc.message, "details": exc.details}
        )

    return app


# Global app instance
app = create_app()


if __name__ == "__main__":
    # Run the application with uvicorn
    uvicorn.run(
        "api.main:app",
        host=API_CONFIG["host"],
        port=API_CONFIG["port"],
        reload=API_CONFIG["reload"],
        log_level=API_CONFIG["log_level"],
    )
