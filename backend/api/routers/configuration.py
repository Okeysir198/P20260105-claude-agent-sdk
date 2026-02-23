"""Configuration management endpoints."""
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from agent.core.agents import get_agents_info


class AgentsListResponse(BaseModel):
    agents: list[dict[str, Any]] = Field(
        ...,
        description="List of available agents with their metadata"
    )


router = APIRouter(tags=["config"])


@router.get("/agents", response_model=AgentsListResponse)
async def list_agents() -> AgentsListResponse:
    """List top-level agents."""
    return AgentsListResponse(agents=get_agents_info())
