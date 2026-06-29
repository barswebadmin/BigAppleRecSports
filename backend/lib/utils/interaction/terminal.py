"""Rich consoles, terminal detection, and clipboard utilities."""

import sys

import pyperclip
from decorator import decorator
from rich.console import Console


# ── Singletons ────────────────────────────────────────────────────────────

console = Console()
error_console = Console(stderr=True)


# ── Clipboard ─────────────────────────────────────────────────────────────


def copy_to_clipboard(value: str) -> bool:
    """Copy *value* to the system clipboard via ``pyperclip``.

    Returns ``True`` on success, ``False`` if no clipboard backend is available.
    """
    try:
        pyperclip.copy(value)
        return True
    except pyperclip.PyperclipException:
        return False


def paste_from_clipboard() -> str | None:
    """Return the current clipboard contents, or ``None`` on failure."""
    try:
        return pyperclip.paste()
    except pyperclip.PyperclipException:
        return None


# ── Signal handling ───────────────────────────────────────────────────────


@decorator
def handle_keyboard_interrupt(f, msg: str | None = "[/bold]Exiting...", *args, **kwargs):
    """Wrap a callable to catch ``KeyboardInterrupt`` and exit cleanly."""
    try:
        return f(*args, **kwargs)
    except KeyboardInterrupt:
        console.print(f"\n [yellow]⚠ Keyboard Interrupt detected. \n [bold]{msg}[/]")
        sys.exit()
