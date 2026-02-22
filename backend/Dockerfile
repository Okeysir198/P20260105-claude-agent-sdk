# Dockerfile for Trung-bot
# Based on official Anthropic guidelines for deploying Claude Agent SDK

FROM python:3.12-slim

# Metadata
LABEL maintainer="nthanhtrung"
LABEL description="Trung-bot - Interactive chat application with Skills and Subagents"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js (required by Claude Code CLI per official docs)
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI (official requirement for Agent SDK)
RUN npm install -g @anthropic-ai/claude-code

# Install Playwright system dependencies (as root, before switching to appuser).
# These are the Chromium browser dependencies needed for headless browser automation.
# Uses npx to install the package temporarily and run the install-deps command.
RUN npx playwright install-deps chromium 2>/dev/null || true

# Pre-install the Playwright MCP package globally so npx doesn't download it every time
RUN npm install -g @playwright/mcp@latest

# Install uv for fast Python package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Create non-root user for security (per official Anthropic guidelines)
RUN useradd -m -u 1000 -s /bin/bash appuser

# Copy application code
COPY . .

# Install Python dependencies using uv (from pyproject.toml)
RUN uv pip install --system --no-cache .

# Create necessary directories and set permissions
RUN mkdir -p /app/data /app/.claude && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Install Chromium browser for Playwright (as non-root user).
# System deps were already installed as root above.
RUN npx playwright install chromium

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PATH="/home/appuser/.local/bin:${PATH}"
ENV PYTHONPATH="/app:${PYTHONPATH}"

# Expose API server port
EXPOSE 7003

# Health check (port must match docker-compose command --port)
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:7003/health || exit 1

# Default command - can be overridden
# Usage: docker run <image>                    # Interactive chat
#        docker run <image> serve              # Start API server
#        docker run <image> skills             # List skills
CMD ["python", "main.py"]
