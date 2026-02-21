#!/usr/bin/env python3
"""Test IMAP connection for Gmail accounts."""
import imaplib
import json
import sys

# Load credentials for both Gmail accounts
accounts = [
    {
        "email": "user@gmail.com",
        "password": "kdocwebvmnrtwqga",
        "server": "imap.gmail.com",
        "port": 993
    },
    {
        "email": "user2@gmail.com",
        "password": "seqizahivbcdddig",
        "server": "imap.gmail.com",
        "port": 993
    }
]

def test_imap_connection(account):
    """Test IMAP connection for a single account."""
    print(f"\n{'='*60}")
    print(f"Testing: {account['email']}")
    print(f"{'='*60}")

    try:
        # Connect to IMAP server
        print(f"Connecting to {account['server']}:{account['port']}...")
        client = imaplib.IMAP4_SSL(account['server'], account['port'])
        print("✓ Connected successfully")

        # Login
        print(f"Authenticating as {account['email']}...")
        try:
            client.login(account['email'], account['password'])
            print("✓ Authentication successful")

            # Select INBOX
            print("Selecting INBOX...")
            client.select('INBOX')
            print("✓ INBOX selected")

            # List messages
            print("Searching for messages...")
            status, messages = client.search(None, 'ALL')
            if status == 'OK':
                msg_count = len(messages[0].split())
                print(f"✓ Found {msg_count} messages in INBOX")
            else:
                print(f"✗ Search failed: {status}")

            client.logout()
            print("✓ Logged out successfully")
            return True

        except imaplib.IMAP4.error as e:
            print(f"✗ Authentication FAILED: {e}")
            print("\nPossible issues:")
            print("1. App password is incorrect")
            print("2. 2-Step Verification is not enabled")
            print("3. App password was not generated correctly")
            print("4. 'Less secure app access' is disabled (for older Gmail accounts)")
            return False

    except Exception as e:
        print(f"✗ Connection FAILED: {e}")
        return False

if __name__ == "__main__":
    print("Testing IMAP connections for Gmail accounts...")
    print("Note: These tests use app passwords from your credential store")

    results = []
    for account in accounts:
        success = test_imap_connection(account)
        results.append((account['email'], success))

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for email, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {email}")

    # Exit with error code if any failed
    if not all(success for _, success in results):
        sys.exit(1)
    else:
        print("\n✓ All accounts connected successfully!")
        sys.exit(0)
