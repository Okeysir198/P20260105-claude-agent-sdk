"""Data models for eval results, turns, and events."""

from dataclasses import dataclass, field, asdict
from typing import Literal, Optional, Any
from enum import Enum
import json
import time


class EventType(str, Enum):
    """Types of events that can occur during a conversation."""
    USER_MESSAGE = "user_message"
    AGENT_MESSAGE = "agent_message"
    TOOL_CALL = "tool_call"
    TOOL_OUTPUT = "tool_output"
    HANDOFF = "handoff"
    ERROR = "error"


def _serialize_value(obj: Any) -> Any:
    """Serialize a value, handling Enums and nested structures."""
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, dict):
        return {k: _serialize_value(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_serialize_value(item) for item in obj]
    return obj


def _to_serializable_dict(obj: Any) -> dict:
    """Convert a dataclass to a dict with proper enum handling."""
    raw = asdict(obj)
    return _serialize_value(raw)


@dataclass
class TurnEvent:
    """A single event in a conversation turn."""
    type: EventType
    content: dict[str, Any]
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return _to_serializable_dict(self)


@dataclass
class Turn:
    """A single conversation turn."""
    turn_number: int
    user_input: str
    agent_response: str
    events: list[TurnEvent] = field(default_factory=list)
    agent_id: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return _to_serializable_dict(self)


@dataclass
class TestResult:
    """Result from running a test case."""
    turns: list[Turn]
    total_turns: int
    duration_ms: float
    stop_reason: Literal["completed", "max_turns", "error", "user_ended", "agent_ended"]
    error: Optional[str] = None
    test_name: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        """True if test completed without errors."""
        return self.error is None and self.stop_reason == "completed"

    @property
    def failed(self) -> bool:
        """True if test had errors or abnormal termination."""
        return not self.passed

    def summary(self) -> str:
        """One-line summary of test result."""
        status = "PASS" if self.passed else "FAIL"
        return f"{status}: {self.test_name} ({self.total_turns} turns, {self.duration_ms:.0f}ms)"

    def get_turn(self, number: int) -> Optional[Turn]:
        """Get a specific turn by number."""
        for turn in self.turns:
            if turn.turn_number == number:
                return turn
        return None

    def get_last_response(self) -> str:
        """Get the agent's last response."""
        if self.turns:
            return self.turns[-1].agent_response
        return ""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return _to_serializable_dict(self)

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def get_assistant_messages(self) -> list[str]:
        """Extract all agent responses from turns."""
        return [turn.agent_response for turn in self.turns if turn.agent_response]

    def get_tool_calls(self) -> list[dict]:
        """Extract all tool calls from turn events."""
        tool_calls = []
        for turn in self.turns:
            for event in turn.events:
                if event.type == EventType.TOOL_CALL:
                    tool_calls.append(event.content)
        return tool_calls


@dataclass
class EvalResult(TestResult):
    """Result from running an evaluation with assertions."""
    score: float = 0.0
    passed_count: int = 0
    failed_count: int = 0
    assertions: list[dict] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """True if all assertions passed and test completed without errors."""
        return self.failed_count == 0 and self.error is None and self.stop_reason == "completed"

    def get_failed_assertions(self) -> list[dict]:
        """Get list of failed assertions."""
        return [a for a in self.assertions if not a.get("passed", False)]

    def summary(self) -> str:
        """One-line summary including assertion results."""
        status = "PASS" if self.passed else "FAIL"
        total_assertions = self.passed_count + self.failed_count
        return f"{status}: {self.test_name} ({self.total_turns} turns, {self.duration_ms:.0f}ms) | Assertions: {self.passed_count}/{total_assertions}"


@dataclass
class SimulationResult(TestResult):
    """Result from running a simulation."""
    persona: str = ""
    goal_achieved: bool = False


@dataclass
class BatchResult:
    """Result from running multiple tests."""
    results: list[TestResult]
    total: int
    passed_count: int
    failed_count: int
    duration_ms: float
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        """True if all tests passed."""
        return self.failed_count == 0

    @property
    def success_rate(self) -> float:
        """Percentage of tests that passed."""
        return (self.passed_count / self.total * 100) if self.total > 0 else 0.0

    def get_failures(self) -> list[TestResult]:
        """Get list of failed test results."""
        return [r for r in self.results if r.failed]

    def summary(self) -> str:
        """One-line summary of batch results."""
        status = "PASS" if self.passed else "FAIL"
        return f"{status}: {self.passed_count}/{self.total} tests passed ({self.success_rate:.1f}%) in {self.duration_ms:.0f}ms"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "results": [r.to_dict() for r in self.results],
            "total": self.total,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
