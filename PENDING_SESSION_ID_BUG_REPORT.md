# Bug Report: Pending Session ID Flow Not Working

## Issue
Sending a second message via a pending session ID fails with `SESSION_NOT_FOUND` error.

## Root Cause
The `pending_session_id` parameter is sent by the frontend but **not used** by the backend.

### Code Path Analysis

#### 1. Frontend sends request with `pending_session_id`
```json
POST /api/v1/conversations
{
  "content": "Hello!",
  "pending_session_id": "pending-1234567890"  // ← Frontend generates this
}
```

#### 2. Router receives the request (conversations.py:74-98)
```python
@router.post("")
async def create_conversation(
    request: CreateConversationRequest,
    conversation_service: ConversationService = Depends(get_conversation_service)
):
    def stream_func():
        return conversation_service.create_and_stream(
            request.content,
            request.resume_session_id,
            request.agent_id,
            request.user_id,
            # ❌ request.pending_session_id is NOT passed!
        )
```

#### 3. Service generates NEW random pending ID (conversation_service.py:94)
```python
async def create_and_stream(self, content, resume_session_id, agent_id, user_id):
    # ...
    session_key = sdk_session_id if is_resuming else f"pending-{int(time.time() * 1000)}"
    #                                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    #                                                     Generates NEW random ID!
```

#### 4. Session registered with wrong key
- Frontend expects: `pending-1234567890`
- Backend registers: `pending-1768610234763` (different timestamp)
- Second message fails because `pending-1234567890` doesn't exist in SessionManager

## Test Results

```
=== First message ===
✅ session_id: ba436e0b-4a43-4b15-89a2-1f3b85febcef
Session registered as: pending-1768610234763 (backend generated)

=== Second message using frontend's pending ID ===
❌ error: Session expired or not found
Because "pending-1234567890" ≠ "pending-1768610234763"
```

## Fix Required

### Option 1: Pass and use frontend's pending ID

**conversations.py** (router):
```python
def stream_func():
    return conversation_service.create_and_stream(
        request.content,
        request.resume_session_id,
        request.agent_id,
        request.user_id,
        request.pending_session_id,  # ← Add this
    )
```

**conversation_service.py** (service):
```python
async def create_and_stream(
    self,
    content: str,
    resume_session_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    user_id: Optional[str] = None,
    pending_session_id: Optional[str] = None,  # ← Add this parameter
):
    # ...
    session_key = sdk_session_id if is_resuming else (pending_session_id or f"pending-{int(time.time() * 1000)}")
    #                                      ^^^^^^^^^^^^^^^^^^^^^ Use frontend's ID if provided
```

### Option 2: Don't use pending IDs at all (simpler)

Remove `pending_session_id` from the flow entirely. Always use the real SDK ID returned in the first `session_id` event for subsequent messages.

**Frontend (use-claude-chat.ts:128-132)**:
```typescript
case 'session_id': {
  const newSessionId = event.data.session_id;
  setSessionId(newSessionId);  // ← Immediately switch to real SDK ID
  onSessionCreated?.(newSessionId);
  break;
}
```

This is simpler and avoids the complexity of pending ID management.

## Recommendation

**Use Option 2** (remove pending IDs). Pending IDs add complexity without much benefit:
- Real SDK IDs are always available in the first event
- Sessions must be in memory anyway for pending IDs to work
- Real SDK IDs work forever, pending IDs are fragile

The frontend should just switch to using the real SDK ID immediately after receiving it.

## Files to Modify

If implementing Option 1:
- `backend/api/routers/conversations.py:89-94`
- `backend/api/services/conversation_service.py:39-45`
- `backend/api/services/conversation_service.py:94`

If implementing Option 2:
- `backend/api/routers/conversations.py:24` (remove pending_session_id from model)
- `backend/api/services/conversation_service.py:94` (remove pending ID logic)
- Update frontend to not send `pending_session_id`

## Test Script

Created `test_pending_final.py` to verify the fix.
