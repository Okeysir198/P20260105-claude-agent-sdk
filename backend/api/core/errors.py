"""Shared error handling utilities for API routers."""

from functools import wraps
from typing import Callable, TypeVar

from fastapi import HTTPException, status


T = TypeVar("T")


def raise_not_found(detail: str) -> None:
    """Raise a 404 Not Found HTTPException."""
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def raise_internal_error(detail: str) -> None:
    """Raise a 500 Internal Server Error HTTPException."""
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)


def handle_service_errors(operation_name: str) -> Callable:
    """Decorator for standardized service error handling.

    Converts ValueError to 404 Not Found and other exceptions to 500 Internal Server Error.

    Args:
        operation_name: Human-readable name of the operation for error messages

    Returns:
        Decorated async function with standardized error handling
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            try:
                return await func(*args, **kwargs)
            except ValueError as e:
                raise_not_found(str(e))
            except HTTPException:
                raise
            except Exception as e:
                raise_internal_error(f"Failed to {operation_name}: {str(e)}")
        return wrapper
    return decorator
