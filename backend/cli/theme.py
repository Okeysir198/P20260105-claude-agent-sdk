"""CLI theme configuration for customizable display styling.

Contains color and style definitions that can be customized for branding.
"""
from dataclasses import dataclass, field
from typing import Optional

from rich import box


@dataclass
class PanelTheme:
    """Theme settings for Rich panels."""

    width: int = 80
    box_style: box.Box = field(default_factory=lambda: box.ROUNDED)


@dataclass
class ColorTheme:
    """Color definitions for CLI display elements."""

    # Message panel colors
    user: str = "cyan"
    assistant: str = "green"
    assistant_streaming: str = "green"
    tool_use: str = "yellow"
    tool_result: str = "blue"
    question: str = "magenta"

    # Status message colors
    success: str = "green"
    warning: str = "yellow"
    error: str = "red"
    info: str = "dim"

    # Interactive elements
    prompt: str = "cyan"
    selection: str = "cyan"
    header: str = "cyan"
    confirm: str = "green"


@dataclass
class CLITheme:
    """Complete CLI theme configuration."""

    panel: PanelTheme = field(default_factory=PanelTheme)
    colors: ColorTheme = field(default_factory=ColorTheme)

    # Content truncation settings
    max_tool_result_length: int = 1000


# Default theme instance
default_theme = CLITheme()


def format_panel_title(text: str, color: str, bold: bool = True) -> str:
    """Format a panel title with consistent styling.

    Args:
        text: Title text.
        color: Color name for the title.
        bold: Whether to apply bold styling.

    Returns:
        Rich markup formatted title string.
    """
    style = f"{color} bold" if bold else color
    return f"[{style}]{text}[/{style}]"


def format_styled(text: str, color: str, bold: bool = False, dim: bool = False) -> str:
    """Format text with Rich markup styling.

    Args:
        text: Text to format.
        color: Color name for the text.
        bold: Whether to apply bold styling.
        dim: Whether to apply dim styling.

    Returns:
        Rich markup formatted string.
    """
    modifiers = []
    if bold:
        modifiers.append("bold")
    if dim:
        modifiers.append("dim")
    modifiers.append(color)
    style = " ".join(modifiers)
    return f"[{style}]{text}[/{style}]"


def get_theme() -> CLITheme:
    """Get the current theme instance.

    Returns:
        The active CLITheme configuration.
    """
    return default_theme


def set_theme(theme: CLITheme) -> None:
    """Set a custom theme globally.

    Args:
        theme: CLITheme instance to use.
    """
    global default_theme
    default_theme = theme
