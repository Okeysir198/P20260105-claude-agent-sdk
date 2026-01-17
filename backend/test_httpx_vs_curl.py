import asyncio
import httpx
import json

async def test_with_httpx():
    """Test with httpx (like CLI does)"""
    print("=== Testing with httpx ===")
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        # First message
        print("First message...")
        resp1 = await client.post(
            "http://localhost:7001/api/v1/conversations",
            json={"content": "hello from httpx"}
        )
        print(f"Status: {resp1.status_code}")
        
        # Read full response
        content1 = resp1.text
        session_id = None
        for line in content1.split('\n'):
            if 'session_id' in line:
                data = json.loads(line.split('data: ')[1])
                session_id = data.get('session_id')
                break
        
        print(f"Session ID: {session_id}")
        
        await asyncio.sleep(2)
        
        # Second message
        print("\nSecond message...")
        resp2 = await client.post(
            f"http://localhost:7001/api/v1/conversations/{session_id}/stream",
            json={"content": "what is 2+2"}
        )
        print(f"Status: {resp2.status_code}")
        
        # Read first few chunks
        content2 = ""
        async for chunk in resp2.aiter_text():
            content2 += chunk
            if len(content2) > 500:
                break
        
        print(f"Response preview: {content2[:200]}...")

asyncio.run(test_with_httpx())
