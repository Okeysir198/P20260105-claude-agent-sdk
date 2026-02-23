"""Message display and streaming for Claude Agent SDK."""
import json
from typing import AsyncIterator, Callable

# Claude SDK type imports
from claude_agent_sdk.types import (
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
    Message,
    AssistantMessage,
    UserMessage,
    SystemMessage,
    ResultMessage,
    StreamEvent,
)

# Rich library imports for enhanced display
from rich.panel import Panel
from rich.live import Live
from rich import box

from agent.display.console import console


async def print_message(
    role: str,
    content: str | TextBlock | ToolUseBlock | ToolResultBlock | AsyncIterator[str],
    width: int = 80,
    stream: bool = False
) -> None:
    """Display formatted message in a Rich panel. Supports strings, SDK blocks, and async iterators."""
    role_colors = {
        "user": "cyan",
        "assistant": "green",
        "system": "yellow",
        "tool": "blue",
        "tool_use": "yellow",
        "tool_result": "blue",
        "error": "red",
        "warning": "orange3",
        "info": "blue",
        "success": "green",
    }

    is_async_iterator = hasattr(content, '__aiter__') or hasattr(content, '__anext__')

    if is_async_iterator or stream:
        # Streaming mode - use Rich Live panel
        color = role_colors.get(role.lower(), "white")
        panel_title = f"[{color} bold]⬤ {role.upper()}[/{color} bold]"

        collected = []

        with Live("", console=console, refresh_per_second=30) as live:
            async for chunk in content:  # type: ignore[arg-type]
                collected.append(chunk)
                panel = Panel(
                    "".join(collected),
                    title=panel_title,
                    title_align="left",
                    border_style=color,
                    width=width,
                    box=box.ROUNDED,
                )
                live.update(panel)
        return

    if isinstance(content, TextBlock):
        color = role_colors.get("assistant", "green")
        display_content = content.text
        panel_title = f"[{color} bold]⬤ ASSISTANT[/{color} bold]"

    elif isinstance(content, ToolUseBlock):
        color = role_colors.get("tool_use", "yellow")
        tool_name = content.name
        tool_input = content.input or {}

        display_content = f"[bold cyan]Tool:[/bold cyan] {tool_name}\n\n"
        display_content += "[bold]Parameters:[/bold]\n"
        display_content += f"[dim cyan]{json.dumps(tool_input, indent=2)}[/dim cyan]"

        panel_title = f"[{color} bold]⚙ TOOL USE: {tool_name}[/{color} bold]"

    elif isinstance(content, ToolResultBlock):
        color = role_colors.get("tool_result", "blue")
        result_content = str(content.content) if content.content else "(empty result)"

        if len(result_content) > 1000:
            result_content = result_content[:1000] + f"\n\n... (truncated, showing first 1000 of {len(result_content)} characters)"

        display_content = result_content
        panel_title = f"[{color} bold]✓ TOOL RESULT[/{color} bold]"

    else:
        color = role_colors.get(role.lower(), "white")
        display_content = str(content)
        panel_title = f"[{color} bold]⬤ {role.upper()}[/{color} bold]"

    panel = Panel(
        display_content,
        title=panel_title,
        title_align="left",
        border_style=color,
        width=width,
        box=box.ROUNDED,
    )
    console.print(panel)


async def process_messages(
    messages: AsyncIterator["Message"],
    stream: bool = False,
    on_session_id: Callable[[str], None] | None = None
) -> None:
    """Process and display all message types from Claude SDK response stream."""
    streaming_text = []
    has_stream_events = False
    live_context = None

    def close_live_panel():
        """Close the Live panel if it is currently open."""
        nonlocal live_context
        if live_context is not None:
            live_context.__exit__(None, None, None)
            live_context = None

    async for message in messages:
        if isinstance(message, StreamEvent):
            has_stream_events = True

            event = message.event
            if event.get("type") == "content_block_delta":
                delta = event.get("delta", {})
                if delta.get("type") == "text_delta":
                    text = delta.get("text", "")
                    if text and stream:
                        streaming_text.append(text)

                        if live_context is None:
                            live_context = Live("", console=console, refresh_per_second=30)
                            live_context.__enter__()

                        panel = Panel(
                            "".join(streaming_text),
                            title="[green bold]⬤ ASSISTANT (STREAMING)[/green bold]",
                            title_align="left",
                            border_style="green",
                            width=80,
                            box=box.ROUNDED,
                        )
                        live_context.update(panel)

        elif isinstance(message, SystemMessage):
            if message.subtype == 'init' and on_session_id:
                session_id = message.data.get('session_id')
                if session_id:
                    on_session_id(session_id)
            continue

        elif isinstance(message, UserMessage):
            close_live_panel()

            for block in message.content:
                if isinstance(block, ToolResultBlock):
                    await print_message("tool_result", block)
                elif isinstance(block, TextBlock):
                    await print_message("user", block.text)

        elif isinstance(message, AssistantMessage):
            text_blocks = [block for block in message.content if isinstance(block, TextBlock)]
            tool_use_blocks = [block for block in message.content if isinstance(block, ToolUseBlock)]

            if tool_use_blocks:
                close_live_panel()

                for block in tool_use_blocks:
                    await print_message("tool_use", block)

            if text_blocks:
                if has_stream_events:
                    streaming_text.clear()
                else:
                    for block in text_blocks:
                        await print_message("assistant", block)

        elif isinstance(message, ResultMessage):
            close_live_panel()

            if message.subtype == 'error_max_turns':
                await print_message("info", f"Session completed: {message.num_turns} turns, ${message.total_cost_usd:.6f}")
            elif message.subtype != 'success':
                await print_message("info", f"Session completed: {message.subtype}")

        elif not stream:
            await print_message("assistant", str(message))

    close_live_panel()
