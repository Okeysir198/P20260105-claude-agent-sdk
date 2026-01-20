"""Test the programmatic API for ConversationSession.

This demonstrates how to use the new connect()/send_message()/disconnect() methods.
"""
import asyncio
from agent.core.session import ConversationSession
from agent.core.agent_options import create_enhanced_options


async def test_programmatic_conversation():
    """Test multi-turn conversation using programmatic API."""
    options = create_enhanced_options()
    session = ConversationSession(options, include_partial_messages=True)

    # Connect to Claude SDK
    await session.connect()
    print("Connected to session:", session.get_session_info())

    # Send multiple messages programmatically
    await session.send_message("What is 2 + 2?")
    await session.send_message("What about 5 + 3?")
    await session.send_message("Thank you!")

    # Check session info after conversation
    print("Session info:", session.get_session_info())

    # Disconnect
    await session.disconnect()
    print("Disconnected. Final session info:", session.get_session_info())


async def test_error_handling():
    """Test error handling for programmatic API."""
    options = create_enhanced_options()
    session = ConversationSession(options)

    # Try to send message without connecting - should raise error
    try:
        await session.send_message("Hello")
        print("ERROR: Should have raised RuntimeError")
    except RuntimeError as e:
        print(f"Correct error: {e}")

    # Try to connect twice - should raise error
    await session.connect()
    try:
        await session.connect()
        print("ERROR: Should have raised RuntimeError for double connect")
    except RuntimeError as e:
        print(f"Correct error: {e}")

    # Cleanup
    await session.disconnect()


if __name__ == "__main__":
    print("=== Test 1: Programmatic Conversation ===")
    asyncio.run(test_programmatic_conversation())

    print("\n=== Test 2: Error Handling ===")
    asyncio.run(test_error_handling())
