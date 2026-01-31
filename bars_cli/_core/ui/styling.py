"""
Styling utilities for BARS CLI.

Provides console themes and styling functions.
"""

from rich.console import Console
from rich.theme import Theme

# Console themes
FORMATTED_THEME = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "red",
    "success": "green",
    "highlight": "blue",
})

SIMPLE_THEME = Theme({
    "info": "white",
    "warning": "white",
    "error": "white",
    "success": "white",
    "highlight": "white",
})

JSON_THEME = Theme({
    "json.key": "blue",
    "json.string": "green",
    "json.number": "cyan",
    "json.bool_true": "green",
    "json.bool_false": "red",
    "json.null": "magenta",
})

# Global console instance
_console = None

def get_console() -> Console:
    """Get the global console instance."""
    global _console
    if _console is None:
        _console = Console(theme=FORMATTED_THEME)
    return _console