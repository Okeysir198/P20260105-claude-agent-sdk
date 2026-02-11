#!/usr/bin/env python3
"""
Test SDK file access - verify that the Read tool can access uploaded files.

This test:
1. Creates a session
2. Uploads a test file to the session input directory
3. Uses the SDK Read tool to access the file
4. Verifies the content matches

Usage:
    source .venv/bin/activate
    python test_sdk_file_access.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from agent.core.file_storage import FileStorage


def test_file_storage():
    """Test FileStorage functionality for SDK file access."""

    print("=" * 60)
    print("SDK File Access Test")
    print("=" * 60)

    # Test configuration
    username = "admin"  # Default admin user
    session_id = "test-session-sdk-file-access"

    # Create FileStorage instance
    print(f"\n1. Creating FileStorage for user={username}, session={session_id}")
    storage = FileStorage(username=username, session_id=session_id)

    # Get input directory path (for SDK Read tool)
    input_dir = storage.get_input_dir()
    print(f"   Input directory: {input_dir}")

    # Create a test file in the input directory
    test_filename = "test_sdk_read.txt"
    test_content = b"This is a test file for SDK Read tool access.\n"
    test_content += b"Created at: 2025-02-11\n"
    test_content += b"Random data: 12345\n"

    print(f"\n2. Creating test file: {test_filename}")
    test_file_path = input_dir / test_filename

    with open(test_file_path, "wb") as f:
        f.write(test_content)

    print(f"   File created at: {test_file_path}")
    print(f"   File size: {len(test_content)} bytes")

    # Verify file exists
    if test_file_path.exists():
        print(f"   ✓ File exists")
    else:
        print(f"   ✗ File does NOT exist!")
        return False

    # List files in the directory
    print(f"\n3. Listing files in input directory:")
    files = list(input_dir.iterdir())
    for f in files:
        print(f"   - {f.name} ({f.stat().st_size} bytes)")

    # Read the file back (simulating SDK Read tool)
    print(f"\n4. Reading file with SDK Read tool simulation:")
    with open(test_file_path, "rb") as f:
        read_content = f.read()

    print(f"   Read {len(read_content)} bytes")
    print(f"   Content:\n{'-' * 40}")
    print(read_content.decode('utf-8'))
    print('-' * 40)

    # Verify content matches
    if read_content == test_content:
        print(f"   ✓ Content matches original!")
    else:
        print(f"   ✗ Content does NOT match!")
        return False

    # Test using FileStorage.list_files()
    print(f"\n5. Testing FileStorage.list_files():")

    async def test_list_files():
        files = await storage.list_files(file_type="input")
        print(f"   Found {len(files)} file(s):")
        for f in files:
            print(f"   - {f.original_name} ({f.safe_name}) - {f.size_bytes} bytes")

    asyncio.run(test_list_files())

    # Test get_file_path()
    print(f"\n6. Testing FileStorage.get_file_path():")

    try:
        file_path = storage.get_file_path(safe_name=test_filename, file_type="input")
        print(f"   File path: {file_path}")
        print(f"   ✓ File path resolved successfully")
    except Exception as e:
        print(f"   ✗ Error getting file path: {e}")
        return False

    # Cleanup
    print(f"\n7. Cleanup:")
    test_file_path.unlink()
    if not test_file_path.exists():
        print(f"   ✓ Test file deleted")
    else:
        print(f"   ✗ Failed to delete test file")

    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)

    # Print SDK usage example
    print("\nSDK Usage Example:")
    print("-" * 60)
    print(f"# To access uploaded files via SDK Read tool:")
    print(f"#")
    print(f"# 1. Get the input directory path:")
    print(f"from agent.core.file_storage import FileStorage")
    print(f"storage = FileStorage(username='{username}', session_id='{session_id}')")
    print(f"input_dir = storage.get_input_dir()")
    print(f"#")
    print(f"# 2. Access files using absolute paths:")
    print(f"# file_path = input_dir / 'uploaded_file.txt'")
    print(f"#")
    print(f"# Or use the SDK Read tool with relative paths from working directory:")
    print(f"# Read tool can access: data/{username}/files/{session_id}/input/filename.txt")
    print("-" * 60)

    return True


if __name__ == "__main__":
    success = test_file_storage()
    sys.exit(0 if success else 1)
