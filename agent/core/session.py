"""Conversation session management for Claude Agent SDK.

Contains the ConversationSession class for managing interactive conversations.
"""
import asyncio
from typing import AsyncIterator

from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
from claude_agent_sdk.types import Message

from agent.core.options import create_enhanced_options, INCLUDE_PARTIAL_MESSAGES
from agent.core.agents import get_agents_info
from agent.core.storage import get_storage
from agent.discovery.skills import discover_skills
from agent.display import (
    console,
    print_header,
    print_success,
    print_warning,
    print_info,
    print_list_item,
    print_command,
    print_session_item,
    print_message,
    process_messages,
)


class ConversationSession:
    """Maintains a single conversation session with Claude."""

    def __init__(self, options: ClaudeAgentOptions | None = None):
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

    def _on_session_id(self, session_id: str):
        """Handle session ID from init message."""
        self.session_id = session_id
        print_info(f"Session ID: {session_id}")
        self._storage.save_session(session_id)  # Always save (deduplicates internally)
        self._session_shown = True

    def _show_skills(self):
        """Display available skills."""
        print_header("Available Skills", "bold cyan")
        skills_data = discover_skills()
        if skills_data:
            for skill in skills_data:
                print_list_item(skill['name'], skill['description'])
            print_info("\nSkills are automatically invoked based on context.")
            print_info("Example: 'Analyze this file for issues' → invokes code-analyzer")
        else:
            print_warning("No skills found. Create .claude/skills/ directory with SKILL.md files.")

    def _show_agents(self):
        """Display available subagents."""
        print_header("Available Subagents", "bold magenta")
        for agent in get_agents_info():
            print_list_item(agent['name'], agent['focus'])
        print_info("\nUse by asking Claude to delegate tasks.")
        print_info("Example: 'Use the researcher to find all API endpoints'")

    def _show_sessions(self):
        """Display saved session history."""
        print_header("Session History", "bold blue")
        sessions = self._storage.load_sessions()
        if sessions:
            # Show sessions with index (newest first)
            for i, session in enumerate(sessions, 1):
                label = session.session_id
                if session.first_message:
                    # Truncate first message for display
                    msg = session.first_message[:40] + "..." if len(session.first_message) > 40 else session.first_message
                    label = f"{session.session_id} - {msg}"
                print_session_item(i, label, is_current=(session.session_id == self.session_id))
            print_info(f"\nTotal: {len(sessions)} session(s)")
            print_info("Use 'resume <session_id>' to resume a specific session")
        else:
            print_warning("No sessions saved yet.")

    def _show_help(self):
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

    async def start(self):
        await self.client.connect()

        print_success("Starting conversation session with Skills and Subagents enabled.")
        print_info("Commands: 'exit', 'interrupt', 'new', 'resume', 'sessions', 'skills', 'agents', 'help'")

        while True:
            user_input = input(f"\n[Turn {self.turn_count + 1}] You: ")

            if user_input.lower() == 'exit':
                break
            elif user_input.lower() == 'help':
                self._show_help()
                continue
            elif user_input.lower() == 'skills':
                self._show_skills()
                continue
            elif user_input.lower() == 'agents':
                self._show_agents()
                continue
            elif user_input.lower() == 'sessions':
                self._show_sessions()
                continue
            elif user_input.lower() == 'interrupt':
                await self.client.interrupt()
                print_warning("Task interrupted!")
                continue
            elif user_input.lower() == 'new':
                # Create fresh options for a new session with skills and subagents
                await self._init_session()
                print_success("Started new conversation session with Skills and Subagents (previous context cleared)")
                continue
            elif user_input.lower().startswith('resume'):
                # Resume a session with skills and subagents enabled
                session_id = None

                if user_input.lower() == 'resume':
                    # Resume last session from history
                    session_id = self._storage.get_last_session_id()
                    if not session_id:
                        print_warning("No previous session found to resume.")
                        continue
                else:
                    # Resume specific session
                    session_id = user_input[7:].strip()

                await self._init_session(resume_id=session_id)
                print_success(f"Resumed session with Skills and Subagents: {session_id}")
                continue

            # Send message - Claude remembers all previous messages in this session
            await print_message("user", user_input)

            # Create async generator that queries and receives response
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
            console.print()  # New line after response

        await self.client.disconnect()
        print_success(f"Conversation ended after {self.turn_count} turns.")


async def main():
    """Main entry point with Skills and Subagents enabled."""
    options = create_enhanced_options()
    session = ConversationSession(options)
    await session.start()


if __name__ == "__main__":
    asyncio.run(main())
