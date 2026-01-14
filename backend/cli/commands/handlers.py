"""Shared command handlers for CLI commands.

Provides reusable command handling logic for interactive chat sessions,
eliminating duplication between chat.py and session.py.
"""
from typing import Callable, Awaitable, Optional
from dataclasses import dataclass

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


# Command handler type aliases
CommandHandler = Callable[[], Awaitable[None] | None]
CommandResult = tuple[bool, bool]  # (handled, should_break)


@dataclass
class CommandContext:
    """Context for command execution.

    Attributes:
        list_skills: Async function to list available skills.
        list_agents: Async function to list top-level agents.
        list_subagents: Async function to list delegation subagents.
        list_sessions: Async function to list session history.
        interrupt: Async function to interrupt current task.
        create_session: Async function to create/resume session.
        close_session: Async function to close a session.
        resume_previous_session: Async function to resume previous session via API.
        current_session_id: Current session ID (for display).
    """
    list_skills: Callable[[], Awaitable[list[dict]]]
    list_agents: Callable[[], Awaitable[list[dict]]]
    list_subagents: Callable[[], Awaitable[list[dict]]]
    list_sessions: Callable[[], Awaitable[list[dict]]]
    interrupt: Callable[[], Awaitable[bool]]
    create_session: Callable[[Optional[str]], Awaitable[dict]]
    close_session: Callable[[str], Awaitable[None]]
    resume_previous_session: Callable[[], Awaitable[Optional[dict]]]
    current_session_id: Optional[str] = None


def show_help() -> None:
    """Display help information for available commands and features."""
    print_header("Commands")
    print_command("exit       ", "Quit the conversation")
    print_command("interrupt  ", "Stop current task")
    print_command("new        ", "Start new session (clears context)")
    print_command("resume     ", "Resume last session")
    print_command("resume <id>", "Resume specific session by ID")
    print_command("sessions   ", "Show saved session history")
    print_command("skills     ", "Show available Skills")
    print_command("agents     ", "Show top-level agents (for agent_id)")
    print_command("subagents  ", "Show delegation subagents")
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


async def show_skills(list_skills: Callable[[], Awaitable[list[dict]]]) -> None:
    """Display available skills.

    Args:
        list_skills: Async function that returns list of skill dictionaries.
    """
    print_header("Available Skills", "bold cyan")

    skills = await list_skills()
    if skills:
        for skill in skills:
            print_list_item(skill['name'], skill['description'])
        print_info("\nSkills are automatically invoked based on context.")
        print_info("Example: 'Analyze this file for issues' -> invokes code-analyzer")
    else:
        print_warning("No skills found.")


async def show_agents(list_agents: Callable[[], Awaitable[list[dict]]]) -> None:
    """Display available top-level agents (for agent_id selection).

    Args:
        list_agents: Async function that returns list of agent dictionaries.
    """
    print_header("Available Agents", "bold yellow")

    agents = await list_agents()
    if agents:
        for agent in agents:
            agent_id = agent.get('agent_id', 'unknown')
            name = agent.get('name', agent_id)
            is_default = agent.get('is_default', False)
            read_only = agent.get('read_only', False)

            suffix = ""
            if is_default:
                suffix = " [default]"
            if read_only:
                suffix += " [read-only]"

            print_list_item(f"{agent_id}", f"{name}{suffix}")
        print_info("\nUse agent_id when creating a conversation via API.")
    else:
        print_warning("No agents found.")


async def show_subagents(list_subagents: Callable[[], Awaitable[list[dict]]]) -> None:
    """Display available subagents (for delegation within conversations).

    Args:
        list_subagents: Async function that returns list of subagent dictionaries.
    """
    print_header("Available Subagents", "bold magenta")

    subagents = await list_subagents()
    if subagents:
        for subagent in subagents:
            print_list_item(subagent['name'], subagent['focus'])
        print_info("\nUse by asking Claude to delegate tasks.")
        print_info("Example: 'Use the researcher to find all API endpoints'")
    else:
        print_warning("No subagents found.")


async def show_sessions(
    list_sessions: Callable[[], Awaitable[list[dict]]],
    current_session_id: Optional[str] = None
) -> None:
    """Display saved session history.

    Args:
        list_sessions: Async function that returns list of session dictionaries.
        current_session_id: Optional current session ID for highlighting.
    """
    print_header("Session History", "bold blue")

    sessions = await list_sessions()
    if sessions:
        for i, session in enumerate(sessions, 1):
            session_id = session.get('session_id', 'unknown')
            first_message = session.get('first_message')
            is_current = session.get('is_current', False) or session_id == current_session_id

            # Build label with optional first message preview
            label = session_id
            if first_message:
                msg = first_message[:40] + "..." if len(first_message) > 40 else first_message
                label = f"{session_id} - {msg}"

            print_session_item(i, label, is_current=is_current)

        print_info(f"\nTotal: {len(sessions)} session(s)")
        print_info("Use 'resume <session_id>' to resume a specific session")
    else:
        print_warning("No sessions found.")


async def handle_command(user_input: str, ctx: CommandContext) -> CommandResult:
    """Handle a CLI command and return whether it was processed.

    This function processes built-in commands like 'exit', 'help', 'skills', etc.
    and returns a tuple indicating whether the command was handled and whether
    the main loop should break.

    Args:
        user_input: The user's input string.
        ctx: Command context with callbacks for various operations.

    Returns:
        Tuple of (handled, should_break):
        - handled: True if the input was a recognized command
        - should_break: True if the main loop should exit
    """
    command = user_input.lower().strip()

    # Exit command
    if command == 'exit':
        return (True, True)

    # Help command
    if command == 'help':
        show_help()
        return (True, False)

    # Skills command
    if command == 'skills':
        await show_skills(ctx.list_skills)
        return (True, False)

    # Agents command (top-level agents)
    if command == 'agents':
        await show_agents(ctx.list_agents)
        return (True, False)

    # Subagents command (delegation subagents)
    if command == 'subagents':
        await show_subagents(ctx.list_subagents)
        return (True, False)

    # Sessions command
    if command == 'sessions':
        await show_sessions(ctx.list_sessions, ctx.current_session_id)
        return (True, False)

    # Interrupt command
    if command == 'interrupt':
        success = await ctx.interrupt()
        if success:
            print_warning("Task interrupted!")
        else:
            print_error("Failed to interrupt task.")
        return (True, False)

    # New session command
    if command == 'new':
        try:
            # Create new session - previous session will be closed when first message is sent
            await ctx.create_session(None)
            print_info("Ready for new conversation (session ID will be assigned on first message)")
            return (True, False)
        except Exception as e:
            print_error(f"Failed to prepare new session: {e}")
            return (True, True)

    # Resume command (with optional session ID)
    if command.startswith('resume'):
        parts = user_input.split(maxsplit=1)
        resume_id = parts[1].strip() if len(parts) > 1 else None

        try:
            if resume_id:
                # Resume specific session
                session_info = await ctx.create_session(resume_id)
            else:
                # Resume previous session via API
                session_info = await ctx.resume_previous_session()
                if not session_info:
                    print_warning("No previous session to resume. Specify session ID: resume <id>")
                    return (True, False)

            session_id = session_info.get("session_id")
            print_success(f"Resumed session: {session_id}")
            return (True, False)
        except Exception as e:
            print_error(f"Failed to resume session: {e}")
            return (True, True)

    # Not a recognized command
    return (False, False)
