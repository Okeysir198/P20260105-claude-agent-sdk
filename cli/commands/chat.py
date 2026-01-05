"""Chat command for Claude Agent SDK CLI.

Contains the interactive chat loop and related display functions.
"""
import asyncio
import inspect
import json
from typing import Optional

from rich.panel import Panel
from rich.live import Live
from rich import box

from agent.display import (
    console,
    print_header,
    print_success,
    print_warning,
    print_error,
    print_info,
    print_list_item,
    print_command,
    print_session_item,
)
from cli.clients import DirectClient, APIClient


def show_help():
    """Display help information."""
    print_header("Commands")
    print_command("exit       ", "Quit the conversation")
    print_command("interrupt  ", "Stop current task")
    print_command("new        ", "Start new session (clears context)")
    print_command("resume     ", "Resume last session")
    print_command("resume <id>", "Resume specific session by ID")
    print_command("sessions   ", "Show saved session history")
    print_command("skills     ", "Show available Skills")
    print_command("agents     ", "Show available Subagents")
    print_command("help       ", "Show this help")

    print_header("Features")
    console.print("[bold cyan]Skills:[/bold cyan] Filesystem-based capabilities (.claude/skills/)")
    print_list_item("code-analyzer", "Analyze Python code for patterns and issues")
    print_list_item("doc-generator", "Generate documentation for code")
    print_list_item("issue-tracker", "Track and categorize code issues")

    console.print("\n[bold magenta]Subagents:[/bold magenta] Programmatic agents with specialized prompts")
    print_list_item("researcher", "Research and explore codebase")
    print_list_item("reviewer", "Code review and quality analysis")
    print_list_item("file_assistant", "File navigation and search")

    print_header("Example Queries")
    print_info("'Analyze the main.py file for issues'")
    print_info("'Use the researcher to find all API endpoints'")
    print_info("'Generate documentation for this module'")
    print_info("'Use the reviewer to check security issues'")


async def show_skills(client):
    """Display available skills."""
    print_header("Available Skills", "bold cyan")

    # Check if method is async or sync
    if hasattr(client, 'list_skills'):
        method = client.list_skills
        if inspect.iscoroutinefunction(method):
            skills = await method()
        else:
            skills = method()  # DirectClient has sync method
    else:
        skills = []

    if skills:
        for skill in skills:
            print_list_item(skill['name'], skill['description'])
        print_info("\nSkills are automatically invoked based on context.")
        print_info("Example: 'Analyze this file for issues' -> invokes code-analyzer")
    else:
        print_warning("No skills found.")


async def show_agents(client):
    """Display available subagents."""
    print_header("Available Subagents", "bold magenta")

    # Check if method is async or sync
    if hasattr(client, 'list_agents'):
        method = client.list_agents
        if inspect.iscoroutinefunction(method):
            agents = await method()
        else:
            agents = method()  # DirectClient has sync method
    else:
        agents = []

    if agents:
        for agent in agents:
            print_list_item(agent['name'], agent['focus'])
        print_info("\nUse by asking Claude to delegate tasks.")
        print_info("Example: 'Use the researcher to find all API endpoints'")
    else:
        print_warning("No agents found.")


async def show_sessions(client):
    """Display saved session history."""
    print_header("Session History", "bold blue")

    # Check if method is async or sync
    if hasattr(client, 'list_sessions'):
        method = client.list_sessions
        if inspect.iscoroutinefunction(method):
            sessions = await method()
        else:
            sessions = method()  # DirectClient has sync method
    else:
        sessions = []

    if sessions:
        for i, session in enumerate(sessions, 1):
            session_id = session.get('session_id', 'unknown')
            is_current = session.get('is_current', False)
            print_session_item(i, session_id, is_current=is_current)
        print_info(f"\nTotal: {len(sessions)} session(s)")
        print_info("Use 'resume <session_id>' to resume a specific session")
    else:
        print_warning("No sessions found.")


async def async_chat(client, initial_session_id: Optional[str] = None):
    """Async chat loop implementation.

    Args:
        client: DirectClient or APIClient instance.
        initial_session_id: Optional session ID to resume.
    """
    # Create or resume session
    try:
        session_info = await client.create_session(resume_session_id=initial_session_id)
        session_id = session_info.get("session_id")

        if session_info.get("resumed"):
            print_success(f"Resuming session: {session_id}")
        else:
            print_info("Ready for new conversation (session ID will be assigned on first message)")

    except Exception as e:
        print_error(f"Failed to prepare session: {e}")
        await client.disconnect()
        return

    print_info("Commands: exit, interrupt, new, resume, sessions, skills, agents, help")
    print_info("Type your message or command below.\n")

    turn_count = 0

    while True:
        try:
            # Get user input
            user_input = console.input(f"\n[Turn {turn_count + 1}] [cyan]You:[/cyan] ")

            # Handle commands
            if user_input.lower() == 'exit':
                break

            elif user_input.lower() == 'help':
                show_help()
                continue

            elif user_input.lower() == 'skills':
                await show_skills(client)
                continue

            elif user_input.lower() == 'agents':
                await show_agents(client)
                continue

            elif user_input.lower() == 'sessions':
                await show_sessions(client)
                continue

            elif user_input.lower() == 'interrupt':
                success = await client.interrupt()
                if success:
                    print_warning("Task interrupted!")
                else:
                    print_error("Failed to interrupt task.")
                continue

            elif user_input.lower() == 'new':
                # Start new session (create_session handles cleanup of existing client)
                try:
                    session_info = await client.create_session()
                    session_id = None  # Will be set on first message
                    turn_count = 0
                    print_info("Ready for new conversation (session ID will be assigned on first message)")
                except Exception as e:
                    print_error(f"Failed to prepare new session: {e}")
                    break
                continue

            elif user_input.lower().startswith('resume'):
                # Resume a session
                parts = user_input.split(maxsplit=1)
                resume_id = parts[1].strip() if len(parts) > 1 else None

                if not resume_id:
                    # Try to get last session from history
                    sessions = client.list_sessions() if hasattr(client, 'list_sessions') else []
                    if isinstance(sessions, list) and len(sessions) > 0:
                        resume_id = sessions[0].get('session_id')
                    else:
                        print_warning("No previous session to resume. Specify session ID: resume <id>")
                        continue

                try:
                    session_info = await client.create_session(resume_session_id=resume_id)
                    session_id = session_info.get("session_id")
                    turn_count = 0
                    print_success(f"Resumed session: {session_id}")
                except Exception as e:
                    print_error(f"Failed to resume session: {e}")
                    break
                continue

            # Display user message with Rich panel
            user_panel = Panel(
                user_input,
                title="[cyan bold]⬤ USER[/cyan bold]",
                title_align="left",
                border_style="cyan",
                width=80,
                box=box.ROUNDED,
            )
            console.print(user_panel)

            # Track assistant text for streaming
            streaming_text = []
            live_panel = None

            try:
                async for event in client.send_message(user_input):
                    # Handle different event types
                    event_type = event.get("type")

                    if event_type == "init":
                        # Update session ID when we get the real one from SDK
                        new_session_id = event.get("session_id")
                        if new_session_id and new_session_id != session_id:
                            session_id = new_session_id
                            print_success(f"Session ID: {session_id}")

                    elif event_type == "stream_event":
                        # Handle streaming events from SDK
                        stream_data = event.get("event", {})
                        if stream_data.get("type") == "content_block_delta":
                            delta = stream_data.get("delta", {})
                            if delta.get("type") == "text_delta":
                                text = delta.get("text", "")
                                if text:
                                    streaming_text.append(text)

                                    # Create live panel for streaming
                                    if live_panel is None:
                                        live_panel = Live("", console=console, refresh_per_second=30)
                                        live_panel.__enter__()

                                    # Update the live panel
                                    panel = Panel(
                                        "".join(streaming_text),
                                        title="[green bold]⬤ ASSISTANT (STREAMING)[/green bold]",
                                        title_align="left",
                                        border_style="green",
                                        width=80,
                                        box=box.ROUNDED,
                                    )
                                    live_panel.update(panel)

                    elif event_type == "assistant":
                        # Handle complete assistant message
                        content = event.get("content", [])
                        for block in content:
                            if block.get("type") == "text":
                                text = block.get("text", "")
                                # Only display if not already streamed
                                if not streaming_text:
                                    panel = Panel(
                                        text,
                                        title="[green bold]⬤ ASSISTANT[/green bold]",
                                        title_align="left",
                                        border_style="green",
                                        width=80,
                                        box=box.ROUNDED,
                                    )
                                    console.print(panel)

                            elif block.get("type") == "tool_use":
                                # Close live panel if open before showing tool use
                                if live_panel is not None:
                                    live_panel.__exit__(None, None, None)
                                    live_panel = None

                                # Display tool use with Rich formatting
                                tool_name = block.get("name", "unknown")
                                tool_input = block.get("input", {})

                                display_content = f"[bold cyan]Tool:[/bold cyan] {tool_name}\n\n"
                                display_content += "[bold]Parameters:[/bold]\n"
                                display_content += f"[dim cyan]{json.dumps(tool_input, indent=2)}[/dim cyan]"

                                panel = Panel(
                                    display_content,
                                    title=f"[yellow bold]⚙ TOOL USE: {tool_name}[/yellow bold]",
                                    title_align="left",
                                    border_style="yellow",
                                    width=80,
                                    box=box.ROUNDED,
                                )
                                console.print(panel)

                    elif event_type == "tool_use":
                        # Direct tool use event (from API mode)
                        # Close live panel if open
                        if live_panel is not None:
                            live_panel.__exit__(None, None, None)
                            live_panel = None

                        tool_name = event.get("name", "unknown")
                        tool_input = event.get("input", {})

                        display_content = f"[bold cyan]Tool:[/bold cyan] {tool_name}\n\n"
                        display_content += "[bold]Parameters:[/bold]\n"
                        display_content += f"[dim cyan]{json.dumps(tool_input, indent=2)}[/dim cyan]"

                        panel = Panel(
                            display_content,
                            title=f"[yellow bold]⚙ TOOL USE: {tool_name}[/yellow bold]",
                            title_align="left",
                            border_style="yellow",
                            width=80,
                            box=box.ROUNDED,
                        )
                        console.print(panel)

                    elif event_type == "user":
                        # Handle user messages (tool results)
                        content = event.get("content", [])
                        for block in content:
                            if block.get("type") == "tool_result":
                                # Close live panel if open
                                if live_panel is not None:
                                    live_panel.__exit__(None, None, None)
                                    live_panel = None

                                # Display tool result with Rich formatting
                                result_content = block.get("content", "")

                                # Truncate if too long
                                if len(result_content) > 1000:
                                    result_content = result_content[:1000] + f"\n\n... (truncated, showing first 1000 of {len(block.get('content', ''))} characters)"

                                panel = Panel(
                                    result_content if result_content else "(empty result)",
                                    title="[blue bold]✓ TOOL RESULT[/blue bold]",
                                    title_align="left",
                                    border_style="blue",
                                    width=80,
                                    box=box.ROUNDED,
                                )
                                console.print(panel)

                    elif event_type == "success":
                        # Close live panel if still open
                        if live_panel is not None:
                            live_panel.__exit__(None, None, None)
                            live_panel = None

                        # Session completed successfully
                        num_turns = event.get("num_turns", 0)
                        cost = event.get("total_cost_usd", 0)
                        if num_turns > 0:
                            print_info(f"\n[Session: {num_turns} turns, ${cost:.6f}]")

                    elif event_type == "error":
                        # Close live panel if still open
                        if live_panel is not None:
                            live_panel.__exit__(None, None, None)
                            live_panel = None

                        error_msg = event.get("error", "Unknown error")
                        print_error(f"\nError: {error_msg}")

                # Close live panel if still open
                if live_panel is not None:
                    live_panel.__exit__(None, None, None)
                    live_panel = None

                console.print()  # New line after response
                turn_count += 1

                # Update turn count in storage (DirectClient only)
                if hasattr(client, 'update_turn_count'):
                    client.update_turn_count(turn_count)

            except Exception as e:
                print_error(f"\nError during message: {e}")
                continue

        except KeyboardInterrupt:
            print_warning("\nInterrupted. Type 'exit' to quit or continue chatting.")
            continue
        except EOFError:
            break

    # Cleanup
    await client.disconnect()
    print_success(f"\nConversation ended after {turn_count} turns.")


def chat_command(ctx):
    """Start interactive chat session.

    Opens an interactive conversation with Claude. Supports both direct SDK
    mode and API mode via HTTP/SSE.
    """
    mode = ctx.obj['mode']
    if mode == 'direct':
        client = DirectClient()
    else:  # api mode
        api_url = ctx.obj['api_url']
        client = APIClient(api_url=api_url)

    initial_session_id = ctx.obj.get('session_id')

    try:
        asyncio.run(async_chat(client, initial_session_id))
    except KeyboardInterrupt:
        print_warning("\nExiting...")
