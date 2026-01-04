"""Styling utilities for consistent CLI output."""

import click


# Color constants
SUCCESS_GREEN = "green"
ERROR_RED = "red"
WARNING_YELLOW = "yellow"
INFO_CYAN = "cyan"
PROMPT_YELLOW = "bright_yellow"
COMMAND_CYAN = "cyan"


def success(text: str) -> str:
    """Style text as success (green)."""
    return click.style(text, fg=SUCCESS_GREEN)


def error(text: str) -> str:
    """Style text as error (red)."""
    return click.style(text, fg=ERROR_RED)


def warning(text: str) -> str:
    """Style text as warning (yellow)."""
    return click.style(text, fg=WARNING_YELLOW)


def info(text: str) -> str:
    """Style text as info (cyan)."""
    return click.style(text, fg=INFO_CYAN)


def prompt(text: str) -> str:
    """Style text as a prompt (bright yellow)."""
    return click.style(text, fg=PROMPT_YELLOW)


def style_command(text: str) -> str:
    """Style text as a command name (cyan)."""
    return click.style(text, fg=COMMAND_CYAN)


def bold(text: str) -> str:
    """Make text bold."""
    return click.style(text, bold=True)


def dim(text: str) -> str:
    """Make text dim."""
    return click.style(text, dim=True)

