"""
Comprehensive test suite for Claude Agent SDK Backend API endpoints.
Tests all endpoints with focus on 2-turn continuous conversation and session persistence.
"""

import asyncio
import time
import json
from typing import AsyncGenerator
import httpx
import pytest
import pytest_asyncio
from datetime import datetime


BASE_URL = "http://localhost:7001"
API_BASE = "http://localhost:7001/api/v1"
API_TIMEOUT = 60.0  # Maximum timeout for API requests


class TestAPIEndpoints:
    """Comprehensive test suite for all API endpoints."""

    @pytest_asyncio.fixture
    async def client(self) -> AsyncGenerator[httpx.AsyncClient, None]:
        """Create an async HTTP client for testing."""
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            yield client

    @pytest_asyncio.fixture
    async def session_id(self, client: httpx.AsyncClient) -> AsyncGenerator[str, None]:
        """Create a session for testing and cleanup afterwards."""
        # Create session
        response = await client.post(f"{API_BASE}/sessions", json={})
        assert response.status_code in [200, 201]
        data = response.json()
        sid = data["session_id"]

        yield sid

        # Cleanup: close and delete session
        try:
            await client.post(f"{API_BASE}/sessions/{sid}/close")
            await client.delete(f"{API_BASE}/sessions/{sid}")
        except Exception:
            pass

    # ==================== Health Endpoint Tests ====================

    @pytest.mark.asyncio
    async def test_health_check(self, client: httpx.AsyncClient):
        """Test health check endpoint."""
        response = await client.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        print("✓ Health check passed")

    # ==================== Configuration Endpoint Tests ====================

    @pytest.mark.asyncio
    async def test_config_skills(self, client: httpx.AsyncClient):
        """Test getting available skills."""
        response = await client.get(f"{API_BASE}/config/skills")
        assert response.status_code == 200
        data = response.json()
        assert "skills" in data
        print(f"✓ Available skills: {len(data.get('skills', []))}")

    @pytest.mark.asyncio
    async def test_config_agents(self, client: httpx.AsyncClient):
        """Test getting top-level agents."""
        response = await client.get(f"{API_BASE}/config/agents")
        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        print(f"✓ Available agents: {len(data.get('agents', []))}")

    @pytest.mark.asyncio
    async def test_config_subagents(self, client: httpx.AsyncClient):
        """Test getting available subagents."""
        response = await client.get(f"{API_BASE}/config/subagents")
        assert response.status_code == 200
        data = response.json()
        assert "subagents" in data
        print(f"✓ Available subagents: {len(data.get('subagents', []))}")

    # ==================== Session Management Tests ====================

    @pytest.mark.asyncio
    async def test_create_session(self, client: httpx.AsyncClient):
        """Test creating a new session."""
        response = await client.post(f"{API_BASE}/sessions", json={})
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["status"] == "ready"
        assert data["resumed"] == False
        print(f"✓ Created session: {data['session_id']}")

        # Cleanup
        await client.delete(f"{API_BASE}/sessions/{data['session_id']}")

    @pytest.mark.asyncio
    async def test_create_session_with_agent(self, client: httpx.AsyncClient):
        """Test creating a session with a specific agent."""
        response = await client.post(f"{API_BASE}/sessions", json={"agent_id": "default"})
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        print(f"✓ Created session with agent: {data['session_id']}")

        # Cleanup
        await client.delete(f"{API_BASE}/sessions/{data['session_id']}")

    @pytest.mark.asyncio
    async def test_list_sessions_empty(self, client: httpx.AsyncClient):
        """Test listing sessions when empty."""
        response = await client.get(f"{API_BASE}/sessions")
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        print(f"✓ Listed sessions (count: {len(data.get('sessions', []))})")

    @pytest.mark.asyncio
    async def test_list_sessions_with_data(self, client: httpx.AsyncClient, session_id: str):
        """Test listing sessions after creating one."""
        # Send a message to ensure session has data
        await client.post(
            f"{API_BASE}/conversations/{session_id}/stream",
            json={"content": "Hello, this is a test message. Just say 'ACK' and nothing else."}
        )

        # Give it a moment to process
        await asyncio.sleep(2)

        # List sessions
        response = await client.get(f"{API_BASE}/sessions")
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        print(f"✓ Listed sessions with data (count: {len(data.get('sessions', []))})")

    @pytest.mark.asyncio
    async def test_close_session(self, client: httpx.AsyncClient):
        """Test closing a session."""
        # Create session
        create_response = await client.post(f"{API_BASE}/sessions", json={})
        sid = create_response.json()["session_id"]

        # Close session
        response = await client.post(f"{BASE_URL}/sessions/{sid}/close")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "closed"

        # Cleanup
        await client.delete(f"{API_BASE}/sessions/{sid}")
        print(f"✓ Closed session: {sid}")

    @pytest.mark.asyncio
    async def test_delete_session(self, client: httpx.AsyncClient):
        """Test deleting a session."""
        # Create session
        create_response = await client.post(f"{API_BASE}/sessions", json={})
        sid = create_response.json()["session_id"]

        # Delete session
        response = await client.delete(f"{API_BASE}/sessions/{sid}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "deleted"
        print(f"✓ Deleted session: {sid}")

    @pytest.mark.asyncio
    async def test_resume_session(self, client: httpx.AsyncClient):
        """Test resuming a previous session."""
        # Create session
        create_response = await client.post(f"{API_BASE}/sessions", json={})
        sid = create_response.json()["session_id"]

        # Close session
        await client.post(f"{BASE_URL}/sessions/{sid}/close")

        # Resume session
        response = await client.post(f"{API_BASE}/sessions", json={"resume_session_id": sid})
        assert response.status_code == 200
        data = response.json()
        assert data["resumed"] == True
        print(f"✓ Resumed session: {sid}")

        # Cleanup
        await client.delete(f"{API_BASE}/sessions/{sid}")

    # ==================== Conversation Tests ====================

    async def _stream_conversation(self, client: httpx.AsyncClient, session_id: str, message: str) -> dict:
        """
        Helper to stream a conversation and collect all events.

        Returns:
            dict with keys: session_id, text_deltas, tool_uses, done_event, duration
        """
        start_time = time.time()
        result = {
            "session_id": None,
            "text_deltas": [],
            "tool_uses": [],
            "done_event": None,
            "duration": 0,
            "full_text": ""
        }

        async with client.stream(
            "POST",
            f"{API_BASE}/conversations/{session_id}/stream",
            json={"content": message},
            timeout=API_TIMEOUT
        ) as response:
            assert response.status_code == 200

            async for line in response.aiter_lines():
                if not line.strip():
                    continue

                # Parse SSE format: "event: <event_name>\ndata: <json_data>"
                if line.startswith("event:"):
                    event = line.split(":", 1)[1].strip()
                    continue

                if line.startswith("data:"):
                    data_str = line.split(":", 1)[1].strip()
                    try:
                        data = json.loads(data_str)

                        if event == "session_id":
                            result["session_id"] = data.get("session_id")
                        elif event == "text_delta":
                            text = data.get("text", "")
                            result["text_deltas"].append(text)
                            result["full_text"] += text
                        elif event == "tool_use":
                            result["tool_uses"].append(data)
                        elif event == "done":
                            result["done_event"] = data
                    except json.JSONDecodeError:
                        pass

        result["duration"] = time.time() - start_time
        return result

    @pytest.mark.asyncio
    async def test_single_turn_conversation(self, client: httpx.AsyncClient, session_id: str):
        """Test a single turn conversation."""
        result = await self._stream_conversation(
            client,
            session_id,
            "What is 2 + 2? Just give me the number."
        )

        assert result["session_id"] is not None
        assert len(result["full_text"]) > 0
        assert result["done_event"] is not None
        assert result["duration"] < 10.0, f"Response took {result['duration']:.2f}s, expected <10s"

        print(f"✓ Single turn conversation completed in {result['duration']:.2f}s")
        print(f"  Session ID: {result['session_id']}")
        print(f"  Response: {result['full_text'][:100]}...")

    @pytest.mark.asyncio
    async def test_two_turn_conversation_with_persistence(self, client: httpx.AsyncClient):
        """
        CRITICAL TEST: Test 2-turn continuous conversation with session persistence.

        This test verifies:
        1. Session ID remains the same across both turns
        2. The agent remembers context from the first turn
        3. Both turns complete in reasonable time (<10s each)
        4. No connection errors occur
        """
        print("\n" + "="*70)
        print("CRITICAL TEST: Two-Turn Conversation with Session Persistence")
        print("="*70)

        # Create session
        create_response = await client.post(f"{API_BASE}/sessions", json={})
        assert create_response.status_code in [200, 201]
        initial_session_id = create_response.json()["session_id"]
        print(f"\n📝 Created session: {initial_session_id}")

        # === FIRST TURN ===
        print("\n--- FIRST TURN ---")
        turn1_start = time.time()
        result1 = await self._stream_conversation(
            client,
            initial_session_id,
            "My name is Alice. What is 2 + 2? Just give me the number."
        )
        turn1_duration = time.time() - turn1_start

        # Verify first turn
        assert result1["session_id"] is not None, "First turn: No session ID received"
        actual_session_id = result1["session_id"]
        assert len(result1["full_text"]) > 0, "First turn: No response text"
        assert result1["done_event"] is not None, "First turn: No done event"
        assert turn1_duration < 10.0, f"First turn took {turn1_duration:.2f}s, expected <10s"

        print(f"✓ First turn completed in {turn1_duration:.2f}s")
        print(f"  Session ID: {actual_session_id}")
        print(f"  Response: {result1['full_text'][:150]}")

        # Wait a bit between turns
        await asyncio.sleep(1)

        # === SECOND TURN ===
        print("\n--- SECOND TURN ---")
        turn2_start = time.time()
        result2 = await self._stream_conversation(
            client,
            actual_session_id,  # Use the SAME session ID
            "What is my name? Just say the name and nothing else."
        )
        turn2_duration = time.time() - turn2_start

        # Verify second turn
        assert result2["session_id"] is not None, "Second turn: No session ID received"
        assert result2["session_id"] == actual_session_id, \
            f"Session ID changed! Expected {actual_session_id}, got {result2['session_id']}"
        assert len(result2["full_text"]) > 0, "Second turn: No response text"
        assert result2["done_event"] is not None, "Second turn: No done event"
        assert turn2_duration < 10.0, f"Second turn took {turn2_duration:.2f}s, expected <10s"

        # Verify context persistence (agent should remember the name)
        response_lower = result2["full_text"].lower()
        assert "alice" in response_lower, \
            f"Context not maintained! Agent should remember name 'Alice'. Response: {result2['full_text']}"

        print(f"✓ Second turn completed in {turn2_duration:.2f}s")
        print(f"  Session ID: {result2['session_id']} (matches!)")
        print(f"  Response: {result2['full_text'][:150]}")

        # Summary
        total_duration = turn1_duration + turn2_duration
        print("\n" + "="*70)
        print("✅ TWO-TURN CONVERSATION TEST PASSED")
        print("="*70)
        print(f"Session ID persisted: {actual_session_id}")
        print(f"Context maintained: Yes (agent remembered 'Alice')")
        print(f"Total duration: {total_duration:.2f}s")
        print(f"Turn 1: {turn1_duration:.2f}s | Turn 2: {turn2_duration:.2f}s")
        print("="*70)

        # Cleanup
        try:
            await client.post(f"{API_BASE}/sessions/{actual_session_id}/close")
            await client.delete(f"{API_BASE}/sessions/{actual_session_id}")
        except Exception:
            pass

    @pytest.mark.asyncio
    async def test_conversation_with_tool_use(self, client: httpx.AsyncClient, session_id: str):
        """Test conversation that triggers tool use."""
        result = await self._stream_conversation(
            client,
            session_id,
            "What is the current date and time? Just give me the date."
        )

        assert result["session_id"] is not None
        assert len(result["full_text"]) > 0
        assert result["duration"] < 10.0

        # Check if any tools were used
        if result["tool_uses"]:
            print(f"✓ Conversation with tool use completed in {result['duration']:.2f}s")
            print(f"  Tools used: {[t['name'] for t in result['tool_uses']]}")
        else:
            print(f"✓ Conversation completed in {result['duration']:.2f}s (no tools)")
        print(f"  Response: {result['full_text'][:100]}...")

    @pytest.mark.asyncio
    async def test_concurrent_conversations_same_session(self, client: httpx.AsyncClient):
        """Test concurrent conversations on the same session."""
        # Create session
        create_response = await client.post(f"{API_BASE}/sessions", json={})
        sid = create_response.json()["session_id"]

        # Send two concurrent messages
        async def send_message(msg: str):
            return await self._stream_conversation(client, sid, msg)

        results = await asyncio.gather(
            send_message("Say 'First' and nothing else."),
            send_message("Say 'Second' and nothing else."),
            return_exceptions=True
        )

        # At least one should succeed
        successful = [r for r in results if not isinstance(r, Exception)]
        assert len(successful) > 0, "Both concurrent requests failed"

        print(f"✓ Concurrent conversations: {len(successful)} succeeded")

        # Cleanup
        await client.delete(f"{API_BASE}/sessions/{sid}")

    @pytest.mark.asyncio
    async def test_conversation_interrupt(self, client: httpx.AsyncClient, session_id: str):
        """Test interrupting a conversation."""
        # Start a conversation in background
        async def slow_conversation():
            return await self._stream_conversation(
                client,
                session_id,
                "Count from 1 to 100 slowly."
            )

        # Start the conversation
        task = asyncio.create_task(slow_conversation())

        # Wait a bit then interrupt
        await asyncio.sleep(2)
        response = await client.post(f"{API_BASE}/conversations/{session_id}/interrupt")
        assert response.status_code == 200

        # Wait for task to complete (may be interrupted)
        try:
            await asyncio.wait_for(task, timeout=5.0)
            print("✓ Conversation interrupted successfully")
        except asyncio.TimeoutError:
            print("✓ Conversation interrupt sent")

    # ==================== Error Handling Tests ====================

    @pytest.mark.asyncio
    async def test_invalid_session_id(self, client: httpx.AsyncClient):
        """Test using an invalid session ID."""
        fake_sid = "fake-session-id-12345"

        response = await client.post(
            f"{API_BASE}/conversations/{fake_sid}/stream",
            json={"content": "Hello"}
        )
        # Should return error (404 or 400)
        assert response.status_code in [400, 404]
        print(f"✓ Invalid session ID handled correctly (status {response.status_code})")

    @pytest.mark.asyncio
    async def test_empty_message(self, client: httpx.AsyncClient, session_id: str):
        """Test sending an empty message."""
        response = await client.post(
            f"{API_BASE}/conversations/{session_id}/stream",
            json={"content": ""}
        )
        # Should return validation error
        assert response.status_code == 422
        print("✓ Empty message rejected correctly")

    @pytest.mark.asyncio
    async def test_delete_nonexistent_session(self, client: httpx.AsyncClient):
        """Test deleting a session that doesn't exist."""
        fake_sid = "nonexistent-session-123"
        response = await client.delete(f"{API_BASE}/sessions/{fake_sid}")
        # Should handle gracefully
        assert response.status_code in [200, 404]
        print(f"✓ Delete nonexistent session handled (status {response.status_code})")


# ==================== Performance Benchmark Tests ====================

class TestPerformanceBenchmarks:
    """Performance benchmarks for API endpoints."""

    @pytest_asyncio.fixture
    async def client(self):
        async with httpx.AsyncClient(timeout=60.0) as client:
            yield client

    @pytest.mark.asyncio
    async def test_session_creation_performance(self, client: httpx.AsyncClient):
        """Benchmark session creation."""
        times = []
        for i in range(5):
            start = time.time()
            response = await client.post(f"{API_BASE}/sessions", json={})
            duration = time.time() - start
            times.append(duration)
            assert response.status_code in [200, 201]
            await client.delete(f"{API_BASE}/sessions/{response.json()['session_id']}")

        avg_time = sum(times) / len(times)
        print(f"✓ Session creation avg: {avg_time:.3f}s (5 iterations)")
        assert avg_time < 1.0, f"Session creation too slow: {avg_time:.3f}s"

    @pytest.mark.asyncio
    async def test_conversation_response_time(self, client: httpx.AsyncClient):
        """Benchmark conversation response time."""
        # Create session
        response = await client.post(f"{API_BASE}/sessions", json={})
        sid = response.json()["session_id"]

        times = []
        for i in range(3):
            start = time.time()

            async with client.stream(
                "POST",
                f"{API_BASE}/conversations/{sid}/stream",
                json={"content": f"What is {i} + {i}? Just give the number."}
            ) as resp:
                async for line in resp.aiter_lines():
                    if '"event":"done"' in line:
                        break

            duration = time.time() - start
            times.append(duration)
            print(f"  Iteration {i+1}: {duration:.2f}s")

        avg_time = sum(times) / len(times)
        print(f"✓ Conversation response avg: {avg_time:.2f}s (3 iterations)")

        # Cleanup
        await client.delete(f"{API_BASE}/sessions/{sid}")


# ==================== Integration Test ====================

class TestEndToEndIntegration:
    """End-to-end integration test simulating real-world usage."""

    @pytest.mark.asyncio
    async def test_complete_workflow(self):
        """
        Complete workflow test:
        1. Check health
        2. Get configuration
        3. Create session
        4. Multi-turn conversation
        5. List sessions
        6. Close session
        7. Delete session
        """
        print("\n" + "="*70)
        print("END-TO-END INTEGRATION TEST")
        print("="*70)

        async with httpx.AsyncClient(timeout=60.0) as client:
            # 1. Health check
            print("\n1. Health check...")
            response = await client.get(f"{BASE_URL}/health")
            assert response.status_code == 200
            print("   ✓ Service is healthy")

            # 2. Get configuration
            print("\n2. Getting configuration...")
            response = await client.get(f"{API_BASE}/config/agents")
            assert response.status_code == 200
            agents = response.json().get("agents", [])
            print(f"   ✓ Found {len(agents)} agents")

            # 3. Create session
            print("\n3. Creating session...")
            response = await client.post(f"{API_BASE}/sessions", json={})
            assert response.status_code == 200
            sid = response.json()["session_id"]
            print(f"   ✓ Session created: {sid}")

            # 4. Multi-turn conversation
            print("\n4. Multi-turn conversation...")
            turns = [
                "Remember the number 42.",
                "What number did I just tell you? Just say the number.",
            ]

            for i, message in enumerate(turns, 1):
                print(f"\n   Turn {i}: {message}")
                start = time.time()

                full_response = ""
                async with client.stream(
                    "POST",
                    f"{API_BASE}/conversations/{sid}/stream",
                    json={"content": message}
                ) as resp:
                    async for line in resp.aiter_lines():
                        if '"event":"text_delta"' in line:
                            data = json.loads(line.split("data:")[1].strip())
                            full_response += data.get("text", "")
                        if '"event":"done"' in line:
                            break

                duration = time.time() - start
                print(f"   ✓ Response in {duration:.2f}s")
                print(f"   Response: {full_response[:100]}...")

                await asyncio.sleep(0.5)

            # 5. List sessions
            print("\n5. Listing sessions...")
            response = await client.get(f"{API_BASE}/sessions")
            assert response.status_code == 200
            sessions = response.json().get("sessions", [])
            print(f"   ✓ Found {len(sessions)} session(s)")

            # 6. Close session
            print("\n6. Closing session...")
            response = await client.post(f"{BASE_URL}/sessions/{sid}/close")
            assert response.status_code == 200
            print("   ✓ Session closed")

            # 7. Delete session
            print("\n7. Deleting session...")
            response = await client.delete(f"{API_BASE}/sessions/{sid}")
            assert response.status_code == 200
            print("   ✓ Session deleted")

            print("\n" + "="*70)
            print("✅ END-TO-END INTEGRATION TEST PASSED")
            print("="*70)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s", "--tb=short"])
