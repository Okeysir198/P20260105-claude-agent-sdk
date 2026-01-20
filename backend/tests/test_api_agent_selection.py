#!/usr/bin/env python3
"""
Simple API test for agent selection and multi-turn conversation.

Tests:
1. List available agents
2. Create conversation with specific agent
3. Multi-turn chat with follow-up messages

Usage:
    # Start the server first:
    python main.py serve --port 7001

    # Run the test:
    python tests/test_api_agent_selection.py
"""
import asyncio
import json
import httpx

API_BASE = "http://localhost:7001"


async def test_list_agents():
    """Test listing available agents."""
    print("\n=== Test: List Agents ===")

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE}/api/v1/config/agents")

        print(f"Status: {response.status_code}")
        data = response.json()

        print(f"Available agents ({len(data.get('agents', []))}):")
        for agent in data.get("agents", []):
            print(f"  - {agent['agent_id']}: {agent['name']} ({agent['type']})")
            if agent.get('is_default'):
                print(f"    ^ DEFAULT AGENT")

        return data.get("agents", [])


async def test_conversation_with_agent(agent_id: str, agent_name: str):
    """Test creating a conversation with a specific agent."""
    print(f"\n=== Test: Conversation with {agent_name} ({agent_id}) ===")

    session_id = None

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Turn 1: Create conversation with specific agent
        print("\n--- Turn 1: Initial message ---")
        response = await client.post(
            f"{API_BASE}/api/v1/conversations",
            json={
                "content": "Hello! Please introduce yourself briefly (1-2 sentences).",
                "agent_id": agent_id
            }
        )

        print(f"Status: {response.status_code}")

        # Parse SSE response
        assistant_text = ""
        for line in response.text.split("\n"):
            if line.startswith("data:"):
                try:
                    data = json.loads(line[5:].strip())
                    if "session_id" in data:
                        session_id = data["session_id"]
                        print(f"Session ID: {session_id}")
                    elif "text" in data:
                        assistant_text += data["text"]
                except json.JSONDecodeError:
                    pass

        print(f"Response: {assistant_text[:200]}..." if len(assistant_text) > 200 else f"Response: {assistant_text}")

        if not session_id:
            print("ERROR: No session_id received")
            return

        # Turn 2: Follow-up message
        print("\n--- Turn 2: Follow-up message ---")
        response = await client.post(
            f"{API_BASE}/api/v1/conversations/{session_id}/stream",
            json={"content": "What is 2 + 2?"}
        )

        assistant_text = ""
        for line in response.text.split("\n"):
            if line.startswith("data:"):
                try:
                    data = json.loads(line[5:].strip())
                    if "text" in data:
                        assistant_text += data["text"]
                except json.JSONDecodeError:
                    pass

        print(f"Response: {assistant_text[:200]}..." if len(assistant_text) > 200 else f"Response: {assistant_text}")

        # Turn 3: Context check
        print("\n--- Turn 3: Context retention check ---")
        response = await client.post(
            f"{API_BASE}/api/v1/conversations/{session_id}/stream",
            json={"content": "What was my first question to you?"}
        )

        assistant_text = ""
        for line in response.text.split("\n"):
            if line.startswith("data:"):
                try:
                    data = json.loads(line[5:].strip())
                    if "text" in data:
                        assistant_text += data["text"]
                except json.JSONDecodeError:
                    pass

        print(f"Response: {assistant_text[:300]}..." if len(assistant_text) > 300 else f"Response: {assistant_text}")

        print(f"\n[OK] Multi-turn conversation completed with session: {session_id}")
        return session_id


async def test_get_history(session_id: str):
    """Test getting conversation history."""
    print(f"\n=== Test: Get History for {session_id} ===")

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE}/api/v1/sessions/{session_id}/history")

        print(f"Status: {response.status_code}")
        data = response.json()

        print(f"Turn count: {data.get('turn_count', 0)}")
        print(f"Messages: {len(data.get('messages', []))}")

        for i, msg in enumerate(data.get("messages", [])[:6]):  # Show first 6 messages
            role = msg.get("role", "unknown")
            content = msg.get("content", "")[:80]
            print(f"  [{i+1}] {role}: {content}...")

        return data


async def main():
    """Run all tests."""
    print("=" * 60)
    print("API Agent Selection & Multi-Turn Test")
    print("=" * 60)
    print(f"API Base: {API_BASE}")

    # Test 1: List agents
    agents = await test_list_agents()

    if not agents:
        print("\nERROR: No agents available. Is the server running?")
        return

    # Test 2: Conversation with default agent (first one)
    default_agent = next((a for a in agents if a.get("is_default")), agents[0])
    session_id = await test_conversation_with_agent(
        default_agent["agent_id"],
        default_agent["name"]
    )

    # Test 3: Get history
    if session_id:
        await test_get_history(session_id)

    # Test 4: Conversation with a different agent (if available)
    if len(agents) > 1:
        other_agent = next((a for a in agents if not a.get("is_default")), None)
        if other_agent:
            print("\n" + "=" * 60)
            print("Testing with different agent...")
            await test_conversation_with_agent(
                other_agent["agent_id"],
                other_agent["name"]
            )

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
