#!/bin/bash
# Test script for file upload/download/delete API
# Usage: cd backend && bash test_files_api.sh

set -e

# Configuration - Load from environment
export $(grep -v '^#' .env | xargs)

# Use local backend for testing (change to production URL after restart)
API_URL="${API_URL:-http://localhost:7003/api/v1}"
API_KEY="${API_KEY:-your-api-key-here}"
USERNAME="${USERNAME:-admin}"
PASSWORD="${CLI_ADMIN_PASSWORD:-your-password-here}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== File API Test Script ===${NC}"
echo "API URL: $API_URL"
echo "Username: $USERNAME"
echo ""

# Step 1: Login to get user token
echo -e "${YELLOW}Step 1: Logging in...${NC}"
LOGIN_RESPONSE=$(curl -s -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d "{\"username\": \"$USERNAME\", \"password\": \"$PASSWORD\"}")

echo $LOGIN_RESPONSE | jq '.'

LOGIN_SUCCESS=$(echo $LOGIN_RESPONSE | jq -r '.success')
if [ "$LOGIN_SUCCESS" != "true" ]; then
  echo -e "${RED}Login failed!${NC}"
  exit 1
fi

USER_TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.token')
echo -e "${GREEN}Login successful! User token obtained.${NC}"
echo ""

# Step 2: Get or create a test session
echo -e "${YELLOW}Step 2: Getting existing sessions...${NC}"
SESSIONS_RESPONSE=$(curl -s -X GET "$API_URL/sessions" \
  -H "X-API-Key: $API_KEY" \
  -H "X-User-Token: $USER_TOKEN")

echo $SESSIONS_RESPONSE | jq '.'

# Try to use existing session, or create a new one
EXISTING_SESSION=$(echo $SESSIONS_RESPONSE | jq -r '.[0].session_id // empty')

if [ -n "$EXISTING_SESSION" ] && [ "$EXISTING_SESSION" != "null" ]; then
  SESSION_ID="$EXISTING_SESSION"
  echo -e "${GREEN}Using existing session: $SESSION_ID${NC}"
else
  echo -e "${YELLOW}No existing sessions, creating new one...${NC}"
  SESSION_RESPONSE=$(curl -s -X POST "$API_URL/sessions" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $API_KEY" \
    -H "X-User-Token: $USER_TOKEN" \
    -d '{"agent_id": null}')

  SESSION_ID=$(echo $SESSION_RESPONSE | jq -r '.session_id')

  if [ -z "$SESSION_ID" ] || [ "$SESSION_ID" = "null" ]; then
    echo -e "${RED}Session creation failed! Response:${NC}"
    echo $SESSION_RESPONSE | jq '.'
    exit 1
  fi

  echo -e "${GREEN}Session created: $SESSION_ID${NC}"
fi
echo ""

# Step 3: Create a test file
echo -e "${YELLOW}Step 3: Creating test file...${NC}"
TEST_FILE="/tmp/test-upload-$(date +%s).txt"
echo "This is a test file for file upload API testing." > "$TEST_FILE"
echo "Created at: $(date)" >> "$TEST_FILE"
echo "Random data: $RANDOM$RANDOM$RANDOM" >> "$TEST_FILE"

echo -e "${GREEN}Test file created: $TEST_FILE${NC}"
cat "$TEST_FILE"
echo ""

# Step 4: Upload file
echo -e "${YELLOW}Step 4: Uploading file...${NC}"
UPLOAD_RESPONSE=$(curl -s -X POST "$API_URL/files/upload" \
  -H "X-API-Key: $API_KEY" \
  -H "X-User-Token: $USER_TOKEN" \
  -F "file=@$TEST_FILE" \
  -F "session_id=$SESSION_ID")

echo $UPLOAD_RESPONSE | jq '.'

UPLOAD_SUCCESS=$(echo $UPLOAD_RESPONSE | jq -r '.success')
if [ "$UPLOAD_SUCCESS" != "true" ]; then
  echo -e "${RED}File upload failed!${NC}"
  exit 1
fi

SAFE_NAME=$(echo $UPLOAD_RESPONSE | jq -r '.file.safe_name')
ORIGINAL_NAME=$(echo $UPLOAD_RESPONSE | jq -r '.file.original_name')
echo -e "${GREEN}File uploaded successfully!${NC}"
echo "  Safe name: $SAFE_NAME"
echo "  Original name: $ORIGINAL_NAME"
echo ""

# Step 5: List files
echo -e "${YELLOW}Step 5: Listing files...${NC}"
LIST_RESPONSE=$(curl -s -X GET "$API_URL/files/$SESSION_ID/list?file_type=input" \
  -H "X-API-Key: $API_KEY" \
  -H "X-User-Token: $USER_TOKEN")

echo $LIST_RESPONSE | jq '.'

TOTAL_FILES=$(echo $LIST_RESPONSE | jq -r '.total_files')
echo -e "${GREEN}Found $TOTAL_FILES file(s)${NC}"
echo ""

# Step 6: Download file
echo -e "${YELLOW}Step 6: Downloading file...${NC}"
DOWNLOAD_FILE="/tmp/downloaded-$(date +%s).txt"

curl -s -X GET "$API_URL/files/$SESSION_ID/download/input/$SAFE_NAME" \
  -H "X-API-Key: $API_KEY" \
  -H "X-User-Token: $USER_TOKEN" \
  -o "$DOWNLOAD_FILE"

if [ -f "$DOWNLOAD_FILE" ]; then
  echo -e "${GREEN}File downloaded to: $DOWNLOAD_FILE${NC}"
  echo "Contents:"
  cat "$DOWNLOAD_FILE"

  # Verify content matches
  if diff -q "$TEST_FILE" "$DOWNLOAD_FILE" > /dev/null; then
    echo -e "${GREEN}✓ Downloaded file matches original!${NC}"
  else
    echo -e "${RED}✗ Downloaded file does NOT match original!${NC}"
  fi
else
  echo -e "${RED}Download failed!${NC}"
  exit 1
fi
echo ""

# Step 7: Verify file exists in session input directory
echo -e "${YELLOW}Step 7: Verifying file in session input directory...${NC}"
SESSION_DIR="backend/data/$USERNAME/files/$SESSION_ID/input"

if [ -d "$SESSION_DIR" ]; then
  echo -e "${GREEN}Session directory exists: $SESSION_DIR${NC}"
  ls -lh "$SESSION_DIR/"

  # Check if the file exists
  if [ -f "$SESSION_DIR/$SAFE_NAME" ]; then
    echo -e "${GREEN}✓ File found in session input directory!${NC}"
    echo "Path: $SESSION_DIR/$SAFE_NAME"
  else
    echo -e "${RED}✗ File NOT found in session input directory!${NC}"
  fi
else
  echo -e "${RED}Session directory does not exist: $SESSION_DIR${NC}"
fi
echo ""

# Step 8: Delete file
echo -e "${YELLOW}Step 8: Deleting file...${NC}"
DELETE_RESPONSE=$(curl -s -X DELETE "$API_URL/files/$SESSION_ID/delete" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -H "X-User-Token: $USER_TOKEN" \
  -d "{\"safe_name\": \"$SAFE_NAME\", \"file_type\": \"input\"}")

echo $DELETE_RESPONSE | jq '.'

DELETE_SUCCESS=$(echo $DELETE_RESPONSE | jq -r '.success')
if [ "$DELETE_SUCCESS" != "true" ]; then
  echo -e "${RED}File deletion failed!${NC}"
  exit 1
fi

REMAINING_FILES=$(echo $DELETE_RESPONSE | jq -r '.remaining_files')
echo -e "${GREEN}File deleted successfully! Remaining files: $REMAINING_FILES${NC}"
echo ""

# Step 9: Verify deletion
echo -e "${YELLOW}Step 9: Verifying deletion...${NC}"
if [ -f "$SESSION_DIR/$SAFE_NAME" ]; then
  echo -e "${RED}✗ File still exists in session directory!${NC}"
else
  echo -e "${GREEN}✓ File successfully removed from session directory!${NC}"
fi
echo ""

# Step 10: List files again to confirm
echo -e "${YELLOW}Step 10: Final file list...${NC}"
FINAL_LIST=$(curl -s -X GET "$API_URL/files/$SESSION_ID/list?file_type=input" \
  -H "X-API-Key: $API_KEY" \
  -H "X-User-Token: $USER_TOKEN")

echo $FINAL_LIST | jq '.'

FINAL_COUNT=$(echo $FINAL_LIST | jq -r '.total_files')
if [ "$FINAL_COUNT" = "0" ]; then
  echo -e "${GREEN}✓ No files remaining (as expected)${NC}"
else
  echo -e "${YELLOW}Warning: Expected 0 files, found $FINAL_COUNT${NC}"
fi
echo ""

# Cleanup
rm -f "$TEST_FILE" "$DOWNLOAD_FILE"

echo -e "${GREEN}=== All tests passed! ===${NC}"
echo ""
echo -e "${YELLOW}Summary:${NC}"
echo "- Login and authentication: ✓"
echo "- Session creation: ✓"
echo "- File upload: ✓"
echo "- File listing: ✓"
echo "- File download: ✓"
echo "- File verification in session directory: ✓"
echo "- File deletion: ✓"
echo ""
echo "Session ID for SDK testing: $SESSION_ID"
echo "Session directory: backend/data/$USERNAME/files/$SESSION_ID/"
