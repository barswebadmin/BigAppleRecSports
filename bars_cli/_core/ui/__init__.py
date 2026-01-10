"""UI utilities for BARS CLI."""

from .styling import success, error, warning, info, style_command
from .display import display_table, display_json
from .terminal import (
    clear_lines,
    flush_output,
    save_cursor_position,
    restore_cursor_position,
    clear_to_end_of_line,
    move_cursor_up,
    move_cursor_down,
    set_keyboard_interrupt_handler,
)

__all__ = [
    "success",
    "error",
    "warning",
    "info",
    "style_command",
    "display_table",
    "display_json",
    "clear_lines",
    "flush_output",
    "save_cursor_position",
    "restore_cursor_position",
    "clear_to_end_of_line",
    "move_cursor_up",
    "move_cursor_down",
    "set_keyboard_interrupt_handler",
]

