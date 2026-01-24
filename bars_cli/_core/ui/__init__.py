"""UI utilities for BARS CLI."""

from .styling import (
    get_console,
    FORMATTED_THEME,
    SIMPLE_THEME,
    JSON_THEME,
)
from .display import (
    display_table,
    display_json,
    format_datetime,
    create_info_table,
    create_panel,
    create_text_panel,
    display_json_syntax,
)
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
    "get_console",
    "FORMATTED_THEME",
    "SIMPLE_THEME",
    "JSON_THEME",
    "display_table",
    "display_json",
    "format_datetime",
    "create_info_table",
    "create_panel",
    "create_text_panel",
    "display_json_syntax",
    "clear_lines",
    "flush_output",
    "save_cursor_position",
    "restore_cursor_position",
    "clear_to_end_of_line",
    "move_cursor_up",
    "move_cursor_down",
    "set_keyboard_interrupt_handler",
]

