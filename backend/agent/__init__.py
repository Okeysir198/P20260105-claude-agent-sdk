"""Claude Agent SDK - Main source package.

This package contains the core business logic, discovery services,
and display utilities for the Claude Agent SDK CLI application.
"""
from pathlib import Path

# Project root directory (where .claude/skills/, config.yaml, etc. are located)
PROJECT_ROOT = Path(__file__).parent.parent

__all__ = ['PROJECT_ROOT']
