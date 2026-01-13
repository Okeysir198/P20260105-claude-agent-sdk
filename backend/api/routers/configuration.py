"""Configuration endpoints for skills and agents."""

from fastapi import APIRouter
from pydantic import BaseModel

from agent.discovery.skills import discover_skills
from agent.core.subagents import get_agents_info as get_subagents_info
from agent.core.agents import get_agents_info, get_default_agent_id


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
    """Top-level agent information model."""
    agent_id: str
    name: str
    type: str
    description: str
    model: str
    read_only: bool
    is_default: bool


class AgentsResponse(BaseModel):
    """Response model for top-level agents list."""
    agents: list[AgentInfo]
    default_agent: str
    total: int


class SubagentInfo(BaseModel):
    """Subagent information model."""
    name: str
    focus: str


class SubagentsResponse(BaseModel):
    """Response model for subagents list."""
    subagents: list[SubagentInfo]
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
    """Get list of available top-level agents.

    Top-level agents are complete agent configurations that can be selected
    when creating a session or conversation. Each agent has specific capabilities,
    model settings, and access permissions.

    Returns:
        List of available agents with full configuration details

    Example:
        {
            "agents": [
                {
                    "agent_id": "general-agent-a1b2c3d4",
                    "name": "General Assistant",
                    "type": "general",
                    "description": "General-purpose coding assistant",
                    "model": "sonnet",
                    "read_only": false,
                    "is_default": true
                }
            ],
            "default_agent": "general-agent-a1b2c3d4",
            "total": 1
        }
    """
    agents_data = get_agents_info()
    agents = [AgentInfo(**agent) for agent in agents_data]
    default_agent = get_default_agent_id()

    return AgentsResponse(
        agents=agents,
        default_agent=default_agent,
        total=len(agents)
    )


@router.get("/subagents", response_model=SubagentsResponse)
async def get_subagents() -> SubagentsResponse:
    """Get list of available subagents.

    Subagents are programmatic agents with specialized prompts and capabilities.
    They can be invoked via the Task tool to handle specific tasks like
    research, code review, file navigation, etc.

    Returns:
        List of available subagents with names and focus areas

    Example:
        {
            "subagents": [
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
    subagents_data = get_subagents_info()
    subagents = [SubagentInfo(**subagent) for subagent in subagents_data]

    return SubagentsResponse(
        subagents=subagents,
        total=len(subagents)
    )
