"""Centralized history tracking for conversation events.

Handles accumulating text deltas, saving tool events, and finalizing
assistant responses during conversation streaming.
"""
import json
from dataclasses import dataclass, field
from typing import Any

from claude_agent_sdk.types import (
    AssistantMessage,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

from agent.core.storage import HistoryStorage
from api.constants import TOOL_REF_PATTERN, EventType, MessageRole
from api.services.content_normalizer import ContentBlock, normalize_content, normalize_tool_result_content

from api.utils.sensitive_data_filter import redact_sensitive_data

# Control/protocol events that should not be persisted to history.
# These are transient signals used for connection and flow management only.
_CONTROL_EVENT_TYPES: set[str] = {
    EventType.SESSION_ID,
    EventType.READY,
    EventType.COMPACT_STARTED,
    EventType.COMPACT_COMPLETED,
    EventType.COMPACT_REQUEST,
    EventType.CANCEL_REQUEST,
}


def _parent_metadata(data: dict) -> dict | None:
    """Extract parent_tool_use_id metadata from event data, or return None."""
    parent_id = data.get("parent_tool_use_id")
    if parent_id:
        return {"parent_tool_use_id": parent_id}
    return None


@dataclass
class HistoryTracker:
    """Tracks and persists conversation history during streaming."""
    session_id: str
    history: HistoryStorage
    _text_parts: list[str] = field(default_factory=list)
    _canonical_text_parts: list[str] = field(default_factory=list)

    def save_user_message(self, content: str | list[ContentBlock | dict[str, Any]]) -> None:
        """Save a user message to history.

        Accepts plain strings (legacy) or lists of ContentBlock/dict (multi-part).
        """
        if isinstance(content, str):
            serialized_content = content
        elif content and hasattr(content[0], 'model_dump'):
            serialized_content = [block.model_dump() for block in content]
        else:
            serialized_content = [block.model_dump() for block in normalize_content(content)]

        self.history.append_message(
            session_id=self.session_id,
            role=MessageRole.USER,
            content=serialized_content
        )

    def add_canonical_text(self, text: str) -> None:
        """Add canonical text from an AssistantMessage TextBlock.

        Preferred over accumulated text_delta content which may contain
        proxy-injected tool references.
        """
        if text:
            self._canonical_text_parts.append(text)

    def accumulate_text(self, text: str) -> None:
        """Accumulate a text delta fragment."""
        self._text_parts.append(text)

    def get_accumulated_text(self) -> str:
        """Get the accumulated text without clearing it."""
        return "".join(self._text_parts)

    def has_accumulated_text(self) -> bool:
        """Check if there is any accumulated text."""
        return bool(self._text_parts)

    def save_tool_use(self, data: dict) -> None:
        """Save a tool use event to history."""
        metadata = _parent_metadata(data)
        self.history.append_message(
            session_id=self.session_id,
            role=MessageRole.TOOL_USE,
            content=json.dumps(data.get("input", {})),
            tool_name=data.get("tool_name") or data.get("name"),
            tool_use_id=data.get("tool_use_id") or data.get("id"),
            metadata=metadata,
        )

    def save_tool_result(self, data: dict) -> None:
        """Save a tool result event to history, redacting sensitive data."""
        metadata = _parent_metadata(data)
        content = redact_sensitive_data(str(data.get("content", "")))

        self.history.append_message(
            session_id=self.session_id,
            role=MessageRole.TOOL_RESULT,
            content=content,
            tool_use_id=data.get("tool_use_id"),
            is_error=bool(data.get("is_error", False)),
            metadata=metadata,
        )

    def save_user_answer(self, data: dict) -> None:
        """Save a user_answer event to history as a tool_result."""
        self.history.append_message(
            session_id=self.session_id,
            role=MessageRole.TOOL_RESULT,
            content=json.dumps(data.get("answers", {})),
            tool_use_id=data.get("question_id"),
            is_error=False
        )

    def save_result_message(self, data: dict) -> None:
        """Save SDK result metadata (usage, costs, turns) as a system message."""
        metadata = {"event_type": "result"}
        metadata.update(data)
        self.history.append_message(
            session_id=self.session_id,
            role=MessageRole.SYSTEM,
            content=json.dumps(data),
            metadata=metadata
        )

    def save_generic_event(self, event_type: str, data: dict) -> None:
        """Save an unrecognized SDK event for future analysis."""
        metadata = {"event_type": event_type}
        self.history.append_message(
            session_id=self.session_id,
            role=MessageRole.EVENT,
            content=json.dumps(data),
            metadata=metadata
        )

    def finalize_assistant_response(self, metadata: dict | None = None) -> None:
        """Finalize and save accumulated assistant text, preferring canonical over delta."""
        self._save_assistant_text(flush_only=False, model=None, metadata=metadata)

    def _flush_canonical_text(self, model: str | None = None) -> None:
        """Flush accumulated canonical text parts to history as an assistant message.

        This ensures text appears in correct temporal order relative to tool calls.
        Called before each ToolUseBlock/ThinkingBlock to maintain ordering.

        Args:
            model: Optional model identifier to include in metadata.
        """
        self._save_assistant_text(flush_only=True, model=model, metadata=None)

    def _save_assistant_text(self, flush_only: bool, model: str | None, metadata: dict | None) -> None:
        """Save accumulated assistant text to history.

        Shared implementation for both finalize_assistant_response and
        _flush_canonical_text. Handles two modes:
        - flush_only=True: Only saves canonical text, used before tool calls
        - flush_only=False: Saves canonical or accumulated text, used at turn end

        Args:
            flush_only: If True, only save canonical text parts. If False, prefer
                canonical text but fall back to accumulated text_delta content.
            model: Optional model identifier to include in metadata (used by flush_only).
            metadata: Optional additional metadata (used by finalize_assistant_response).
        """
        if flush_only:
            # _flush_canonical_text mode: only save canonical text
            if not self._canonical_text_parts:
                return

            content = "\n\n".join(self._canonical_text_parts)
            if not content:
                self._canonical_text_parts = []
                return

            save_metadata: dict | None = None
            if model:
                save_metadata = {"model": model}

            self.history.append_message(
                session_id=self.session_id,
                role=MessageRole.ASSISTANT,
                content=content,
                metadata=save_metadata,
            )
            self._canonical_text_parts = []
        else:
            # finalize_assistant_response mode: prefer canonical, fall back to accumulated
            if not self._text_parts and not self._canonical_text_parts:
                return

            # Use canonical TextBlock text if available, otherwise fall back
            # to accumulated text_delta content (which may contain proxy-injected
            # tool references that need stripping).
            if self._canonical_text_parts:
                content = "\n\n".join(self._canonical_text_parts)
            else:
                content = TOOL_REF_PATTERN.sub('', "".join(self._text_parts)).strip()

            self._text_parts = []
            self._canonical_text_parts = []

            if not content:
                return

            self.history.append_message(
                session_id=self.session_id,
                role=MessageRole.ASSISTANT,
                content=content,
                metadata=metadata
            )

    def save_from_assistant_message(self, msg: AssistantMessage) -> None:
        """Save history entries from a typed AssistantMessage.

        Uses typed block attributes (block.id, block.name, block.input)
        instead of dict keys. This produces clean JSONL entries:
        - ToolUseBlock.input stored as structured dict in metadata
        - ToolResultBlock.content stripped of agentId metadata
        - TextBlock text cleaned of proxy-injected tool references and
          flushed before tool calls to maintain temporal ordering
        - ThinkingBlock saved with metadata marking the block type
        - AssistantMessage.error captured as a system message
        - AssistantMessage.model included in metadata
        """
        model = getattr(msg, 'model', None)

        for block in msg.content:
            if isinstance(block, TextBlock):
                # The SDK assembles TextBlock.text from text_delta events.
                # The Z.AI proxy injects serialized tool references into the
                # text stream (e.g., "[Tool: Bash (ID: ...)] Input: {...}"),
                # so TextBlock.text may contain them. Strip before saving.
                clean_text = TOOL_REF_PATTERN.sub('', block.text)
                clean_text = clean_text.strip()
                if clean_text:
                    self._canonical_text_parts.append(clean_text)
            elif isinstance(block, ToolUseBlock):
                # Flush any accumulated text BEFORE the tool call for correct ordering
                self._flush_canonical_text(model=model)
                self._save_tool_use_block(block, parent_tool_use_id=msg.parent_tool_use_id, model=model)
            elif isinstance(block, ThinkingBlock):
                # Flush text before thinking block to maintain ordering
                self._flush_canonical_text(model=model)
                self._save_thinking_block(block, model=model)
            elif isinstance(block, ToolResultBlock):
                self._save_tool_result_block(block, parent_tool_use_id=msg.parent_tool_use_id)

        # Capture AssistantMessage.error as a system message
        if msg.error:
            self.history.append_message(
                session_id=self.session_id,
                role=MessageRole.SYSTEM,
                content=str(msg.error),
                metadata={"event_type": "assistant_error", "error": str(msg.error)},
            )

    def save_from_user_message(self, msg: UserMessage) -> None:
        """Save entries from a typed UserMessage.

        UserMessages after tool execution contain ToolResultBlocks.
        UserMessages may also contain TextBlock content (user text).
        Uses typed attributes for clean history entries.
        """
        if isinstance(msg.content, str):
            return
        for block in msg.content:
            if isinstance(block, ToolResultBlock):
                self._save_tool_result_block(block, parent_tool_use_id=msg.parent_tool_use_id)
            elif isinstance(block, TextBlock):
                if block.text and block.text.strip():
                    self.history.append_message(
                        session_id=self.session_id,
                        role=MessageRole.USER,
                        content=block.text.strip(),
                    )

    def _save_tool_use_block(
        self,
        block: ToolUseBlock,
        parent_tool_use_id: str | None = None,
        model: str | None = None,
    ) -> None:
        """Save a ToolUseBlock using typed attributes.

        Stores block.input as a structured dict in metadata.input,
        avoiding the double-encoding problem of json.dumps(dict).

        Args:
            block: The ToolUseBlock to save.
            parent_tool_use_id: Optional parent tool use ID for subagents.
            model: Optional model identifier to include in metadata.
        """
        metadata: dict = {"input": block.input or {}}
        if parent_tool_use_id:
            metadata["parent_tool_use_id"] = parent_tool_use_id
        if model:
            metadata["model"] = model
        self.history.append_message(
            session_id=self.session_id,
            role=MessageRole.TOOL_USE,
            content=json.dumps(block.input or {}),
            tool_name=block.name,
            tool_use_id=block.id,
            metadata=metadata,
        )

    def _save_thinking_block(
        self,
        block: ThinkingBlock,
        model: str | None = None,
    ) -> None:
        """Save a ThinkingBlock to history.

        Stores thinking content as an assistant role message with
        metadata indicating the block type.

        Args:
            block: The ThinkingBlock to save.
            model: Optional model identifier to include in metadata.
        """
        metadata: dict = {"block_type": "thinking"}
        if model:
            metadata["model"] = model
        self.history.append_message(
            session_id=self.session_id,
            role=MessageRole.ASSISTANT,
            content=block.thinking,
            metadata=metadata,
        )

    def _save_tool_result_block(
        self,
        block: ToolResultBlock,
        parent_tool_use_id: str | None = None,
    ) -> None:
        """Save a ToolResultBlock using typed attributes.

        Strips agentId metadata from content before storing.
        """
        metadata = {"parent_tool_use_id": parent_tool_use_id} if parent_tool_use_id else None
        self.history.append_message(
            session_id=self.session_id,
            role=MessageRole.TOOL_RESULT,
            content=normalize_tool_result_content(block.content),
            tool_use_id=block.tool_use_id,
            is_error=bool(block.is_error),
            metadata=metadata,
        )

    def process_event(self, event_type: str, data: dict) -> None:
        """Process an event and update history accordingly.

        This is a convenience method that routes events to the appropriate
        handler based on event type.  Unrecognized events are persisted as
        generic event records so that new SDK message types are captured
        automatically. Control/protocol events (session_id, ready, compact_*,
        cancel_request) are intentionally excluded from history.

        Args:
            event_type: The type of event (from EventType constants).
            data: The event data dictionary.
        """
        if event_type == EventType.TEXT_DELTA:
            self.accumulate_text(data.get("text", ""))
        elif event_type == EventType.TOOL_USE:
            # Flush accumulated text before tool_use to maintain temporal ordering.
            # This ensures both WebSocket and SSE paths get correct ordering
            # without duplicating the check in each caller.
            if self.has_accumulated_text():
                self.finalize_assistant_response()
            self.save_tool_use(data)
        elif event_type == EventType.TOOL_RESULT:
            self.save_tool_result(data)
        elif event_type == EventType.USER_ANSWER:
            self.save_user_answer(data)
        elif event_type == EventType.DONE:
            self.finalize_assistant_response()
            self.save_result_message(data)
        elif event_type == EventType.CANCELLED:
            # Finalize any partial response with cancelled metadata
            self.finalize_assistant_response(metadata={"cancelled": True})
        elif event_type == EventType.ERROR:
            self.history.append_message(
                session_id=self.session_id,
                role=MessageRole.SYSTEM,
                content=str(data.get("error", data.get("message", json.dumps(data)))),
                metadata={"event_type": "error"}
            )
        elif event_type not in _CONTROL_EVENT_TYPES:
            # Catch-all: persist any unrecognized event for future analysis
            self.save_generic_event(event_type, data)
