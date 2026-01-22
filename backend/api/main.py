"""FastAPI application factory for Agent SDK API."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from api.config import API_CONFIG
from api.core.errors import SessionNotFoundError, APIError
from api.routers import health, sessions, conversations, configuration, websocket
from api.middleware.auth import APIKeyMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan handler for startup and shutdown events."""
    # Startup - ensure storage directories exist
    from agent.core.storage import get_storage, get_history_storage
    get_storage()  # Creates data/ and sessions.json
    get_history_storage()  # Creates data/history/

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
