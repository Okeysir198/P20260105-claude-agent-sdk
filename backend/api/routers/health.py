from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/")
async def root():
    """Root endpoint for load balancer health checks."""
    return {"status": "ok"}


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "agent-sdk-api"}
