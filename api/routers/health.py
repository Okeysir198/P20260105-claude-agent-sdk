"""Health check router."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """
    Health check endpoint.

    Returns:
        dict: Health status response
    """
    return {"status": "healthy"}
