"""
Agent Factory for Debt Collection Multi-Agent System.

Creates and configures all agents with their instructions and tools.
"""

from pathlib import Path
from typing import Optional
from datetime import datetime, date
import yaml

# Import from specific modules to avoid circular imports
from .base_agent import NEGOTIATION, PAYMENT
from .agent01_introduction import IntroductionAgent
from .agent02_verification import VerificationAgent
from .agent03_negotiation import NegotiationAgent
from .agent04_payment import PaymentAgent
from .agent05_closing import ClosingAgent
from shared_state import UserData

# Define AGENT_CLASSES here to avoid circular import
AGENT_CLASSES = {
    "introduction": IntroductionAgent,
    "verification": VerificationAgent,
    "negotiation": NegotiationAgent,
    "payment": PaymentAgent,
    "closing": ClosingAgent,
}
from business_rules.config import AUTHORITIES
from business_rules import build_negotiation_context, build_payment_context
from tools import get_tools_by_names
from prompts import load_instruction, format_instruction

# Load config
_config_path = Path(__file__).parent.parent / "agent.yaml"
CONFIG = yaml.safe_load(_config_path.read_text()) if _config_path.exists() else {}
SUB_AGENTS = {a["id"]: a for a in CONFIG.get("sub_agents", [])}
VERSIONS = CONFIG.get("versions", {})
ACTIVE_VERSION = CONFIG.get("active_version")  # None = use base prompts

# Agents requiring userdata for dynamic prompts
DYNAMIC_PROMPT_AGENTS = {NEGOTIATION, PAYMENT}


def build_prompt_variables(agent_id: str, userdata: Optional[UserData] = None) -> dict:
    """Build template variables for a given agent."""
    variables = CONFIG.get("variables", {})
    agent_name = variables.get("default_agent_name", "Alex")

    default_authority = AUTHORITIES.get("cartrack", {})

    # Add date/time context so agents know the current date/time
    now = datetime.now()
    today = date.today()

    base_vars = {
        "agent_name": agent_name,
        "authority": default_authority.get("name", "Cartrack Accounts Department"),
        "authority_contact": default_authority.get("contact", "011-250-3000"),
        # Date/time context for agents
        "today": today.strftime("%Y-%m-%d"),
        "today_friendly": today.strftime("%A, %B %d, %Y"),
        "current_time": now.strftime("%H:%M"),
        "current_day": today.strftime("%A"),
        "is_before_2pm": now.hour < 14,
    }

    if not userdata:
        return base_vars

    debtor = userdata.debtor
    call = userdata.call

    base_vars.update({
        "debtor_name": debtor.full_name or "",
        "authority": call.authority or base_vars["authority"],
        "authority_contact": call.authority_contact or base_vars["authority_contact"],
        "outstanding_amount": f"R{debtor.outstanding_amount:,.2f}" if debtor.outstanding_amount else "R0.00",
        "overdue_days": debtor.overdue_days or 0,
        "contact_number": debtor.contact_number or "",
        "email": debtor.email or "",
        "bank_name": debtor.bank_name or "",
        "subscription": f"{debtor.monthly_subscription:.2f}" if debtor.monthly_subscription else "0.00",
        "subscription_date": debtor.salary_date or "",
    })

    if agent_id == NEGOTIATION:
        context = build_negotiation_context(userdata)
        base_vars.update(_flatten_negotiation_context(context))
    elif agent_id == PAYMENT:
        context = build_payment_context(userdata)
        base_vars.update(_flatten_payment_context(context))

    return base_vars


def _flatten_negotiation_context(context: dict) -> dict:
    """Flatten negotiation context from business_rules for Mustache template."""
    consequences_list = "\n".join(f"- {c}" for c in context.get("consequences", []))
    benefits_list = "\n".join(f"- {b}" for b in context.get("benefits", []))

    flat = {
        "reason_for_call": context.get("reason_for_call", ""),
        "consequences_list": consequences_list,
        "benefits_list": benefits_list,
        "max_payments": context.get("max_payments", 2),
    }

    discount = context.get("discount")
    if discount:
        flat["discount_enabled"] = True
        flat["discount_percentage"] = discount.get("percentage", 0)
        flat["settlement_amount"] = discount.get("settlement_amount", "")
        flat["discount_deadline"] = discount.get("deadline", "")
        flat["discount_section"] = (
            f"{discount.get('percentage', 0)}% discount available. "
            f"Settlement: {discount.get('settlement_amount', '')}. "
            f"Valid until {discount.get('deadline', '')}."
        )
    else:
        flat["discount_enabled"] = False
        flat["discount_section"] = "No discount available for this account."

    max_payments = context.get("max_payments", 2)
    flat["payment_options"] = f"Settlement (one-time) or Installment (up to {max_payments} months)"

    return flat


def _flatten_payment_context(context: dict) -> dict:
    """Flatten payment context from business_rules for Mustache template."""
    debicheck_fee = context.get("debicheck_fee", 10)
    subscription = context.get("subscription_amount", 0) or 0

    return {
        "payment_type": context.get("payment_type", "settlement"),
        "debicheck_fee": f"{debicheck_fee:.2f}",
        "subscription_amount": f"{subscription:.2f}",
        "total_with_fee": f"{debicheck_fee + subscription:.2f}",
        "amount": f"{subscription:.2f}",
        "debit_date": "to be confirmed",
        "last_failed_date": "N/A",
        "phone_number": "",
    }


def get_agent_instructions(agent_id: str, userdata: Optional[UserData] = None) -> str:
    """Load and format agent instructions.

    Uses active_version from agent.yaml if set, which determines which
    prompt version to load for each agent.
    """
    agent_cfg = SUB_AGENTS.get(agent_id, {})
    source = agent_cfg.get("instructions", "")

    # Determine prompt_version from active_version config
    prompt_version = None
    if ACTIVE_VERSION and ACTIVE_VERSION in VERSIONS:
        version_config = VERSIONS[ACTIVE_VERSION]
        sub_agents = version_config.get("sub_agents", {})
        agent_version_cfg = sub_agents.get(agent_id, {})
        prompt_version = agent_version_cfg.get("prompt_version")

    template = load_instruction(source, version=prompt_version)
    variables = build_prompt_variables(agent_id, userdata)

    return format_instruction(template, **variables)


def create_agents(userdata: UserData) -> dict:
    """Create all agents using AGENT_CLASSES."""
    agents = {}
    for agent_id, agent_class in AGENT_CLASSES.items():
        agent_cfg = SUB_AGENTS.get(agent_id, {})
        tools = agent_cfg.get("tools", [])

        # Dynamic prompts for negotiation/payment, static for others
        ud = userdata if agent_id in DYNAMIC_PROMPT_AGENTS else None

        agents[agent_id] = agent_class(
            instructions=get_agent_instructions(agent_id, ud),
            tools=get_tools_by_names(tools),
        )
    return agents
