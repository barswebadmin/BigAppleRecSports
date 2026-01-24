"""Rich themes and console factory for consistent styling across CLI commands.

Provides pre-defined themes for different display formats and a central factory
function to create Console instances with appropriate themes.
"""

from typing import Optional, Literal
import click
from rich.console import Console
from rich.theme import Theme

# ============================================================================
# Rich Themes for Different Display Formats
# ============================================================================

# Formatted theme - for rich displays with panels, info tables, styled text
# Used for intermediate displays, detailed entity views, etc.
FORMATTED_THEME = Theme({
    # Panel styles
    "panel.border.primary": "cyan",
    "panel.border.success": "green",
    "panel.border.warning": "yellow",
    "panel.border.error": "red",
    "panel.title": "bold cyan",
    
    # Info table styles (key-value pairs)
    "info.field": "bold",
    "info.field.primary": "bold cyan",
    "info.field.success": "bold green",
    "info.field.warning": "bold yellow",
    "info.field.error": "bold red",
    "info.value": "white",
    "info.value.primary": "cyan",
    "info.value.success": "green",
    "info.value.warning": "yellow",
    "info.value.error": "red",
    
    # Table styles
    "table.header": "bold cyan",
    "table.title": "bold magenta",
    "table.column.0": "cyan",      # First column
    "table.column.1": "white",     # Second column
    "table.column.2": "yellow",    # Third column
    "table.column.3": "green",     # Fourth column
    "table.column.4": "blue",      # Fifth column
    "table.column.5": "magenta",   # Sixth column
    "table.row.even": "dim",
    "table.row.odd": "",
    
    # Text/markup styles
    "text.primary": "cyan",
    "text.secondary": "white",
    "text.success": "green",
    "text.warning": "yellow",
    "text.error": "red",
    "text.dim": "dim",
    "text.bold": "bold",
    "text.bold.primary": "bold cyan",
    "text.bold.success": "bold green",
    "text.bold.warning": "bold yellow",
    "text.bold.error": "bold red",
    
    # List/option styles
    "list.key": "bold cyan",
    "list.value": "white",
    "list.separator": "dim",
    "list.item.selected": "bold yellow",
    "list.item.unselected": "white",
})

# Simple theme - for basic tables with minimal styling
# Used for simple tabular data, quick lists, etc.
SIMPLE_THEME = Theme({
    "table.header": "bold",
    "table.column.0": "",
    "table.column.1": "",
    "table.column.2": "",
    "table.column.3": "",
    "text.primary": "",
    "text.secondary": "",
    "text.dim": "dim",
})

# JSON theme - Rich has defaults, but we can customize if needed
# Set to None to use Rich's built-in JSON colorization
JSON_THEME = None  # Use Rich's defaults

# Format-to-theme mapping
_FORMAT_THEMES: dict[str, Optional[Theme]] = {
    "formatted": FORMATTED_THEME,
    "simple": SIMPLE_THEME,
    "json": JSON_THEME,
    "raw": None,
}

# ============================================================================
# Console Factory
# ============================================================================

def get_console(
    format_type: Literal["formatted", "simple", "json", "raw"] = "formatted",
    *,
    ctx: Optional[click.Context] = None,
    color: Optional[bool] = None,
    stream = None
) -> Console:
    """Get a Rich Console instance configured for the specified format type.
    
    Central factory function for creating Console instances with appropriate
    themes based on display format. Use this for all Rich console creation
    to ensure consistent styling across the CLI.
    
    Args:
        format_type: Display format type
            - 'formatted': Rich displays with panels, info tables, styled text
            - 'simple': Basic tables with minimal styling
            - 'json': JSON output (uses Rich's defaults)
            - 'raw': Plain text (no theme)
        ctx: Optional Click context for color preferences
        color: Override color setting (if None, uses ctx.color or defaults to True)
        stream: Output stream (defaults to stdout)
    
    Returns:
        Console instance with appropriate theme and settings
    
    Usage:
        # In commands for intermediate displays
        console = get_console("formatted", ctx=ctx)
        console.print(Panel("Order Details", border_style="panel.border.primary"))
        
        # For simple tables
        console = get_console("simple", ctx=ctx)
        table = Table(header_style="table.header")
        
        # For JSON output
        console = get_console("json", ctx=ctx)
        console.print(JSON.from_data(data))
    """
    if stream is None:
        stream = click.get_text_stream("stdout")
    
    # Determine color setting
    if color is None:
        if ctx is None:
            try:
                ctx = click.get_current_context()
            except RuntimeError:
                ctx = None
        
        if ctx is not None and hasattr(ctx, 'color'):
            color_enabled = ctx.color
        else:
            color_enabled = True  # Default to enabled
    else:
        color_enabled = color
    
    # Get theme for format type
    theme = _FORMAT_THEMES.get(format_type) if color_enabled else None
    
    return Console(file=stream, theme=theme, no_color=not color_enabled)
