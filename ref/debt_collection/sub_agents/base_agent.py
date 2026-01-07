#!/usr/bin/env python3
"""
BaseAgent Class for Debt Collection System

Minimal base agent class that provides:
- Chat context preservation during handoffs
- Silent handoff mechanism with generate_reply(tool_choice="none")
- Shared userdata access

All configuration is handled in agents.py at the session level.
"""

import logging
from typing import Any, Optional

from livekit.agents.voice import Agent, RunContext

from shared_state import UserData

logger = logging.getLogger("debt-collection-agent")

# Type alias for RunContext with UserData
RunContext_T = RunContext[UserData]

# Constants used by BaseAgent
CHAT_CONTEXT_MAX_ITEMS = 6  # Max items from previous agent to include in handoff

# Agent ID Constants
INTRODUCTION = "introduction"
VERIFICATION = "verification"
NEGOTIATION = "negotiation"
PAYMENT = "payment"
CLOSING = "closing"


class BaseAgent(Agent):
    """Base class for all debt collection agents with context preservation.

    Provides:
    - Chat context preservation during handoffs
    - Silent handoff mechanism
    - Shared userdata access
    - Helper methods for conversation management

    All configuration (LLM, STT, TTS, instructions, tools) is provided
    by the session level in agents.py via kwargs.
    """

    def __init__(
        self,
        instructions: str,
        tools: list[Any],
        **kwargs
    ):
        """Initialize base agent.

        Args:
            instructions: Agent prompt/instructions
            tools: List of tool functions for this agent
            **kwargs: Additional Agent arguments (llm, stt, tts from session)
        """
        # Call parent Agent constructor
        # LLM, STT, TTS are provided by the session via kwargs
        super().__init__(
            instructions=instructions,
            tools=tools,
            **kwargs,
        )

        # Centralized logging
        agent_name = self.__class__.__name__
        logger.info(f"Initializing {agent_name}")
        logger.debug(f"{agent_name} initialized with {len(tools)} tools")

    async def on_enter(self) -> None:
        """Called when this agent becomes active.

        Handles:
        - Loading previous agent's chat context
        - Adding current call state as system message
        - Triggering initial reply generation
        """
        agent_name = self.__class__.__name__
        logger.info(f"Entering agent: {agent_name}")

        userdata: UserData = self.session.userdata
        chat_ctx = self.chat_ctx.copy()

        # Add the previous agent's chat history to the current agent
        if isinstance(userdata.prev_agent, Agent):
            truncated_chat_ctx = userdata.prev_agent.chat_ctx.copy(
                exclude_instructions=True, exclude_function_call=False
            ).truncate(max_items=CHAT_CONTEXT_MAX_ITEMS)
            existing_ids = {item.id for item in chat_ctx.items}
            items_copy = [
                item for item in truncated_chat_ctx.items if item.id not in existing_ids
            ]
            chat_ctx.items.extend(items_copy)

        # Add current user data as system message
        chat_ctx.add_message(
            role="system",
            content=f"You are {agent_name} agent. Current call state:\n{userdata.summarize()}",
        )

        await self.update_chat_ctx(chat_ctx)


__all__ = [
    # Classes
    "BaseAgent",
    "RunContext_T",
    # Constants
    "CHAT_CONTEXT_MAX_ITEMS",
    "INTRODUCTION",
    "VERIFICATION",
    "NEGOTIATION",
    "PAYMENT",
    "CLOSING",
]
