"""
Agent Factory for Debt Collection Multi-Agent System.

Creates and configures all agents with their instructions and tools.
"""

from pathlib import Path
from typing import Optional
import yaml

# Import agent classes
from .agent01_introduction import IntroductionAgent
from .agent02_verification import VerificationAgent
from .agent03_negotiation import NegotiationAgent
from .agent04_payment import PaymentAgent
from .agent05_closing import ClosingAgent
from shared_state import UserData
from tools import get_tools_by_names
from prompts import load_prompt, format_prompt

# Define AGENT_CLASSES here for export
AGENT_CLASSES = {
    "introduction": IntroductionAgent,
    "verification": VerificationAgent,
    "negotiation": NegotiationAgent,
    "payment": PaymentAgent,
    "closing": ClosingAgent,
}

# Load config
_config_path = Path(__file__).parent.parent / "agent.yaml"
CONFIG = yaml.safe_load(_config_path.read_text()) if _config_path.exists() else {}
SUB_AGENTS = {a["id"]: a for a in CONFIG.get("sub_agents", [])}


def build_prompt_variables(agent_id: str, userdata: Optional[UserData] = None) -> dict:
    """Build template variables for a given agent."""
    variables = CONFIG.get("variables", {})
    agent_name = variables.get("default_agent_name", "Alex")

    base_vars = {
        "agent_name": agent_name,
    }

    if not userdata:
        return base_vars

    debtor = userdata.debtor
    call = userdata.call

    base_vars.update({
        "debtor_name": debtor.full_name or "",
        "outstanding_amount": f"R{debtor.outstanding_amount:,.2f}" if debtor.outstanding_amount else "R0.00",
        "overdue_days": debtor.overdue_days or 0,
        "contact_number": debtor.contact_number or "",
        "email": debtor.email or "",
    })

    return base_vars


def get_agent_instructions(agent_id: str, userdata: Optional[UserData] = None) -> str:
    """Load and format agent instructions."""
    agent_cfg = SUB_AGENTS.get(agent_id, {})
    source = agent_cfg.get("instructions", "")

    # Load prompt YAML
    prompt_data = load_prompt(source.replace(".yaml", ""))
    template = prompt_data.get("prompt", "")
    variables = build_prompt_variables(agent_id, userdata)

    return format_prompt(template, **variables)


def create_agents(userdata: UserData) -> dict:
    """Create all agents using AGENT_CLASSES."""
    agents = {}
    for agent_id, agent_class in AGENT_CLASSES.items():
        agent_cfg = SUB_AGENTS.get(agent_id, {})
        tools = agent_cfg.get("tools", [])

        agents[agent_id] = agent_class(
            instructions=get_agent_instructions(agent_id, userdata),
            tools=get_tools_by_names(tools),
        )
    return agents
