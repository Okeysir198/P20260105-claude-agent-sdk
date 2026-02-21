"""Chat command for Claude Agent SDK CLI.

Contains the interactive chat loop and message streaming display functions.
"""
import asyncio
import json
import os

from rich.live import Live
from rich.panel import Panel

from agent.display import console, print_error, print_header, print_info, print_success, print_warning
from cli.clients import APIClient, WSClient
from cli.commands.handlers import CommandContext, handle_command
from cli.theme import format_panel_title, format_styled, get_theme


def create_panel(content: str, title: str, border_style: str) -> Panel:
    """Create a Rich panel with consistent styling.

    Args:
        content: Panel content text.
        title: Panel title with Rich markup.
        border_style: Border color style.

    Returns:
        Configured Rich Panel instance.
    """
    theme = get_theme()
    return Panel(
        content,
        title=title,
        title_align="left",
        border_style=border_style,
        width=theme.panel.width,
        box=theme.panel.box_style,
    )


def display_user_message(content: str) -> None:
    """Display a user message panel."""
    theme = get_theme()
    title = format_panel_title("USER", theme.colors.user)
    panel = create_panel(content, title, theme.colors.user)
    console.print(panel)


def display_tool_use(tool_name: str, tool_input: dict) -> None:
    """Display a tool use panel with formatted parameters."""
    theme = get_theme()
    color = theme.colors.tool_use
    display_content = f"[bold {color}]Tool:[/bold {color}] {tool_name}\n\n"
    display_content += "[bold]Parameters:[/bold]\n"
    display_content += f"[dim {color}]{json.dumps(tool_input, indent=2)}[/dim {color}]"

    title = format_panel_title(f"TOOL USE: {tool_name}", color)
    panel = create_panel(display_content, title, color)
    console.print(panel)


def display_tool_result(content: str) -> None:
    """Display a tool result panel with content truncation."""
    theme = get_theme()
    max_length = theme.max_tool_result_length
    display_content = content

    # Check for standalone file metadata and display separately
    try:
        parsed = json.loads(content)
        if parsed.get("_standalone_file"):
            file_data = parsed["_standalone_file"]
            file_type = file_data.get("type", "file")
            filename = file_data.get("filename", "unknown")
            url = file_data.get("url", "")
            size_bytes = file_data.get("size_bytes", 0)

            # Display file info in a prominent panel
            size_str = _format_size(size_bytes)
            type_emoji = {"audio": "🎵", "video": "🎬", "image": "🖼️", "file": "📄"}.get(file_type, "📄")

            title = format_panel_title(f"{type_emoji} FILE", "cyan")
            file_info = f"[bold]{filename}[/bold] ({size_str})\n"
            file_info += f"[dim]{url}[/dim]"

            panel = create_panel(file_info, title, "cyan")
            console.print(panel)

            # Return early - don't show the full tool result for file messages
            return
    except (json.JSONDecodeError, TypeError):
        pass  # Not JSON or no standalone file data, continue with normal display

    if len(content) > max_length:
        display_content = content[:max_length] + f"\n\n... (truncated, showing first {max_length} of {len(content)} characters)"

    title = format_panel_title("TOOL RESULT", theme.colors.tool_result)
    panel = create_panel(
        display_content if display_content else "(empty result)",
        title,
        theme.colors.tool_result
    )
    console.print(panel)


def _format_size(size_bytes: int) -> str:
    """Format byte size to human readable string."""
    size = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"


def display_assistant_message(content: str, streaming: bool = False) -> None:
    """Display an assistant message panel.

    Args:
        content: Message content.
        streaming: Whether this is a streaming message.
    """
    theme = get_theme()
    color = theme.colors.assistant_streaming if streaming else theme.colors.assistant
    label = "ASSISTANT (STREAMING)" if streaming else "ASSISTANT"
    title = format_panel_title(label, color)
    panel = create_panel(content, title, color)
    console.print(panel)


def collect_user_answers(questions: list, timeout: int) -> dict:
    """Display questions and collect answers from the user.

    Args:
        questions: List of question dictionaries with header, question, options, multiSelect.
        timeout: Timeout in seconds (displayed to user).

    Returns:
        Dictionary mapping question text to user's answer(s).
    """
    theme = get_theme()
    color = theme.colors.question
    prompt_color = theme.colors.prompt

    console.print()
    title = format_panel_title("QUESTION", color)
    panel = create_panel(
        f"[bold]Claude needs your input[/bold]\n[dim]Timeout: {timeout} seconds[/dim]",
        title,
        color
    )
    console.print(panel)

    answers = {}
    for q in questions:
        header = q.get("header", "Question")
        question_text = q.get("question", "")
        options = q.get("options", [])
        multi_select = q.get("multiSelect", False)

        console.print(f"\n[bold {prompt_color}]{header}:[/bold {prompt_color}] {question_text}")

        for i, opt in enumerate(options, 1):
            label = opt.get("label", f"Option {i}")
            description = opt.get("description", "")
            desc_suffix = f" [dim]- {description}[/dim]" if description else ""
            console.print(f"  [{prompt_color}]{i}.[/{prompt_color}] {label}{desc_suffix}")

        console.print(f"  [{prompt_color}]{len(options) + 1}.[/{prompt_color}] Other [dim](type your own answer)[/dim]")

        if multi_select:
            console.print("[dim]  (Enter numbers separated by commas for multiple selections)[/dim]")

        try:
            answer = _collect_single_answer(options, multi_select, prompt_color)
            answers[question_text] = answer
        except (EOFError, KeyboardInterrupt):
            answers[question_text] = "Skipped"

    console.print(format_styled("Answers submitted", theme.colors.confirm))
    return answers


def _collect_single_answer(options: list, multi_select: bool, prompt_color: str):
    """Collect a single answer from user input.

    Args:
        options: Available options.
        multi_select: Whether multiple selections are allowed.
        prompt_color: Color for prompt text.

    Returns:
        User's answer (string or list of strings).
    """
    if multi_select:
        user_input = console.input(f"[{prompt_color}]Your choices: [/{prompt_color}]").strip()
        return _parse_multi_select(user_input, options, prompt_color)

    user_input = console.input(f"[{prompt_color}]Your choice: [/{prompt_color}]").strip()
    return _parse_single_select(user_input, options, prompt_color)


def _parse_multi_select(user_input: str, options: list, prompt_color: str) -> list:
    """Parse multi-select user input."""
    selected = []
    for part in user_input.split(","):
        part = part.strip()
        if not part.isdigit():
            selected.append(part)
            continue

        idx = int(part) - 1
        if 0 <= idx < len(options):
            selected.append(options[idx].get("label", f"Option {idx + 1}"))
        elif idx == len(options):
            other_text = console.input(f"[{prompt_color}]Enter your answer: [/{prompt_color}]").strip()
            if other_text:
                selected.append(f"Other: {other_text}")

    return selected if selected else ["No selection"]


def _parse_single_select(user_input: str, options: list, prompt_color: str) -> str:
    """Parse single-select user input."""
    if not user_input:
        return "No answer"

    if not user_input.isdigit():
        return user_input

    idx = int(user_input) - 1
    if 0 <= idx < len(options):
        return options[idx].get("label", f"Option {idx + 1}")

    if idx == len(options):
        other_text = console.input(f"[{prompt_color}]Enter your answer: [/{prompt_color}]").strip()
        return f"Other: {other_text}" if other_text else "Other"

    return user_input


class StreamingDisplay:
    """Manages streaming text display with Rich Live panel."""

    def __init__(self):
        self._text_chunks: list[str] = []
        self._live: Live | None = None

    def append_text(self, text: str) -> None:
        """Append text chunk and update the live display."""
        self._text_chunks.append(text)

        if self._live is None:
            self._live = Live("", console=console, refresh_per_second=30)
            self._live.__enter__()

        theme = get_theme()
        title = format_panel_title("ASSISTANT (STREAMING)", theme.colors.assistant_streaming)
        panel = create_panel("".join(self._text_chunks), title, theme.colors.assistant_streaming)
        self._live.update(panel)

    def close(self) -> None:
        """Close the live display if active."""
        if self._live is not None:
            self._live.__exit__(None, None, None)
            self._live = None

    def has_content(self) -> bool:
        """Check if any text was streamed."""
        return len(self._text_chunks) > 0


# Event handler dispatch table
EventResult = tuple[str | None, dict | None]


def _handle_init(event: dict, streaming: StreamingDisplay, session_id: str | None, client) -> EventResult:
    """Handle init event."""
    new_session_id = event.get("session_id")
    if new_session_id and new_session_id != session_id:
        print_success(f"Session ID: {new_session_id}")
    return new_session_id, None


def _handle_stream_event(event: dict, streaming: StreamingDisplay, session_id: str | None, client) -> EventResult:
    """Handle streaming text delta event."""
    stream_data = event.get("event", {})
    if stream_data.get("type") != "content_block_delta":
        return None, None

    delta = stream_data.get("delta", {})
    if delta.get("type") == "text_delta":
        text = delta.get("text", "")
        if text:
            streaming.append_text(text)
    return None, None


def _handle_assistant(event: dict, streaming: StreamingDisplay, session_id: str | None, client) -> EventResult:
    """Handle complete assistant message event."""
    content = event.get("content", [])
    for block in content:
        block_type = block.get("type")
        if block_type == "text" and not streaming.has_content():
            display_assistant_message(block.get("text", ""))
        elif block_type == "tool_use":
            streaming.close()
            display_tool_use(block.get("name", "unknown"), block.get("input", {}))
    return None, None


def _handle_tool_use(event: dict, streaming: StreamingDisplay, session_id: str | None, client) -> EventResult:
    """Handle direct tool use event (from API mode)."""
    streaming.close()
    display_tool_use(event.get("name", "unknown"), event.get("input", {}))
    return None, None


def _handle_user(event: dict, streaming: StreamingDisplay, session_id: str | None, client) -> EventResult:
    """Handle user messages (tool results)."""
    content = event.get("content", [])
    for block in content:
        if block.get("type") == "tool_result":
            streaming.close()
            display_tool_result(block.get("content", ""))
    return None, None


def _handle_ask_user_question(event: dict, streaming: StreamingDisplay, session_id: str | None, client) -> EventResult:
    """Handle ask user question event."""
    streaming.close()
    question_id = event.get("question_id")
    questions = event.get("questions", [])
    timeout = event.get("timeout", 60)

    answers = collect_user_answers(questions, timeout)
    return None, {"question_id": question_id, "answers": answers}


def _handle_success(event: dict, streaming: StreamingDisplay, session_id: str | None, client) -> EventResult:
    """Handle success event."""
    streaming.close()
    num_turns = event.get("num_turns", 0)
    cost = event.get("total_cost_usd", 0)
    if num_turns > 0:
        print_info(f"\n[Session: {num_turns} turns, ${cost:.6f}]")
    return None, None


def _handle_error(event: dict, streaming: StreamingDisplay, session_id: str | None, client) -> EventResult:
    """Handle error event."""
    streaming.close()
    error_msg = event.get("error", "Unknown error")
    print_error(f"\nError: {error_msg}")
    return None, None


def _handle_info(event: dict, streaming: StreamingDisplay, session_id: str | None, client) -> EventResult:
    """Handle info event."""
    streaming.close()
    info_msg = event.get("message", "")
    if info_msg:
        print_info(info_msg)
    return None, None


def _handle_cancelled(event: dict, streaming: StreamingDisplay, session_id: str | None, client) -> EventResult:
    """Handle cancelled event."""
    streaming.close()
    print_warning("Task cancelled.")
    return None, None


def _handle_compact_started(event: dict, streaming: StreamingDisplay, session_id: str | None, client) -> EventResult:
    """Handle compact started event."""
    streaming.close()
    print_info("Compacting context...")
    return None, None


def _handle_compact_completed(event: dict, streaming: StreamingDisplay, session_id: str | None, client) -> EventResult:
    """Handle compact completed event."""
    streaming.close()
    summary = event.get("summary", "")
    if summary:
        print_success(f"Context compacted: {summary}")
    else:
        print_success("Context compacted successfully.")
    return None, None


def _handle_thinking(event: dict, streaming: StreamingDisplay, session_id: str | None, client) -> EventResult:
    """Handle thinking event (display dimmed)."""
    text = event.get("text", "")
    if text:
        console.print(f"[dim italic]{text}[/dim italic]")
    return None, None


def _handle_assistant_text(event: dict, streaming: StreamingDisplay, session_id: str | None, client) -> EventResult:
    """Handle assistant text event (canonical cleaned text)."""
    # If we already displayed via streaming, skip duplicate display
    if streaming.has_content():
        return None, None
    text = event.get("text", "")
    if text:
        display_assistant_message(text)
    return None, None


EVENT_HANDLERS = {
    "init": _handle_init,
    "stream_event": _handle_stream_event,
    "assistant": _handle_assistant,
    "tool_use": _handle_tool_use,
    "user": _handle_user,
    "ask_user_question": _handle_ask_user_question,
    "success": _handle_success,
    "error": _handle_error,
    "info": _handle_info,
    "cancelled": _handle_cancelled,
    "compact_started": _handle_compact_started,
    "compact_completed": _handle_compact_completed,
    "thinking": _handle_thinking,
    "assistant_text": _handle_assistant_text,
}


def process_event(event: dict, streaming: StreamingDisplay, session_id: str | None, client=None) -> EventResult:
    """Process a single event from the response stream.

    Args:
        event: Event dictionary from the client.
        streaming: StreamingDisplay instance for text accumulation.
        session_id: Current session ID (updated if init event received).
        client: Optional client instance for sending answers.

    Returns:
        Tuple of (updated session_id or None, question_data or None).
        question_data contains question_id and answers if user answered a question.
    """
    handler = EVENT_HANDLERS.get(event.get("type"))
    if handler is None:
        return None, None

    return handler(event, streaming, session_id, client)


async def async_chat(client) -> None:
    """Async chat loop implementation.

    Args:
        client: APIClient instance.
    """
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

    print_info("Commands: exit, interrupt, new, resume, agent, sessions, skills, help")
    print_info("Type your message or command below.\n")

    switch_agent_fn = getattr(client, 'switch_agent', None)
    search_sessions_fn = getattr(client, 'search_sessions', None)
    send_compact_fn = getattr(client, 'send_compact', None)
    cmd_ctx = CommandContext(
        list_skills=client.list_skills,
        list_agents=client.list_agents,
        list_subagents=client.list_subagents,
        list_sessions=client.list_sessions,
        interrupt=client.interrupt,
        create_session=client.create_session,
        close_session=client.close_session,
        resume_previous_session=client.resume_previous_session,
        switch_agent=switch_agent_fn,
        search_sessions=search_sessions_fn,
        send_compact=send_compact_fn,
        current_session_id=session_id,
    )

    turn_count = 0

    while True:
        try:
            theme = get_theme()
            user_input = console.input(f"\n[Turn {turn_count + 1}] [{theme.colors.user}]You:[/{theme.colors.user}] ")

            handled, should_break = await handle_command(user_input, cmd_ctx)
            if should_break:
                break
            if handled:
                cmd_ctx.current_session_id = client.session_id
                session_id = client.session_id
                cmd_lower = user_input.lower().strip()
                if cmd_lower in ('new', 'resume') or cmd_lower.startswith('resume ') or cmd_lower.startswith('agent '):
                    turn_count = 0
                continue

            display_user_message(user_input)

            streaming = StreamingDisplay()
            try:
                async for event in client.send_message(user_input):
                    new_session_id, question_data = process_event(event, streaming, session_id, client)
                    if new_session_id:
                        session_id = new_session_id
                        cmd_ctx.current_session_id = session_id

                    if question_data and hasattr(client, 'send_answer'):
                        await client.send_answer(
                            question_data["question_id"],
                            question_data["answers"]
                        )

                streaming.close()
                console.print()
                turn_count += 1

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


async def select_agent_interactive(api_url: str, api_key: str | None = None) -> str | None:
    """Show agent selection menu and return selected agent_id.

    Args:
        api_url: API server URL to fetch agents from.
        api_key: Optional API key for authentication.

    Returns:
        Selected agent_id or None for default.
    """
    import httpx

    try:
        headers = {"X-API-Key": api_key} if api_key else {}
        async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
            response = await client.get(f"{api_url}/api/v1/config/agents")
            response.raise_for_status()
            data = response.json()
            agents = data.get("agents", [])
    except Exception as e:
        print_error(f"Failed to fetch agents: {e}")
        return None

    if not agents:
        print_warning("No agents available")
        return None

    theme = get_theme()
    prompt_color = theme.colors.prompt

    print_header("Select an Agent", f"bold {theme.colors.header}")
    print_info("Enter number to select, or press Enter for default:\n")

    for i, agent in enumerate(agents, 1):
        agent_id = agent.get("agent_id", "unknown")
        name = agent.get("name", agent_id)
        is_default = agent.get("is_default", False)
        description = agent.get("description", "")

        default_marker = " [default]" if is_default else ""
        console.print(f"  [{prompt_color}]{i}.[/{prompt_color}] [bold]{name}[/bold]{default_marker}")
        if description:
            truncated = description[:60] + ('...' if len(description) > 60 else '')
            console.print(f"     [dim]{truncated}[/dim]")

    console.print()

    try:
        choice = console.input(f"[{prompt_color}]Select agent (1-{len(agents)}, Enter=default): [/{prompt_color}]")
        choice = choice.strip()

        if not choice:
            return _select_default_agent(agents)

        idx = int(choice) - 1
        if 0 <= idx < len(agents):
            selected = agents[idx]
            print_success(f"Using agent: {selected.get('name')}")
            return selected.get("agent_id")

        print_warning("Invalid selection, using default")
        return None

    except (ValueError, EOFError, KeyboardInterrupt):
        print_warning("Using default agent")
        return None


def _select_default_agent(agents: list) -> str | None:
    """Select the default agent from the list.

    Args:
        agents: List of agent dictionaries.

    Returns:
        Agent ID of the default agent, or first agent if no default marked.
    """
    default_agent = next((a for a in agents if a.get("is_default")), agents[0])
    is_default = default_agent.get("is_default", False)
    label = "default agent" if is_default else "agent"
    print_success(f"Using {label}: {default_agent.get('name')}")
    return default_agent.get("agent_id")


def chat_command(
    api_url: str = "http://localhost:7001",
    mode: str = "ws",
    agent_id: str | None = None
) -> None:
    """Start interactive chat session.

    Args:
        api_url: API server URL.
        mode: Connection mode - 'ws' (WebSocket) or 'sse' (HTTP SSE).
        agent_id: Optional agent ID to use.
    """
    api_key = os.getenv("API_KEY")

    if agent_id is None:
        agent_id = asyncio.run(select_agent_interactive(api_url, api_key=api_key))

    if mode == "ws":
        client = WSClient(api_url=api_url, agent_id=agent_id, api_key=api_key)
        print_info("Using WebSocket mode (persistent connection)")
    else:
        client = APIClient(api_url=api_url, api_key=api_key)
        print_info("Using HTTP SSE mode")

    try:
        asyncio.run(async_chat(client))
    except KeyboardInterrupt:
        print_warning("\nExiting...")
