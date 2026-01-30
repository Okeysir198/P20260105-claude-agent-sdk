#!/usr/bin/env python3
"""
Direct SDK test: Multi-turn conversation with ConversationSession.

Run: python tests/test_01_sdk_multi_turn.py
"""
import sys
from pathlib import Path

# Add parent directory to path to import agent package
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio

from agent.core.session import ConversationSession
from agent.core.agent_options import create_agent_sdk_options
from agent.display import print_header, print_info


async def conduct_turn(session: ConversationSession, turn_number: int, prompt: str) -> None:
    """Conduct a single turn using ConversationSession.

    Args:
        session: The ConversationSession instance
        turn_number: The turn number (1-indexed)
        prompt: The user's prompt for this turn
    """
    print_header(f"Turn {turn_number}", style="bold yellow")
    await session.send_message(prompt)
    print()
    print_info(f"Turn {turn_number} completed")
    print()


async def main() -> None:
    """Demonstrate 3-turn conversation with ConversationSession."""
    print_header("Claude Agent SDK - Multi-Turn Test with ConversationSession", style="bold cyan")

    # Create session with enhanced options (Skills + Subagents)
    options = create_agent_sdk_options()
    # Use default include_partial_messages=True
    session = ConversationSession(options)

    try:
        await session.connect()

        # Three turns
        await conduct_turn(session, 1, "Hello! What is 2 + 2?")
        await conduct_turn(session, 2, "Great! Now what is 5 + 3?")
        await conduct_turn(session, 3, "What were the two answers you gave me in our previous messages?")

        print_header("Test Complete", style="bold green")
        print_info("All 3 turns completed successfully!")
        print_info(f"Session ID: {session.session_id}")
        print_info(f"Total turns: {session.turn_count}")

        # Show session info
        info = session.get_session_info()
        print_info(f"Session info: {info}")
        await session.disconnect()
        info = session.get_session_info()
        print_info(f"Session info: {info}")
    except Exception as e:
        print()
        print_info(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await session.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
