#!/usr/bin/env python
"""Unified entry point for Claude Agent SDK CLI.

This script provides a command-line interface to manage the API server,
interact with the API, and list available resources.

Usage:
  python main.py api                # Start interactive chat via API
  python main.py serve              # Start API server
  python main.py skills             # List available skills
  python main.py agents             # List available agents
  python main.py subagents          # List available subagents
  python main.py sessions           # List conversation sessions
  python main.py --help             # Show help
"""
from cli.main import cli

if __name__ == "__main__":
    cli()
