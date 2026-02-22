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
# Install deps for both chromium and chrome — the Playwright MCP plugin defaults to chrome.
RUN npx playwright install-deps chromium chrome 2>/dev/null || true

# Pre-install the Playwright MCP package globally so npx doesn't download it every time
RUN npm install -g @playwright/mcp@latest

# Install Chrome browser as root (installs to /opt/google/chrome/ which requires root).
# Chrome is only available on x86_64; skip on ARM64 (Playwright MCP falls back to chromium).
RUN if [ "$(uname -m)" = "x86_64" ]; then npx playwright install chrome; fi

# Install uv for fast Python package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Create non-root user for security (per official Anthropic guidelines)
RUN useradd -m -u 1000 -s /bin/bash appuser

# ----- Dependency layer (cached unless pyproject.toml changes) -----
COPY pyproject.toml ./

# Install Python dependencies using uv (from pyproject.toml)
RUN uv pip install --system --no-cache ".[email,platforms]"

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

# Copy pre-cached Playwright browsers from build context (avoids slow CDN download).
# To populate: cp -r ~/.cache/ms-playwright/.    backend/.playwright-cache/
# Falls back to npx download if cache dir is missing.
COPY --chown=appuser:appuser .playwright-cache/ /home/appuser/.cache/ms-playwright/

# Install official Anthropic plugins.
RUN claude plugin marketplace add anthropics/claude-plugins-official && \
    claude plugin install playwright@claude-plugins-official --scope project && \
    claude plugin install context7@claude-plugins-official --scope project && \
    claude plugin install github@claude-plugins-official --scope project

# On ARM64, Chrome is not available at /opt/google/chrome/chrome.
# Patch the Playwright MCP plugin to use --browser chromium instead.
RUN if [ "$(uname -m)" != "x86_64" ]; then \
      MCP_JSON=$(find /home/appuser/.claude/plugins/cache/claude-plugins-official/playwright -name '.mcp.json' 2>/dev/null | head -1); \
      if [ -n "$MCP_JSON" ]; then \
        sed -i 's|"@playwright/mcp@latest"|"@playwright/mcp@latest", "--browser", "chromium"|' "$MCP_JSON"; \
        echo "Patched $MCP_JSON for ARM64 chromium fallback"; \
      fi; \
    fi

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
