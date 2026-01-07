"""
Prompts package for debt collection multi-agent system.

Uses chevron for Mustache template rendering.
"""

import logging
import yaml
from pathlib import Path

import chevron

logger = logging.getLogger(__name__)


def load_prompt(prompt_name: str) -> dict:
    """
    Load prompt YAML file.

    Args:
        prompt_name: Prompt file name (e.g., 'prompt01_introduction')

    Returns:
        Dictionary with prompt metadata and content

    Raises:
        FileNotFoundError: If prompt file doesn't exist
        ValueError: If YAML is invalid
    """
    prompts_dir = Path(__file__).parent
    prompt_file = prompts_dir / f"{prompt_name}.yaml"

    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

    try:
        with open(prompt_file, 'r') as f:
            data = yaml.safe_load(f)
            logger.debug(f"Loaded prompt: {prompt_name}")
            return data
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in {prompt_file}: {e}")


def format_prompt(template: str, **variables) -> str:
    """
    Format prompt template using Mustache syntax.

    Args:
        template: Template string with {{variable}} placeholders
        **variables: Variables to substitute in template

    Returns:
        Formatted prompt string

    Example:
        format_prompt("Hello {{name}}", name="John") -> "Hello John"
    """
    try:
        result = chevron.render(template, **variables)
        return result
    except Exception as e:
        logger.error(f"Template formatting error: {e}")
        return template


def format_instruction(template: str, **variables) -> str:
    """Alias for format_prompt for backward compatibility."""
    return format_prompt(template, **variables)


__all__ = [
    "load_prompt",
    "format_prompt",
    "format_instruction",
]
