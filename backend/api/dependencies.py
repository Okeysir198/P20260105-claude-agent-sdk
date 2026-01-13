"""FastAPI dependency injection."""

from fastapi import Request

from api.services.session_manager import SessionManager
from api.services.conversation_service import ConversationService


def get_session_manager(request: Request) -> SessionManager:
    """Get the session manager from app state."""
    return request.app.state.session_manager


def get_conversation_service(request: Request) -> ConversationService:
    """Get the conversation service from app state."""
    return request.app.state.conversation_service
