"""Event extraction from LiveKit RunResult with type-safe parsing."""

import json
from dataclasses import dataclass
from typing import Any, Optional

from ..schemas.models import TurnEvent, EventType


@dataclass
class EventItem:
    """Normalized event item for type-safe access.

    Provides a consistent interface for accessing event data regardless
    of the underlying raw event structure.
    """
    role: Optional[str] = None
    content: Optional[Any] = None
    name: Optional[str] = None
    arguments: Optional[Any] = None
    output: Optional[str] = None
    is_error: bool = False
    new_agent_id: Optional[str] = None
    old_agent_id: Optional[str] = None

    @classmethod
    def from_raw(cls, raw: Any) -> "EventItem":
        """Safely extract fields from raw event item.

        Args:
            raw: Raw event item from LiveKit RunResult

        Returns:
            EventItem with safely extracted fields
        """
        if raw is None:
            return cls()

        return cls(
            role=getattr(raw, 'role', None),
            content=getattr(raw, 'content', None),
            name=getattr(raw, 'name', None),
            arguments=getattr(raw, 'arguments', None),
            output=getattr(raw, 'output', None),
            is_error=getattr(raw, 'is_error', False),
            new_agent_id=getattr(raw, 'new_agent_id', None),
            old_agent_id=getattr(raw, 'old_agent_id', None),
        )

    def is_assistant_message(self) -> bool:
        """Check if this is an assistant message event."""
        return self.role == 'assistant'

    def is_tool_call(self) -> bool:
        """Check if this is a tool call event."""
        return self.name is not None and self.arguments is not None

    def is_tool_output(self) -> bool:
        """Check if this is a tool output event."""
        return self.output is not None

    def is_handoff(self) -> bool:
        """Check if this is a handoff event."""
        return self.new_agent_id is not None and self.old_agent_id is not None


def _parse_arguments(args: Any) -> dict:
    """Parse tool arguments to dict.

    Args:
        args: Raw arguments (dict, JSON string, or other)

    Returns:
        Parsed arguments as dict
    """
    if args is None:
        return {}

    if isinstance(args, dict):
        return args

    if isinstance(args, str):
        try:
            parsed = json.loads(args)
            return parsed if isinstance(parsed, dict) else {"raw": args}
        except json.JSONDecodeError:
            return {"raw": args}

    return {"raw": str(args)}


def _content_to_str(content: Any) -> str:
    """Convert content to string, handling lists and other types.

    Args:
        content: Raw content (string, list, or other)

    Returns:
        Content as string
    """
    if content is None:
        return ""

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        return ' '.join(str(c) for c in content)

    return str(content)


def extract_events(run_result: Any) -> list[TurnEvent]:
    """Extract events from LiveKit RunResult with type-safe access.

    Args:
        run_result: LiveKit RunResult object

    Returns:
        List of normalized TurnEvent objects
    """
    events = []
    raw_events = getattr(run_result, 'events', [])

    for event in raw_events:
        raw_item = getattr(event, 'item', None)
        item = EventItem.from_raw(raw_item)

        if item.is_assistant_message():
            events.append(TurnEvent(
                type=EventType.AGENT_MESSAGE,
                content={"text": _content_to_str(item.content)}
            ))

        elif item.is_tool_call():
            events.append(TurnEvent(
                type=EventType.TOOL_CALL,
                content={
                    "name": item.name,
                    "arguments": _parse_arguments(item.arguments)
                }
            ))

        elif item.is_tool_output():
            events.append(TurnEvent(
                type=EventType.TOOL_OUTPUT,
                content={
                    "result": str(item.output),
                    "is_error": item.is_error
                }
            ))

        elif item.is_handoff():
            events.append(TurnEvent(
                type=EventType.HANDOFF,
                content={
                    "from_agent": item.old_agent_id or "unknown",
                    "to_agent": item.new_agent_id or "unknown"
                }
            ))

    return events


def get_response_text(events: list[TurnEvent]) -> str:
    """Get concatenated agent response text from events.

    Args:
        events: List of TurnEvent objects

    Returns:
        Concatenated agent response text
    """
    return " ".join(
        str(e.content.get("text", ""))
        for e in events
        if e.type == EventType.AGENT_MESSAGE
    )
