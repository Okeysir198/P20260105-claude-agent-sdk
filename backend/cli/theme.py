"""CLI theme configuration for display styling."""
from dataclasses import dataclass, field

from rich import box


@dataclass
class PanelTheme:
    """Theme settings for Rich panels."""

    width: int = 80
    box_style: box.Box = field(default_factory=lambda: box.ROUNDED)


@dataclass
class ColorTheme:
    """Color definitions for CLI display elements."""

    user: str = "cyan"
    assistant: str = "green"
    assistant_streaming: str = "green"
    tool_use: str = "yellow"
    tool_result: str = "blue"
    question: str = "magenta"

    success: str = "green"
    warning: str = "yellow"
    error: str = "red"
    info: str = "dim"

    prompt: str = "cyan"
    selection: str = "cyan"
    header: str = "cyan"
    confirm: str = "green"


@dataclass
class CLITheme:
    """Complete CLI theme configuration."""

    panel: PanelTheme = field(default_factory=PanelTheme)
    colors: ColorTheme = field(default_factory=ColorTheme)
    max_tool_result_length: int = 1000


default_theme = CLITheme()


def format_panel_title(text: str, color: str, bold: bool = True) -> str:
    """Format a panel title with Rich markup styling."""
    style = f"{color} bold" if bold else color
    return f"[{style}]{text}[/{style}]"


def format_styled(text: str, color: str, bold: bool = False, dim: bool = False) -> str:
    """Format text with Rich markup styling."""
    modifiers = []
    if bold:
        modifiers.append("bold")
    if dim:
        modifiers.append("dim")
    modifiers.append(color)
    style = " ".join(modifiers)
    return f"[{style}]{text}[/{style}]"


def get_theme() -> CLITheme:
    """Get the current theme instance."""
    return default_theme


def set_theme(theme: CLITheme) -> None:
    """Set a custom theme globally."""
    global default_theme
    default_theme = theme
