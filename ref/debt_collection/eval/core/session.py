"""Test session wrapper for LiveKit AgentSession."""

from __future__ import annotations

import asyncio
from typing import Optional, Any, Callable

from livekit.agents import AgentSession, Agent
from livekit.plugins import openai as livekit_openai

from .config import EvalConfig
from .loader import (
    create_test_userdata, get_agent_classes, get_tools_function,
    load_agent_config, load_instructions
)
from .events import extract_events, get_response_text
from ..schemas.models import Turn, TurnEvent


class TestSession:
    """Wrapper for running test conversations with LiveKit agents."""

    def __init__(
        self,
        start_agent: Optional[str] = None,
        model: str = None,  # type: ignore[assignment] - Required, checked below
        temperature: float = None,  # type: ignore[assignment] - Required, checked below
        config: Optional[EvalConfig] = None,
        llm_factory: Optional[Callable[[str, float], Any]] = None,
        greeting_timeout: float = 3.0,
        test_data: Optional[dict] = None,
        version: Optional[str] = None,
    ):
        """Initialize test session.

        Args:
            start_agent: Starting agent ID from agent.yaml
            model: LLM model identifier (REQUIRED - no fallback)
            temperature: LLM temperature (REQUIRED - no fallback)
            config: Optional EvalConfig instance
            llm_factory: Factory function (model: str, temperature: float) -> LLM
            greeting_timeout: Seconds to wait for initial greeting
            test_data: Test-specific data to override defaults from YAML
            version: Optional version string for instruction loading

        Raises:
            ValueError: If model or temperature not provided
        """
        # STRICT: No fallbacks - model and temperature must be explicitly provided
        if model is None:
            raise ValueError(
                "model is required. Use EvalRunner or interactive_session which resolve config automatically."
            )
        if temperature is None:
            raise ValueError(
                "temperature is required. Use EvalRunner or interactive_session which resolve config automatically."
            )

        self.config = config or EvalConfig.load()
        self.start_agent = start_agent or self.config.default_agent
        self.model = model
        self.temperature = temperature
        self.llm_factory = llm_factory or self._default_llm_factory
        self.greeting_timeout = greeting_timeout
        self.test_data = test_data
        self.version = version
        self._session: Optional[AgentSession] = None
        self._llm = None
        self._started = False
        self._initial_greeting: Optional[str] = None
        self._userdata = None

    def _default_llm_factory(self, model: str, temperature: float = 0.8):
        """Create OpenAI LLM (default provider)."""
        return livekit_openai.LLM(model=model, temperature=temperature)

    async def __aenter__(self) -> "TestSession":
        await self.start()
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def start(self) -> Optional[str]:
        """Start session, return initial greeting if any."""
        if self._started:
            return self._initial_greeting

        # Create LLM using factory
        self._llm = self.llm_factory(self.model, self.temperature)
        await self._llm.__aenter__()

        # Create userdata with test-specific data overrides
        self._userdata = create_test_userdata(self.config, test_data=self.test_data)
        agent_config = load_agent_config()

        # Build agents
        AGENT_CLASSES = get_agent_classes(self.config)
        get_tools = get_tools_function(self.config)

        self._userdata.agents = {}
        for agent_id in self.config.agent_ids:
            agent_class = AGENT_CLASSES.get(agent_id)
            if agent_class:
                sub_agents = {a["id"]: a for a in agent_config.get("sub_agents", [])}
                agent_cfg = sub_agents.get(agent_id, {})
                instructions = load_instructions(agent_id, self._userdata, agent_config, version=self.version)
                tools = get_tools(agent_cfg.get("tools", []), strict=False)
                self._userdata.agents[agent_id] = agent_class(instructions=instructions, tools=tools)

        # Get starting agent
        agent = self._userdata.agents.get(self.start_agent)
        if not agent and self._userdata.agents:
            agent = next(iter(self._userdata.agents.values()))

        if not agent:
            raise ValueError(f"Agent '{self.start_agent}' not found")

        # Create and start session
        self._session = AgentSession(llm=self._llm, userdata=self._userdata)
        await self._session.__aenter__()
        await self._session.start(agent)

        # Wait for on_enter
        await asyncio.sleep(self.greeting_timeout)

        # Extract initial greeting
        self._initial_greeting = self._extract_greeting()
        self._started = True

        return self._initial_greeting

    def _extract_greeting(self) -> Optional[str]:
        """Extract initial greeting from history."""
        if not self._session:
            return None
        for item in self._session.history.items:
            if hasattr(item, "role") and getattr(item, "role", None) == "assistant":
                text = getattr(item, "text_content", "") or ""
                if text:
                    return text
        return None

    async def send_message(self, user_input: str) -> tuple[str, list[TurnEvent]]:
        """Send message and get response with events."""
        if not self._started or not self._session:
            raise RuntimeError("Session not started")

        run_result = await self._session.run(user_input=user_input)
        events = extract_events(run_result)
        response = get_response_text(events)

        return response, events

    def get_initial_greeting(self) -> Optional[str]:
        """Get initial greeting."""
        return self._initial_greeting

    async def close(self):
        """Clean up resources."""
        if self._session:
            await self._session.__aexit__(None, None, None)
        if self._llm:
            await self._llm.__aexit__(None, None, None)
        self._started = False
