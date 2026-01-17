import asyncio
import sys
sys.path.insert(0, '.')

from cli.clients import APIClient

async def test_followup():
    client = APIClient("http://localhost:7001")
    
    # Create session
    session = await client.create_session()
    print(f"Created session: {session['session_id']}")
    
    # First message
    print("\n=== First message ===")
    async for event in client.send_message("hello"):
        if event.get("type") == "init":
            print(f"Got session_id: {event.get('session_id')}")
        elif event.get("type") == "success":
            print(f"First message complete")
            break
    
    print(f"Client session_id after first message: {client.session_id}")
    
    # Second message
    print("\n=== Second message ===")
    try:
        async for event in client.send_message("what is 2+2"):
            if event.get("type") == "stream_event":
                delta = event.get("event", {}).get("delta", {})
                if delta.get("type") == "text_delta":
                    print(delta.get("text", ""), end="", flush=True)
            elif event.get("type") == "success":
                print(f"\nSecond message complete!")
                break
    except Exception as e:
        print(f"\nError on second message: {e}")
    
    await client.disconnect()

asyncio.run(test_followup())
