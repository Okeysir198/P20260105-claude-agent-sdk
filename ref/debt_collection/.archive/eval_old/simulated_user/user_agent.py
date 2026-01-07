"""LangChain-based simulated user for testing voice agents.

This module provides a configurable simulated user that can engage in
conversations with LiveKit voice agents for testing purposes.
"""

import time
from typing import Any

from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from .config import SimulatedUserConfig
from .types import Message, Role


class SimulatedUserAgent:
    """A simulated user agent for testing voice agents.

    Uses LangChain's init_chat_model for provider-agnostic model configuration.
    Maintains conversation history and generates contextual responses based
    on the configured persona and goals.
    """

    def __init__(self, config: SimulatedUserConfig):
        """Initialize the simulated user agent.

        Args:
            config: Configuration defining persona, model, and behavior.
        """
        self.config = config
        self.conversation_history: list[Message] = []
        self.model = self._create_model()

    def _create_model(self) -> Any:
        """Create configurable LLM instance using init_chat_model.

        Returns:
            A LangChain chat model configured with the specified provider,
            model, and parameters. Supports runtime configuration overrides.
        """
        return init_chat_model(
            model=self.config.model,
            model_provider=self.config.model_provider,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            configurable_fields=("model", "model_provider", "temperature", "max_tokens"),
        )

    def _build_system_prompt(self) -> str:
        """Build complete system prompt from config components.

        Combines the base system prompt (or default) with optional
        goal description and persona traits.

        Returns:
            Complete system prompt string for the LLM.
        """
        base_prompt = self.config.system_prompt or self._default_system_prompt()

        parts = [base_prompt]

        if self.config.goal_description:
            parts.append(f"\nYour goal: {self.config.goal_description}")

        if self.config.persona_traits:
            traits_text = ", ".join(self.config.persona_traits)
            parts.append(f"\nYour personality traits: {traits_text}")

        return "\n".join(parts)

    def _default_system_prompt(self) -> str:
        """Default prompt for debt collection scenario.

        Returns:
            Default system prompt instructing the LLM how to behave
            as a simulated call recipient.
        """
        return """You are simulating a person receiving a debt collection call.

Respond naturally as if you are the person being called.
Keep responses concise (1-3 sentences).

IMPORTANT - Ending the conversation:
- When the call reaches a natural conclusion
- Or when the agent says goodbye
- You MUST respond with "good bye" or "goodbye" to end the conversation"""

    def _build_messages(self, agent_message: str) -> list:
        """Build the message list for the LLM invocation.

        Args:
            agent_message: The latest message from the agent.

        Returns:
            List of LangChain message objects including system prompt,
            conversation history, and the new agent message.
        """
        messages = [SystemMessage(content=self._build_system_prompt())]

        # Add conversation history
        for msg in self.conversation_history:
            if msg.role == Role.USER:
                messages.append(HumanMessage(content=msg.content))
            elif msg.role == Role.ASSISTANT:
                messages.append(AIMessage(content=msg.content))

        # Add the new agent message (agent speaks as AI from user's perspective)
        messages.append(AIMessage(content=agent_message))

        return messages

    async def generate_response(
        self,
        agent_message: str,
        runtime_config: dict[str, Any] | None = None,
    ) -> str:
        """Generate user response to agent message.

        Args:
            agent_message: The message from the agent to respond to.
            runtime_config: Optional runtime configuration overrides.
                           Supports keys: model, model_provider, temperature, max_tokens.

        Returns:
            The simulated user's response text.

        Raises:
            Exception: If the model invocation fails.
        """
        messages = self._build_messages(agent_message)

        # Build config for runtime overrides if provided
        invoke_config = None
        if runtime_config:
            invoke_config = {"configurable": runtime_config}

        # Invoke the model asynchronously
        response = await self.model.ainvoke(messages, config=invoke_config)

        # Extract response text
        response_text = response.content if hasattr(response, "content") else str(response)

        # Record agent message in history
        self.conversation_history.append(
            Message(
                role=Role.ASSISTANT,
                content=agent_message,
                timestamp=time.time(),
            )
        )

        # Record user response in history
        self.conversation_history.append(
            Message(
                role=Role.USER,
                content=response_text,
                timestamp=time.time(),
            )
        )

        return response_text

    def should_stop(self, message: str) -> bool:
        """Check if message contains stop phrases indicating conversation end.

        Args:
            message: The message to check for stop phrases.

        Returns:
            True if any stop phrase is found in the message.
        """
        message_lower = message.lower()
        return any(phrase in message_lower for phrase in self.config.stop_phrases)

    def get_initial_message(self) -> str | None:
        """Get the initial message to start the conversation.

        Returns:
            The configured initial message, or None if conversation
            should start with the agent speaking first.
        """
        return self.config.initial_message

    def reset(self) -> None:
        """Reset conversation history for a new simulation."""
        self.conversation_history = []
