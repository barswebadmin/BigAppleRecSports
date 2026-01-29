"""Terminal control utilities for cursor positioning and output management."""

import signal
import sys

import click_extra as click


def clear_lines(count: int) -> None:
    """Clear the specified number of lines above the cursor.
    
    Uses ANSI escape sequences to move cursor up and clear lines.
    
    Args:
        count: Number of lines to clear
    """
    if count <= 0:
        return
    
    # Move cursor up and clear each line
    for _ in range(count):
        sys.stdout.write("\033[A\033[2K")
    sys.stdout.flush()


def flush_output() -> None:
    """Flush stdout buffer to ensure output is displayed immediately."""
    sys.stdout.flush()


def save_cursor_position() -> None:
    """Save the current cursor position.
    
    Uses ANSI escape sequence to save cursor position for later restoration.
    """
    sys.stdout.write("\033[s")
    sys.stdout.flush()


def restore_cursor_position() -> None:
    """Restore the previously saved cursor position.
    
    Uses ANSI escape sequence to restore cursor position saved with save_cursor_position().
    """
    sys.stdout.write("\033[u")
    sys.stdout.flush()


def clear_to_end_of_line() -> None:
    """Clear from the current cursor position to the end of the line.
    
    Uses ANSI escape sequence to clear to end of line.
    """
    sys.stdout.write("\033[K")
    sys.stdout.flush()


def move_cursor_up(lines: int) -> None:
    """Move cursor up by the specified number of lines.
    
    Args:
        lines: Number of lines to move up
    """
    if lines <= 0:
        return
    
    sys.stdout.write(f"\033[{lines}A")
    sys.stdout.flush()


def move_cursor_down(lines: int) -> None:
    """Move cursor down by the specified number of lines.
    
    Args:
        lines: Number of lines to move down
    """
    if lines <= 0:
        return
    
    sys.stdout.write(f"\033[{lines}B")
    sys.stdout.flush()


# Current keyboard interrupt mode
_KEYBOARD_INTERRUPT_MODE: str = 'exit'


def set_keyboard_interrupt_handler(mode: str = 'exit') -> None:
    """Set up keyboard interrupt handler for the CLI.
    
    The handler catches SIGINT (Ctrl+C) and exits gracefully with a message,
    or raises KeyboardInterrupt based on the mode setting.
    
    Args:
        mode: Handling mode - 'exit' (default) or 'raise' (case-insensitive).
              'exit': Display message and exit gracefully (default behavior).
              'raise': Raise KeyboardInterrupt normally for custom handling.
              Invalid modes default to 'exit'.
    """
    global _KEYBOARD_INTERRUPT_MODE
    
    # Normalize mode to lowercase and validate
    mode_lower = mode.lower() if mode else 'exit'
    if mode_lower not in ('exit', 'raise'):
        mode_lower = 'exit'
    
    _KEYBOARD_INTERRUPT_MODE = mode_lower
    
    def _keyboard_interrupt_handler(signum, frame) -> None:
        """Signal handler for SIGINT (Ctrl+C)."""
        if _KEYBOARD_INTERRUPT_MODE.lower() == 'raise':
            # Allow KeyboardInterrupt to propagate normally
            raise KeyboardInterrupt()
        else:
            # Default: exit with message
            click.echo("\n")
            click.secho("🙅 Keyboard interrupt detected. Exiting command", fg="bright_yellow")
            click.echo()
            sys.exit(0)
    
    signal.signal(signal.SIGINT, _keyboard_interrupt_handler)

