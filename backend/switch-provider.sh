#!/bin/bash
# Quick provider switcher for Claude Agent SDK Docker

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if provider is specified
if [ -z "$1" ]; then
    echo -e "${RED}Error: No provider specified${NC}"
    echo ""
    echo "Usage: ./switch-provider.sh <provider>"
    echo ""
    echo "Available providers:"
    echo "  - claude (Official Anthropic)"
    echo "  - zai"
    echo "  - minimax"
    echo ""
    echo "Example:"
    echo "  ./switch-provider.sh zai"
    exit 1
fi

PROVIDER=$1

# Validate provider
if [[ ! "$PROVIDER" =~ ^(claude|zai|minimax)$ ]]; then
    echo -e "${RED}Error: Invalid provider '$PROVIDER'${NC}"
    echo "Valid providers: claude, zai, minimax"
    exit 1
fi

echo -e "${YELLOW}Switching to provider: $PROVIDER${NC}"
echo ""

# Update config.yaml
sed -i "s/^provider: .*/provider: $PROVIDER/" config.yaml

# Verify the change
NEW_PROVIDER=$(grep "^provider:" config.yaml | awk '{print $2}')

if [ "$NEW_PROVIDER" = "$PROVIDER" ]; then
    echo -e "${GREEN}✓ Provider switched to: $NEW_PROVIDER${NC}"
    echo ""
    echo "Restarting Docker container..."
    docker compose restart claude-api
    echo ""
    echo -e "${GREEN}✓ Done! Provider switched successfully${NC}"
    echo ""
    echo "Check logs: docker compose logs -f claude-api"
else
    echo -e "${RED}✗ Failed to switch provider${NC}"
    exit 1
fi
