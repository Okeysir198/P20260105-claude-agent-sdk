"""
Sub-agents package for debt collection multi-agent system.

Exports agent classes and factory function.
"""

from .base_agent import (
    BaseAgent,
    RunContext_T,
    INTRODUCTION,
    VERIFICATION,
    NEGOTIATION,
    PAYMENT,
    CLOSING,
)
from .factory import create_agents, AGENT_CLASSES
from .agent01_introduction import IntroductionAgent
from .agent02_verification import VerificationAgent
from .agent03_negotiation import NegotiationAgent
from .agent04_payment import PaymentAgent
from .agent05_closing import ClosingAgent

__all__ = [
    # Base
    "BaseAgent",
    "RunContext_T",
    # Constants
    "INTRODUCTION",
    "VERIFICATION",
    "NEGOTIATION",
    "PAYMENT",
    "CLOSING",
    # Factory
    "create_agents",
    "AGENT_CLASSES",
    # Agent classes
    "IntroductionAgent",
    "VerificationAgent",
    "NegotiationAgent",
    "PaymentAgent",
    "ClosingAgent",
]
