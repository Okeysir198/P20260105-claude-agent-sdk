"""Configuration management endpoints.

Provides endpoint to list available agents.
"""
from fastapi import APIRouter

from agent.core.agents import get_agents_info

router = APIRouter(tags=["config"])


@router.get("/agents")
async def list_agents():
    """List top-level agents.

    Returns all registered agents that can be selected via agent_id.
    """
    agents = get_agents_info()
    return {"agents": agents}
