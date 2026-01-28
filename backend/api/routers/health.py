"""Health check endpoints for load balancer and monitoring."""
from fastapi import APIRouter
from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Response model for health check endpoints.

    Attributes:
        status: Health status ("ok" or "error").
        service: Optional service name for identification.
    """

    status: str
    service: str | None = None


router = APIRouter(tags=["health"])


@router.get("/", response_model=HealthResponse)
async def root() -> HealthResponse:
    """Root endpoint for load balancer health checks.

    Returns:
        HealthResponse with status "ok".
    """
    return HealthResponse(status="ok")


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint.

    Returns:
        HealthResponse with status "ok" and service name.
    """
    return HealthResponse(status="ok", service="agent-sdk-api")
