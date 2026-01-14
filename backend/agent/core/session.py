"""Conversation session management for Claude Agent SDK.

Contains the ConversationSession class for managing interactive conversations
with Skills and Subagents support.
"""
import asyncio
from typing import AsyncIterator

from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
from claude_agent_sdk.types import Message

from agent.core.agent_options import create_enhanced_options, INCLUDE_PARTIAL_MESSAGES
from agent.core.subagents import get_agents_info
from agent.core.storage import get_storage
from agent.discovery.skills import discover_skills
from agent.display import console, print_success, print_info, print_message, process_messages


class ConversationSession:
    """Maintains a single conversation session with Claude.

    Provides an interactive REPL for conversations with Skills and Subagents
    enabled. Manages session lifecycle, command handling, and message display.

    Attributes:
        client: ClaudeSDKClient instance for SDK communication.
        turn_count: Number of completed conversation turns.
        session_id: Current session identifier (assigned on first message).
    """

    def __init__(self, options: ClaudeAgentOptions | None = None):
        """Initialize conversation session.

        Args:
            options: Optional ClaudeAgentOptions. If None, uses default options.
        """
        self.client = ClaudeSDKClient(options)
        self.turn_count = 0
        self.session_id = None
        self._session_shown = False
        self._first_message = None
        self._storage = get_storage()

    async def _init_session(self, resume_id: str | None = None) -> None:
        """Initialize or reinitialize the session.

        Args:
            resume_id: If provided, resume the session with this ID.
                       If None, starts a fresh new session.
        """
        await self.client.disconnect()
        options = create_enhanced_options(resume_session_id=resume_id)
        self.client = ClaudeSDKClient(options)
        await self.client.connect()
        self.turn_count = 0
        self._session_shown = False

    def _on_session_id(self, session_id: str) -> None:
        """Handle session ID from init message.

        Args:
            session_id: Session ID received from SDK.
        """
        self.session_id = session_id
        print_info(f"Session ID: {session_id}")
        self._storage.save_session(session_id)
        self._session_shown = True

    def _handle_command(self, user_input: str) -> tuple[bool, bool]:
        """Handle built-in commands synchronously.

        This method handles commands that do not require async operations.
        Async commands (skills, agents, sessions, new, resume) are handled
        separately in the main loop.

        Args:
            user_input: The user's input string.

        Returns:
            Tuple of (handled, should_break):
            - handled: True if command was processed
            - should_break: True if session should exit
        """
        command = user_input.lower().strip()

        if command == 'exit':
            return (True, True)

        if command == 'help':
            self._show_help()
            return (True, False)

        return (False, False)

    def _show_help(self) -> None:
        """Display help information for available commands."""
        from agent.display import print_header, print_command, print_list_item

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

    def _show_skills(self) -> None:
        """Display available skills from filesystem discovery."""
        from agent.display import print_header, print_list_item, print_warning

        print_header("Available Skills", "bold cyan")
        skills_data = discover_skills()
        if skills_data:
            for skill in skills_data:
                print_list_item(skill['name'], skill['description'])
            print_info("\nSkills are automatically invoked based on context.")
            print_info("Example: 'Analyze this file for issues' -> invokes code-analyzer")
        else:
            print_warning("No skills found. Create .claude/skills/ directory with SKILL.md files.")

    def _show_agents(self) -> None:
        """Display available subagents for delegation."""
        from agent.display import print_header, print_list_item

        print_header("Available Subagents", "bold magenta")
        for agent in get_agents_info():
            print_list_item(agent['name'], agent['focus'])
        print_info("\nUse by asking Claude to delegate tasks.")
        print_info("Example: 'Use the researcher to find all API endpoints'")

    def _show_sessions(self) -> None:
        """Display saved session history."""
        from agent.display import print_header, print_session_item, print_warning

        print_header("Session History", "bold blue")
        sessions = self._storage.load_sessions()
        if sessions:
            for i, session in enumerate(sessions, 1):
                label = session.session_id
                if session.first_message:
                    msg = session.first_message[:40] + "..." if len(session.first_message) > 40 else session.first_message
                    label = f"{session.session_id} - {msg}"
                print_session_item(i, label, is_current=(session.session_id == self.session_id))
            print_info(f"\nTotal: {len(sessions)} session(s)")
            print_info("Use 'resume <session_id>' to resume a specific session")
        else:
            print_warning("No sessions saved yet.")

    async def start(self) -> None:
        """Start the interactive conversation session.

        Runs the main REPL loop, handling commands and messages until
        the user exits or an error occurs.
        """
        from agent.display import print_warning

        await self.client.connect()

        print_success("Starting conversation session with Skills and Subagents enabled.")
        print_info("Commands: 'exit', 'interrupt', 'new', 'resume', 'sessions', 'skills', 'agents', 'help'")

        while True:
            user_input = input(f"\n[Turn {self.turn_count + 1}] You: ")
            command = user_input.lower().strip()

            # Handle synchronous commands first
            handled, should_break = self._handle_command(user_input)
            if should_break:
                break
            if handled:
                continue

            # Handle async-requiring commands
            if command == 'skills':
                self._show_skills()
                continue

            if command == 'agents':
                self._show_agents()
                continue

            if command == 'sessions':
                self._show_sessions()
                continue

            if command == 'interrupt':
                await self.client.interrupt()
                print_warning("Task interrupted!")
                continue

            if command == 'new':
                await self._init_session()
                print_success("Started new conversation session with Skills and Subagents (previous context cleared)")
                continue

            if command.startswith('resume'):
                session_id = None
                if command == 'resume':
                    session_id = self._storage.get_last_session_id()
                    if not session_id:
                        print_warning("No previous session found to resume.")
                        continue
                else:
                    session_id = user_input[7:].strip()

                await self._init_session(resume_id=session_id)
                print_success(f"Resumed session with Skills and Subagents: {session_id}")
                continue

            # Send message and process response
            await print_message("user", user_input)

            async def get_response() -> AsyncIterator[Message]:
                await self.client.query(user_input)
                async for msg in self.client.receive_response():
                    yield msg

            await process_messages(
                get_response(),
                stream=INCLUDE_PARTIAL_MESSAGES,
                on_session_id=None if self._session_shown else self._on_session_id
            )

            self.turn_count += 1
            console.print()

        await self.client.disconnect()
        print_success(f"Conversation ended after {self.turn_count} turns.")


async def main() -> None:
    """Main entry point with Skills and Subagents enabled."""
    options = create_enhanced_options()
    session = ConversationSession(options)
    await session.start()


if __name__ == "__main__":
    asyncio.run(main())
