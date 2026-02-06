#!/usr/bin/env python3
"""
Test agent teams feature - Claude spawns multiple specialized subagents.

This test creates files in backend/tests/team_test/ to demonstrate
inter-agent communication and coordination.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import os
os.environ['CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS'] = '1'

import asyncio

from claude_agent_sdk import ClaudeSDKClient
from agent.display import process_messages, print_header, print_info, print_message
from agent.core import create_agent_sdk_options


async def main() -> None:
    """Test agent teams with inter-agent communication."""
    print_header("Claude Agent SDK - Agent Teams Test", style="bold cyan")

    options = create_agent_sdk_options()
    print_info(f"Working directory: {options.cwd}")
    print_info(f"Agent teams: ENABLED (CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1)")
    print_info(f"Test output: backend/tests/team_test/")
    print()

    client = ClaudeSDKClient(options)

    prompt = """Create an agent team with 3 members:
1. 'planner' - plans the task
2. 'creator' - creates the files
3. 'reviewer' - reviews the work

Task: Create 3 test files in backend/tests/team_test/ folder:
- hello.txt with content 'Hello from Agent Team!'
- team.txt with each agent's name and role
- summary.txt with a brief summary of what the team accomplished

IMPORTANT: Each agent MUST communicate with others before proceeding.
- Planner should tell Creator what to create
- Creator should tell Reviewer when done for review
- Reviewer should confirm completion

Show all communication between agents in your response."""

    try:
        await client.connect()

        print_header("Test: Inter-Agent Communication", style="bold yellow")
        print()

        await print_message("user", prompt)
        await client.query(prompt)
        await process_messages(client.receive_response(), stream=True)

    except Exception as e:
        print()
        print_info(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if hasattr(client, "disconnect"):
            await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())