"""Chat command for Claude Agent SDK CLI.

Contains the interactive chat loop and message streaming display functions.
"""
import asyncio
import json
from typing import Optional

from rich.panel import Panel
from rich.live import Live
from rich import box

from agent.display import console, print_success, print_warning, print_error, print_info
from cli.clients import APIClient
from cli.commands.handlers import CommandContext, handle_command


# Panel configuration constants
PANEL_WIDTH = 80
PANEL_BOX = box.ROUNDED


def create_panel(content: str, title: str, border_style: str) -> Panel:
    """Create a Rich panel with consistent styling.

    Args:
        content: Panel content text.
        title: Panel title with Rich markup.
        border_style: Border color style.

    Returns:
        Configured Rich Panel instance.
    """
    return Panel(
        content,
        title=title,
        title_align="left",
        border_style=border_style,
        width=PANEL_WIDTH,
        box=PANEL_BOX,
    )


def display_user_message(content: str) -> None:
    """Display a user message panel."""
    panel = create_panel(content, "[cyan bold]USER[/cyan bold]", "cyan")
    console.print(panel)


def display_tool_use(tool_name: str, tool_input: dict) -> None:
    """Display a tool use panel with formatted parameters."""
    display_content = f"[bold cyan]Tool:[/bold cyan] {tool_name}\n\n"
    display_content += "[bold]Parameters:[/bold]\n"
    display_content += f"[dim cyan]{json.dumps(tool_input, indent=2)}[/dim cyan]"

    panel = create_panel(
        display_content,
        f"[yellow bold]TOOL USE: {tool_name}[/yellow bold]",
        "yellow"
    )
    console.print(panel)


def display_tool_result(content: str) -> None:
    """Display a tool result panel with content truncation."""
    # Truncate long results
    display_content = content
    if len(content) > 1000:
        display_content = content[:1000] + f"\n\n... (truncated, showing first 1000 of {len(content)} characters)"

    panel = create_panel(
        display_content if display_content else "(empty result)",
        "[blue bold]TOOL RESULT[/blue bold]",
        "blue"
    )
    console.print(panel)


class StreamingDisplay:
    """Manages streaming text display with Rich Live panel."""

    def __init__(self):
        self._text_chunks: list[str] = []
        self._live: Optional[Live] = None

    def append_text(self, text: str) -> None:
        """Append text chunk and update the live display."""
        self._text_chunks.append(text)

        if self._live is None:
            self._live = Live("", console=console, refresh_per_second=30)
            self._live.__enter__()

        panel = create_panel(
            "".join(self._text_chunks),
            "[green bold]ASSISTANT (STREAMING)[/green bold]",
            "green"
        )
        self._live.update(panel)

    def close(self) -> None:
        """Close the live display if active."""
        if self._live is not None:
            self._live.__exit__(None, None, None)
            self._live = None

    def has_content(self) -> bool:
        """Check if any text was streamed."""
        return len(self._text_chunks) > 0


async def process_event(event: dict, streaming: StreamingDisplay, session_id: Optional[str]) -> Optional[str]:
    """Process a single event from the response stream.

    Args:
        event: Event dictionary from the client.
        streaming: StreamingDisplay instance for text accumulation.
        session_id: Current session ID (updated if init event received).

    Returns:
        Updated session_id if changed, otherwise None.
    """
    event_type = event.get("type")
    new_session_id = None

    if event_type == "init":
        # Update session ID when we get the real one from SDK
        new_session_id = event.get("session_id")
        if new_session_id and new_session_id != session_id:
            print_success(f"Session ID: {new_session_id}")
        return new_session_id

    if event_type == "stream_event":
        # Handle streaming text delta
        stream_data = event.get("event", {})
        if stream_data.get("type") == "content_block_delta":
            delta = stream_data.get("delta", {})
            if delta.get("type") == "text_delta":
                text = delta.get("text", "")
                if text:
                    streaming.append_text(text)
        return None

    if event_type == "assistant":
        # Handle complete assistant message
        content = event.get("content", [])
        for block in content:
            if block.get("type") == "text" and not streaming.has_content():
                # Only display if not already streamed
                panel = create_panel(
                    block.get("text", ""),
                    "[green bold]ASSISTANT[/green bold]",
                    "green"
                )
                console.print(panel)
            elif block.get("type") == "tool_use":
                streaming.close()
                display_tool_use(block.get("name", "unknown"), block.get("input", {}))
        return None

    if event_type == "tool_use":
        # Direct tool use event (from API mode)
        streaming.close()
        display_tool_use(event.get("name", "unknown"), event.get("input", {}))
        return None

    if event_type == "user":
        # Handle user messages (tool results)
        content = event.get("content", [])
        for block in content:
            if block.get("type") == "tool_result":
                streaming.close()
                display_tool_result(block.get("content", ""))
        return None

    if event_type == "success":
        streaming.close()
        num_turns = event.get("num_turns", 0)
        cost = event.get("total_cost_usd", 0)
        if num_turns > 0:
            print_info(f"\n[Session: {num_turns} turns, ${cost:.6f}]")
        return None

    if event_type == "error":
        streaming.close()
        error_msg = event.get("error", "Unknown error")
        print_error(f"\nError: {error_msg}")
        return None

    return None


async def async_chat(client) -> None:
    """Async chat loop implementation.

    Args:
        client: APIClient instance.
    """
    # Create or resume session
    try:
        session_info = await client.create_session()
        session_id = session_info.get("session_id")

        if session_info.get("resumed"):
            print_success(f"Resuming session: {session_id}")
        else:
            print_info("Ready for new conversation (session ID will be assigned on first message)")
    except Exception as e:
        print_error(f"Failed to prepare session: {e}")
        await client.disconnect()
        return

    print_info("Commands: exit, interrupt, new, resume, sessions, skills, agents, subagents, help")
    print_info("Type your message or command below.\n")

    # Create command context for shared handler
    cmd_ctx = CommandContext(
        list_skills=client.list_skills,
        list_agents=client.list_agents,
        list_subagents=client.list_subagents,
        list_sessions=client.list_sessions,
        interrupt=client.interrupt,
        create_session=client.create_session,
        close_session=client.close_session,
        resume_previous_session=client.resume_previous_session,
        current_session_id=session_id,
    )

    turn_count = 0

    while True:
        try:
            user_input = console.input(f"\n[Turn {turn_count + 1}] [cyan]You:[/cyan] ")

            # Handle commands using shared handler
            handled, should_break = await handle_command(user_input, cmd_ctx)
            if should_break:
                break
            if handled:
                # Update context in case session changed
                cmd_ctx.current_session_id = client.session_id
                session_id = client.session_id
                if user_input.lower().strip() in ('new', 'resume') or user_input.lower().startswith('resume '):
                    turn_count = 0
                continue

            # Display user message
            display_user_message(user_input)

            # Process response stream
            streaming = StreamingDisplay()
            try:
                async for event in client.send_message(user_input):
                    new_session_id = await process_event(event, streaming, session_id)
                    if new_session_id:
                        session_id = new_session_id
                        cmd_ctx.current_session_id = session_id

                streaming.close()
                console.print()
                turn_count += 1

                # Update turn count in storage (DirectClient only)
                if hasattr(client, 'update_turn_count'):
                    client.update_turn_count(turn_count)

            except Exception as e:
                streaming.close()
                print_error(f"\nError during message: {e}")
                continue

        except KeyboardInterrupt:
            print_warning("\nExiting...")
            break
        except EOFError:
            break

    await client.disconnect()
    print_success(f"Conversation ended after {turn_count} turns.")


def chat_command(api_url: str = "http://localhost:7001") -> None:
    """Start interactive chat session via API.

    Args:
        api_url: API server URL.
    """
    client = APIClient(api_url=api_url)

    try:
        asyncio.run(async_chat(client))
    except KeyboardInterrupt:
        print_warning("\nExiting...")
