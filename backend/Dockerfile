# Dockerfile for Trung-bot
# Based on official Anthropic guidelines for deploying Claude Agent SDK
#
# Optimized for fast rebuilds: dependency layers are cached separately
# from application code. Only pyproject.toml changes trigger full rebuild.

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
    gosu \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js (required by Claude Code CLI and Playwright MCP)
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright system dependencies (as root, before switching to appuser).
RUN npx playwright install-deps chromium 2>/dev/null || true

# Pre-install the Playwright MCP package globally so npx doesn't download it every time
RUN npm install -g @playwright/mcp@latest

# Install uv for fast Python package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Create non-root user for security (per official Anthropic guidelines)
RUN useradd -m -u 1000 -s /bin/bash appuser

# ----- Dependency layer (cached unless pyproject.toml changes) -----
COPY pyproject.toml ./

# Install Python dependencies using uv (from pyproject.toml)
RUN uv pip install --system --no-cache .

# Create necessary directories and set ownership for appuser
RUN mkdir -p /app/data /app/.claude && \
    chown -R appuser:appuser /app

# Switch to non-root user for remaining setup
USER appuser

# Install Claude Code CLI via native installer (installs to ~/.claude/local/)
RUN curl -fsSL https://claude.ai/install.sh | bash

# Set environment variables (before plugin install so claude is in PATH)
ENV PYTHONUNBUFFERED=1
ENV PATH="/home/appuser/.claude/local/bin:/home/appuser/.local/bin:${PATH}"
ENV PYTHONPATH="/app:${PYTHONPATH}"

# Install Chromium browser for Playwright (as non-root user).
RUN npx playwright install chromium

# Install official Anthropic plugins.
RUN claude plugin marketplace add anthropics/claude-plugins-official && \
    claude plugin install playwright@claude-plugins-official --scope project && \
    claude plugin install context7@claude-plugins-official --scope project && \
    claude plugin install github@claude-plugins-official --scope project

# ----- Application code layer (rebuilt on every code change, ~instant) -----
# Switch back to root to copy files with correct ownership
USER root
COPY --chown=appuser:appuser . .
USER appuser

# Expose API server port
EXPOSE 7003

# Health check (port must match docker-compose command --port)
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:7003/health || exit 1

# Default command - can be overridden
CMD ["python", "main.py"]
