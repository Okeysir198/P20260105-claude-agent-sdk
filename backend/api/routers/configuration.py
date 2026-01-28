"""Configuration management endpoints.

Provides endpoint to list available agents.
"""
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from agent.core.agents import get_agents_info


class AgentsListResponse(BaseModel):
    """Response model for listing available agents.

    Attributes:
        agents: List of agent information dictionaries.
    """

    agents: list[dict[str, Any]] = Field(
        ...,
        description="List of available agents with their metadata"
    )


router = APIRouter(tags=["config"])


@router.get("/agents", response_model=AgentsListResponse)
async def list_agents() -> AgentsListResponse:
    """List top-level agents.

    Returns:
        AgentsListResponse with all registered agents that can be selected via agent_id.
    """
    agents = get_agents_info()
    return AgentsListResponse(agents=agents)
