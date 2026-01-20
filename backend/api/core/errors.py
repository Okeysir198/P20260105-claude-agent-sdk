"""
Custom exceptions for the API.

This module defines application-specific exceptions that map to
appropriate HTTP status codes.
"""

from typing import Any, Dict, Optional


class APIError(Exception):
    """Base exception for API errors."""

    def __init__(self, status_code: int, message: str, details: Optional[Dict[str, Any]] = None):
        self.status_code = status_code
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class SessionNotFoundError(APIError):
    """Exception raised when a session is not found."""

    def __init__(self, session_id: str, details: Optional[Dict[str, Any]] = None):
        self.session_id = session_id
        super().__init__(
            status_code=404,
            message=f"Session '{session_id}' not found",
            details=details
        )


class SessionStateError(APIError):
    """Exception raised when a session is in an invalid state for the requested operation."""

    def __init__(self, session_id: str, state: str, details: Optional[Dict[str, Any]] = None):
        self.session_id = session_id
        self.state = state
        super().__init__(
            status_code=409,
            message=f"Session '{session_id}' is in invalid state '{state}' for this operation",
            details=details
        )


class InvalidRequestError(APIError):
    """Exception raised when a request is invalid."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=400,
            message=message,
            details=details
        )
