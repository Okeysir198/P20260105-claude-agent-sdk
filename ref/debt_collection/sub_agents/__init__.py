"""Sub-Agents Package for Debt Collection Multi-Agent System.

Agent Flow:
    Introduction -> Verification -> Negotiation -> Payment -> Closing

Each agent inherits from BaseAgent which provides:
    - Chat context preservation during handoffs
    - Silent handoff mechanism
    - Shared userdata access
"""

# Import base components first (no circular deps)
from .base_agent import (
    BaseAgent,
    INTRODUCTION,
    VERIFICATION,
    NEGOTIATION,
    PAYMENT,
    CLOSING,
)

# Import agent classes
from .agent01_introduction import IntroductionAgent
from .agent02_verification import VerificationAgent
from .agent03_negotiation import NegotiationAgent
from .agent04_payment import PaymentAgent
from .agent05_closing import ClosingAgent

# Import factory functions and AGENT_CLASSES (defined in factory to avoid circular import)
from .factory import create_agents, AGENT_CLASSES

__all__ = [
    # Base
    "BaseAgent",
    # Agents
    "IntroductionAgent",
    "VerificationAgent",
    "NegotiationAgent",
    "PaymentAgent",
    "ClosingAgent",
    # Constants
    "AGENT_CLASSES",
    "INTRODUCTION",
    "VERIFICATION",
    "NEGOTIATION",
    "PAYMENT",
    "CLOSING",
    # Factory
    "create_agents",
]
