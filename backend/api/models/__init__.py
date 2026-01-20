"""
API request and response models.

This package contains Pydantic models for validating API requests
and formatting API responses.
"""
from .requests import (
    SendMessageRequest,
    CreateSessionRequest,
    CreateConversationRequest,
    ResumeSessionRequest,
)
from .responses import (
    SessionResponse,
    SessionInfo,
    ErrorResponse,
    CloseSessionResponse,
    DeleteSessionResponse,
    SessionHistoryResponse,
)

__all__ = [
    "SendMessageRequest",
    "CreateSessionRequest",
    "CreateConversationRequest",
    "ResumeSessionRequest",
    "SessionResponse",
    "SessionInfo",
    "ErrorResponse",
    "CloseSessionResponse",
    "DeleteSessionResponse",
    "SessionHistoryResponse",
]
