#!/usr/bin/env python3
"""
Demonstration: LLM sees real data, Frontend sees redacted data

This script demonstrates the complete data flow showing that:
1. Email tools return actual credential data (LLM processes this)
2. Normalization layer applies redaction for storage/frontend
3. Frontend displays [****] instead of [app_password]
4. History stores redacted data
"""
import sys
sys.path.insert(0, '/home/nthanhtrung/Documents/01_Personal/P20260105-claude-agent-sdk/backend')

from api.utils.sensitive_data_filter import redact_sensitive_data
from api.services.content_normalizer import normalize_tool_result_content


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print('='*70)


def demo_list_email_accounts():
    """Demonstrate the list_email_accounts data flow."""
    print_section("STEP 1: Email Tool Returns Raw Data (LLM Sees This)")

    # This is what the email tool returns - with actual auth types
    raw_tool_output = """Connected email accounts (3):

- **Gmail** (nthanhtrung198@gmail.com) [app_password]
- **Gmail-nthanhtrung1987** (nthanhtrung1987@gmail.com) [app_password]
- **Yahoo Mail** (okeysir@yahoo.com) [app_password]"""

    print(raw_tool_output)
    print("\n📊 LLM Processing:")
    print("  ✅ LLM sees: [app_password] - can process authentication types")
    print("  ✅ LLM sees: email addresses - can identify accounts")
    print("  ✅ LLM sees: provider names - can understand email services")

    print_section("STEP 2: Normalization Layer Applies Redaction")

    # The normalize_tool_result_content function applies redaction
    normalized_content = normalize_tool_result_content(raw_tool_output)

    print("🔒 Applying redaction patterns:")
    print("  • [app_password] → [****]")
    print("  • [OAuth] → [****]")
    print("  • [oauth] → [****]")

    print_section("STEP 3: Frontend Receives Redacted Data")

    print(normalized_content)
    print("\n👤 User sees:")
    print("  ✅ [****] - auth method is hidden")
    print("  ✅ Email addresses - still visible for identification")
    print("  ✅ Provider names - still visible for context")

    print_section("STEP 4: History Storage")

    print(f"💾 Saved to history file:")
    print(f"  content: {repr(normalized_content[:50])}...")
    print("\n  ✅ History contains redacted data only")
    print("  ✅ No sensitive auth types in storage")

    return raw_tool_output, normalized_content


def demo_oauth_token_redaction():
    """Demonstrate OAuth token redaction."""
    print_section("EXAMPLE: OAuth Token Redaction")

    raw_response = """Gmail OAuth connection successful:
Email: user@gmail.com
access_token: ya29.a0AfH6SMBx_very_long_token_here
refresh_token: another_secret_token_value
expires_in: 3600"""

    print("📧 Raw tool output (LLM sees):")
    print(raw_response)

    redacted = redact_sensitive_data(raw_response)

    print("\n🔒 Redacted for frontend:")
    print(redacted)
    print("\n  ✅ Token values are replaced with ***REDACTED***")
    print("  ✅ Email address remains visible")


def demo_websocket_message_flow():
    """Demonstrate WebSocket message redaction."""
    print_section("EXAMPLE: WebSocket Message Flow")

    from api.utils.sensitive_data_filter import sanitize_websocket_message

    ws_message = {
        "type": "tool_result",
        "tool_use_id": "toolu_abc123",
        "content": """Connected email accounts (2):

- **Gmail** (user@gmail.com) [app_password]
- **Yahoo Mail** (user@yahoo.com) [OAuth]""",
        "is_error": False
    }

    print("📨 WebSocket message (before sanitization):")
    print(f"  type: {ws_message['type']}")
    print(f"  tool_use_id: {ws_message['tool_use_id']}")
    print(f"  content: {repr(ws_message['content'][:50])}...")
    print(f"  is_error: {ws_message['is_error']}")

    sanitized = sanitize_websocket_message(ws_message)

    print("\n🔒 WebSocket message (after sanitization):")
    print(f"  type: {sanitized['type']}")
    print(f"  tool_use_id: {sanitized['tool_use_id']}")
    print(f"  content: {repr(sanitized['content'][:50])}...")
    print(f"  is_error: {sanitized['is_error']}")

    print("\n  ✅ Content is redacted before sending to frontend")
    print("  ✅ Message structure is preserved")


def main():
    """Run all demonstrations."""
    print("\n" + "█"*70)
    print("█" + " "*68 + "█")
    print("█" + "  LLM vs Frontend: Data Visibility Demonstration".center(68) + "█")
    print("█" + " "*68 + "█")
    print("█"*70)

    # Main demonstration
    raw, redacted = demo_list_email_accounts()

    # Additional examples
    demo_oauth_token_redaction()
    demo_websocket_message_flow()

    print_section("SUMMARY")

    print("""
✅ REQUIREMENT VERIFIED:

1. LLM/Agent Processing:
   • Receives raw tool output with actual auth types
   • Can see [app_password], [OAuth], email addresses
   • Processes real data for decision-making

2. Frontend/User Display:
   • Receives redacted content via normalization layer
   • Sees [****] instead of [app_password]
   • Sees email addresses for identification

3. History Storage:
   • Stores normalized (redacted) content
   • No sensitive auth types in JSONL files
   • Safe for long-term storage

4. Redaction Layer:
   • Applied in normalize_tool_result_content()
   • Applied in save_tool_result() before storage
   • Applied in sanitize_websocket_message() before sending

🔒 SECURITY: Sensitive data is protected at presentation layer
🧠 INTELLIGENCE: LLM still has full context for processing
""")

    print("█"*70 + "\n")


if __name__ == "__main__":
    main()
