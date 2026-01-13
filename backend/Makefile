.PHONY: help build build-api build-interactive up up-api down logs test clean

# Default target
help:
	@echo "Claude Agent SDK CLI - Docker Management"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  build            Build Docker image"
	@echo "  build-api        Build and start API server"
	@echo "  up               Start API server (alias for build-api)"
	@echo "  up-interactive   Start interactive chat session"
	@echo "  down             Stop all containers"
	@echo "  logs             Show API server logs"
	@echo "  test             Run basic tests"
	@echo "  clean            Remove containers and images"
	@echo "  rebuild          Rebuild from scratch (no cache)"
	@echo ""
	@echo "Interactive Commands:"
	@echo "  make skills       List available skills"
	@echo "  make agents       List available subagents"
	@echo "  make sessions     List conversation sessions"
	@echo ""
	@echo "Examples:"
	@echo "  make build && make up-api          # Build and start API server"
	@echo "  make up-interactive                # Start interactive chat"
	@echo "  make exec-cmd skills               # Run 'skills' command in container"

# Build Docker image
build:
	docker compose build

# Build and start API server
build-api: build
	docker compose up -d claude-api
	@echo "API Server starting on http://localhost:19830"
	@echo "Check logs with: make logs"
	@sleep 3
	docker compose logs --tail=20 claude-api

# Start API server
up: build-api

# Start interactive session
up-interactive:
	@echo "Starting interactive Claude Agent SDK CLI..."
	docker compose run --rm claude-interactive

# Stop all containers
down:
	docker compose down

# Show logs
logs:
	docker compose logs -f claude-api

# Run skills command
skills:
	docker compose run --rm claude-interactive python main.py skills

# Run agents command
agents:
	docker compose run --rm claude-interactive python main.py agents

# Run sessions command
sessions:
	docker compose run --rm claude-interactive python main.py sessions

# Execute arbitrary command
exec-cmd:
	@read -p "Enter command: " cmd; \
	docker compose run --rm claude-interactive $$cmd

# Test container
test:
	@echo "Testing container build..."
	docker compose run --rm claude-interactive python -c "import claude_agent_sdk; print('✓ claude-agent-sdk installed')"
	docker compose run --rm claude-interactive python -c "import yaml; print('✓ yaml installed')"
	docker compose run --rm claude-interactive python -c "from dotenv import load_dotenv; print('✓ python-dotenv installed')"
	docker compose run --rm claude-interactive python main.py --help
	@echo "✓ All tests passed!"

# Clean up
clean:
	docker compose down -v
	docker system prune -f
	@echo "✓ Cleaned up containers and volumes"

# Rebuild from scratch
rebuild:
	docker compose build --no-cache
	@echo "✓ Rebuilt from scratch"

# Shell access
shell:
	docker compose run --rm claude-interactive /bin/bash
