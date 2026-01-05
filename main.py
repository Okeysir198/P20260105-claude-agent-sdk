#!/usr/bin/env python
"""Unified entry point for Claude Agent SDK CLI.

This script provides a command-line interface to interact with Claude Agent SDK.
It supports two modes:
  - direct: Use Python SDK directly (default)
  - api: Connect to HTTP/SSE API server

Usage:
  python main.py                    # Start interactive chat (direct mode)
  python main.py --mode api         # Start chat via API server
  python main.py serve              # Start API server
  python main.py skills             # List available skills
  python main.py agents             # List available subagents
  python main.py sessions           # List conversation sessions
  python main.py --help             # Show help
"""

from cli.main import cli

if __name__ == "__main__":
    cli()
