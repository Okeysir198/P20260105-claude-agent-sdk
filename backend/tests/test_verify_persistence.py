"""
Quick test to verify if the SAME session object is reused across multiple turns.
"""
import asyncio
import time
import httpx


async def test_same_session_object():
    """Verify that the same session object is reused across turns."""
    BASE_URL = "http://localhost:8000"
    API_BASE = "http://localhost:8000/api/v1"

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Update URLs to use port 7001
        BASE_URL = "http://localhost:7001"
        API_BASE = "http://localhost:7001/api/v1"

        # Create session
        create_response = await client.post(f"{API_BASE}/sessions", json={})
        temp_id = create_response.json()["session_id"]
        print(f"📝 Created session with temp_id: {temp_id}")

        # First turn - use temp_id
        print("\n--- FIRST TURN (using temp_id) ---")
        start = time.time()
        real_id = None
        async with client.stream(
            "POST",
            f"{API_BASE}/conversations/{temp_id}/stream",
            json={"content": "Say 'First' and nothing else."}
        ) as response:
            async for line in response.aiter_lines():
                if '"event":"session_id"' in line:
                    import json
                    data = json.loads(line.split("data:")[1].strip())
                    real_id = data.get("session_id")
                if '"event":"done"' in line:
                    break
        print(f"First turn completed in {time.time()-start:.2f}s")
        print(f"Real session ID from SDK: {real_id}")

        # Wait a bit
        await asyncio.sleep(1)

        # Second turn - use temp_id again (NOT real_id)
        print("\n--- SECOND TURN (using temp_id again) ---")
        start = time.time()
        async with client.stream(
            "POST",
            f"{API_BASE}/conversations/{temp_id}/stream",
            json={"content": "Say 'Second' and nothing else."}
        ) as response:
            async for line in response.aiter_lines():
                if '"event":"session_id"' in line:
                    import json
                    data = json.loads(line.split("data:")[1].strip())
                    second_real_id = data.get("session_id")
                if '"event":"done"' in line:
                    break
        print(f"Second turn completed in {time.time()-start:.2f}s")
        print(f"Real session ID from SDK: {second_real_id}")

        # Verify
        if real_id == second_real_id:
            print(f"\n✅ SUCCESS: Same session ID ({real_id})")
        else:
            print(f"\n❌ FAILURE: Session IDs differ! First: {real_id}, Second: {second_real_id}")


if __name__ == "__main__":
    asyncio.run(test_same_session_object())
