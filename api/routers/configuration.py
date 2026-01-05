"""Configuration endpoints for skills and agents."""

from fastapi import APIRouter
from pydantic import BaseModel

from agent.discovery.skills import discover_skills
from agent.core.agents import get_agents_info


router = APIRouter(tags=["configuration"])


# Response Models
class SkillInfo(BaseModel):
    """Skill information model."""
    name: str
    description: str


class SkillsResponse(BaseModel):
    """Response model for skills list."""
    skills: list[SkillInfo]
    total: int


class AgentInfo(BaseModel):
    """Agent information model."""
    name: str
    focus: str


class AgentsResponse(BaseModel):
    """Response model for agents list."""
    agents: list[AgentInfo]
    total: int


# Endpoints
@router.get("/skills", response_model=SkillsResponse)
async def get_skills() -> SkillsResponse:
    """Get list of available skills from .claude/skills/ directory.

    Skills are filesystem-based capabilities that extend Claude's functionality.
    They are automatically discovered from the .claude/skills/ directory.

    Returns:
        List of available skills with names and descriptions

    Example:
        {
            "skills": [
                {
                    "name": "code-analyzer",
                    "description": "Analyze Python code for patterns and issues"
                },
                {
                    "name": "doc-generator",
                    "description": "Generate documentation for code"
                }
            ],
            "total": 2
        }
    """
    skills_data = discover_skills()
    skills = [SkillInfo(**skill) for skill in skills_data]

    return SkillsResponse(
        skills=skills,
        total=len(skills)
    )


@router.get("/agents", response_model=AgentsResponse)
async def get_agents() -> AgentsResponse:
    """Get list of available subagents.

    Subagents are programmatic agents with specialized prompts and capabilities.
    They can be invoked to handle specific tasks like research, code review, etc.

    Returns:
        List of available agents with names and focus areas

    Example:
        {
            "agents": [
                {
                    "name": "researcher",
                    "focus": "Code exploration and analysis"
                },
                {
                    "name": "reviewer",
                    "focus": "Code review and quality checks"
                }
            ],
            "total": 2
        }
    """
    agents_data = get_agents_info()
    agents = [AgentInfo(**agent) for agent in agents_data]

    return AgentsResponse(
        agents=agents,
        total=len(agents)
    )
