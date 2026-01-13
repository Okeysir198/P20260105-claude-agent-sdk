"""
Data structures for the simulated user system.

This module defines the core types used throughout the simulation framework,
including message types, turn events, and simulation results.
"""

import json
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Literal, Optional


class Role(Enum):
    """Role of a participant in the conversation."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@dataclass
class Message:
    """A single message in a conversation.

    Attributes:
        role: The role of the message sender.
        content: The text content of the message.
        timestamp: Unix timestamp when the message was created.
        metadata: Additional metadata about the message.
    """

    role: Role
    content: str
    timestamp: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary with role as string value."""
        return {
            "role": self.role.value,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class TurnEvent:
    """A JSON-serializable event that occurs during a conversation turn.

    Attributes:
        type: The type of event that occurred.
        content: Event-specific data.
        timestamp: Unix timestamp when the event occurred.
    """

    type: Literal[
        "user_message",
        "agent_message",
        "tool_call",
        "tool_output",
        "handoff",
        "error",
    ]
    content: dict[str, Any]
    timestamp: float


@dataclass
class SimulationTurn:
    """A single turn in a simulated conversation.

    Attributes:
        turn_number: The sequence number of this turn (1-indexed).
        user_message: The simulated user's message.
        agent_response: The agent's response to the user.
        events: List of events that occurred during this turn.
        agent_id: Identifier of the agent that handled this turn.
    """

    turn_number: int
    user_message: str
    agent_response: str
    events: list[TurnEvent] = field(default_factory=list)
    agent_id: Optional[str] = None


@dataclass
class SimulationResult:
    """The complete result of a simulated conversation.

    Attributes:
        turns: List of all turns in the simulation.
        total_turns: Total number of turns completed.
        stop_reason: Why the simulation ended.
        error: Error message if simulation ended due to error.
        metadata: Additional metadata about the simulation.
    """

    turns: list[SimulationTurn]
    total_turns: int
    stop_reason: Literal[
        "max_turns",
        "user_ended",
        "agent_ended",
        "goal_achieved",
        "error",
    ]
    error: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert the simulation result to a dictionary.

        Returns:
            Dictionary representation of the simulation result.
        """
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Convert the simulation result to a JSON string.

        Args:
            indent: Number of spaces for JSON indentation.

        Returns:
            JSON string representation of the simulation result.
        """
        return json.dumps(self.to_dict(), indent=indent)
