#!/usr/bin/env python3
"""
Direct SDK test: Permission hooks - allowed vs denied operations.

Run: python tests/test00_sdk_permissions.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio

from claude_agent_sdk import ClaudeSDKClient

from agent.display import process_messages, print_header, print_info, print_message
from agent.core import create_agent_sdk_options


async def main() -> None:
    """Test SDK permission hooks with allowed and denied operations."""
    print_header("Claude Agent SDK - Permission Test", style="bold cyan")

    options = create_agent_sdk_options()

    print_info(f"Working directory: {options.cwd}")
    print_info(f"Allowed directories: /tmp and cwd")
    print_info(f"Tools: {', '.join(options.allowed_tools[:5])}...")
    print()

    client = ClaudeSDKClient(options)

    import time
    ts = int(time.time())
    prompt = f"""Do these 2 tasks and report results:
1. Create file /tmp/test_allowed_{ts}.txt with content 'Allowed write'
2. Create file /etc/test_denied_{ts}.txt with content 'Denied write'

Report: Task 1: SUCCESS/FAILURE, Task 2: SUCCESS/FAILURE"""

    try:
        await client.connect()

        print_header("Test: Allowed vs Denied Write Operations", style="bold yellow")
        print()

        await print_message("user", prompt)
        await client.query(prompt)
        await process_messages(client.receive_response(), stream=True)

        print()
        print_header("Expected Results", style="bold green")
        print_info("Task 1 (/tmp): SUCCESS - allowed directory")
        print_info("Task 2 (/etc): FAILURE - denied by permission hook")

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
