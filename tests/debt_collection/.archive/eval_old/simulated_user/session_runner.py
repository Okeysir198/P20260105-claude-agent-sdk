"""
AgentSession wrapper for simulated user testing.

This module provides the AgentSessionRunner class that wraps LiveKit's AgentSession
for use in simulation testing, reusing patterns from the eval framework.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Optional

# Setup path to import from parent eval/ folder
_simulated_user_dir = Path(__file__).parent
_eval_dir = _simulated_user_dir.parent
sys.path.insert(0, str(_eval_dir))

# Import from _provider.py (sibling in eval/)
from _provider import (
    ConversationEvent,
    _extract_events,
    create_agents_for_session,
    create_test_userdata,
    get_default_agent,
    get_llm_model,
    load_agent_config,
)

from livekit.agents import AgentSession

from livekit.plugins import openai

from .types import TurnEvent


class AgentSessionRunner:
    """Manages LiveKit AgentSession for simulation.

    This class wraps the LiveKit AgentSession to provide a clean interface
    for simulated user testing. It handles session lifecycle, message sending,
    and event extraction.

    Usage:
        async with AgentSessionRunner() as runner:
            greeting = runner.get_initial_greeting()
            response, events = await runner.send_message("Hello")
    """

    def __init__(
        self,
        start_agent: str | None = None,
        model: str | None = None,
    ):
        """Initialize the session runner.

        Args:
            start_agent: ID of the agent to start with. Defaults to config default.
            model: LLM model to use. Defaults to config model.
        """
        self.start_agent = start_agent or get_default_agent()
        self.model = model or get_llm_model()
        self.session: AgentSession | None = None
        self.llm = None
        self._started = False
        self._llm_context = None
        self._session_context = None
        self._initial_greeting: str | None = None

    async def __aenter__(self) -> "AgentSessionRunner":
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    async def start(self) -> None:
        """Initialize and start the agent session.

        Creates the LLM, userdata, agents, and starts the session.
        Waits for on_enter to complete (initial greeting).
        """
        if self._started:
            return

        # Create LLM with async context manager
        self.llm = openai.LLM(model=self.model)
        self._llm_context = self.llm
        await self._llm_context.__aenter__()

        # Create test userdata and agents
        userdata = create_test_userdata()
        config = load_agent_config()
        userdata.agents = create_agents_for_session(userdata, config)

        # Get starting agent with fallback
        agent = userdata.agents.get(self.start_agent)
        if agent is None:
            default_agent = get_default_agent()
            agent = userdata.agents.get(default_agent)
        if agent is None and userdata.agents:
            agent = next(iter(userdata.agents.values()))

        if agent is None:
            raise ValueError(
                f"Agent '{self.start_agent}' not found. "
                f"Available: {list(userdata.agents.keys())}"
            )

        # Create and start session
        self.session = AgentSession(llm=self.llm, userdata=userdata)
        self._session_context = self.session
        await self._session_context.__aenter__()

        await self.session.start(agent)

        # Wait for on_enter generate_reply to complete
        await asyncio.sleep(1.5)

        # Capture initial greeting from history
        self._initial_greeting = self._extract_initial_greeting()

        self._started = True

    async def close(self) -> None:
        """Clean up session and LLM resources."""
        if self._session_context is not None:
            try:
                await self._session_context.__aexit__(None, None, None)
            except Exception:
                pass
            self._session_context = None
            self.session = None

        if self._llm_context is not None:
            try:
                await self._llm_context.__aexit__(None, None, None)
            except Exception:
                pass
            self._llm_context = None
            self.llm = None

        self._started = False

    async def send_message(self, user_input: str) -> tuple[str, list[TurnEvent]]:
        """Send user input and get agent response with events.

        Args:
            user_input: The user's message text.

        Returns:
            Tuple of (agent_response_text, list_of_events).

        Raises:
            RuntimeError: If session is not started.
        """
        if not self._started or self.session is None:
            raise RuntimeError("Session not started. Call start() or use async context manager.")

        # Run the session with user input
        run_result = await self.session.run(user_input=user_input)

        # Extract events from the run result
        conversation_events = _extract_events(run_result)

        # Convert ConversationEvent to TurnEvent
        events = self._convert_events(conversation_events)

        # Extract agent response text from events
        agent_response = self._extract_response_text(conversation_events)

        return agent_response, events

    def get_initial_greeting(self) -> str | None:
        """Get the agent's initial greeting from on_enter.

        Returns:
            The initial greeting text, or None if no greeting was generated.
        """
        return self._initial_greeting

    def _extract_initial_greeting(self) -> str | None:
        """Extract the initial greeting from session history.

        Returns:
            The first assistant message text, or None if none found.
        """
        if self.session is None:
            return None

        for item in self.session.history.items:
            if hasattr(item, "role") and item.role == "assistant":
                text = getattr(item, "text_content", "") or ""
                if text:
                    return text
        return None

    def _convert_events(self, conversation_events: list[ConversationEvent]) -> list[TurnEvent]:
        """Convert ConversationEvent list to TurnEvent list.

        Args:
            conversation_events: Events from _extract_events.

        Returns:
            List of TurnEvent objects with timestamps.
        """
        events = []
        now = time.time()

        for event in conversation_events:
            event_type = self._map_event_type(event.type)
            events.append(
                TurnEvent(
                    type=event_type,
                    content=event.content,
                    timestamp=now,
                )
            )

        return events

    def _map_event_type(self, provider_type: str) -> str:
        """Map provider event type to TurnEvent type.

        Args:
            provider_type: Event type from _provider.py.

        Returns:
            Corresponding TurnEvent type string.
        """
        type_mapping = {
            "user_input": "user_message",
            "assistant_message": "agent_message",
            "tool_call": "tool_call",
            "tool_output": "tool_output",
            "handoff": "handoff",
            "error": "error",
        }
        return type_mapping.get(provider_type, "error")

    def _extract_response_text(self, events: list[ConversationEvent]) -> str:
        """Extract the agent's response text from events.

        Args:
            events: List of conversation events.

        Returns:
            Concatenated text from all assistant messages.
        """
        texts = []
        for event in events:
            if event.type == "assistant_message":
                text = event.content.get("text", "")
                if text:
                    texts.append(text)
        return " ".join(texts)
