#!/usr/bin/env python3
"""
Simple test script for Claude Agent SDK with permission hooks.

This script demonstrates using sandboxed options to restrict
file operations to the tests directory and /tmp.
"""
import sys
from pathlib import Path

# Add parent directory to path to import agent package
sys.path.append(str(Path(__file__).parent.parent))

import asyncio
from claude_agent_sdk import ClaudeSDKClient

# Import display utilities
from agent.display import process_messages, print_header, print_info, print_message
from agent.core import create_sandbox_options


def get_tests_directory() -> str:
    """Get the tests directory."""
    return str(Path(__file__).parent.absolute())


async def main():
    """Demonstrate sandboxed agent with permission hooks."""
    print_header("Claude Agent SDK - Permission Test", style="bold cyan")

    # Create sandboxed options (lean - using predefined options)
    tests_dir = get_tests_directory()
    options = create_sandbox_options(
        sandbox_dir=tests_dir,
        additional_allowed_dirs=["/tmp"]
    )

    print_info(f"Sandbox directory: {options.cwd}")
    print_info("Allowed directories: tests folder and /tmp")
    print_info("Skills and subagents: enabled")
    print_info(f"Available tools: {', '.join(options.allowed_tools)}")
    print()

    # Create client with sandboxed options
    client = ClaudeSDKClient(options=options)

    # Test permissions
    print_header("Test: Write Tool Permissions", style="bold yellow")
    print_info("Testing file operations in different locations")
    print()

    prompt = """
    Test the Write tool permissions:
    1. Create or edit a file named /tmp/test_write.txt with content "Hello from /tmp"
    2. Try to create a file named /home/test_write.txt (should be blocked)
    3. Create or edit a file in the /home/ct-admin/Documents/Langgraph/P20260105-claude-agent-sdk/tests directory named test_write.txt with content "Hello from tests"

    Report the results of each operation.
    """

    try:
        await client.connect()
        await print_message("user", prompt)
        await client.query(prompt)

        # Use display utilities to process and show response
        await process_messages(client.receive_response(), stream=True)

        print()
        print_info("✓ Test completed successfully!")

    except Exception as e:
        print()
        print_info(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up
        if hasattr(client, 'disconnect'):
            await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
