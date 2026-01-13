#!/usr/bin/env python3
"""
Debt Collection Agent Creation Test

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


def get_project_directory() -> Path:
    """Get the project directory."""
    cwd = Path(__file__).parent.absolute()
    return cwd


async def main():

    # Create sandboxed options for safe file operations
    cwd_path = get_project_directory()
    agent_code_dir = cwd_path / "agent_code"  # Assuming agent code is in this subdirectory
    options = create_sandbox_options(
        sandbox_dir=str(cwd_path),
        additional_allowed_dirs=[str(agent_code_dir), "/tmp"]
    )


    # Override system prompt for specialized agent

    print_info(f"Project directory: {str(cwd_path)}")
    print_info(f"Agent code location: {str(agent_code_dir)}")
    print_info(f"Available tools: {', '.join(options.allowed_tools)}")
    print()

    # Create client with debt collection agent
    client = ClaudeSDKClient(options=options)

    # Test
    print()

    prompt = """Using skill to generate voice agent code for debt collection calls."""

    try:
        await client.connect()
        await print_message("user", prompt)
        await client.query(prompt)

        # Use display utilities to process and show response
        await process_messages(client.receive_response(), stream=True)

        print()

    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        # Clean up
        if hasattr(client, 'disconnect'):
            await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
