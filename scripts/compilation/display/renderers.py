"""Rich rendering for compilation check results."""

import textwrap
from typing import Dict, List, Mapping, Optional, Protocol, Sequence

from rich.console import Console
from rich.panel import Panel
from rich.table import Table


# ============================================================================
# Error Protocol (defines interface renderers expects)
# ============================================================================

class ErrorProtocol(Protocol):
    """Protocol defining the interface for error objects that renderers can display.
    
    This allows renderers to work with any error object that has these attributes,
    without importing from compile_main.
    """
    file: str
    line: int
    code: str
    message: str
    import_path: Optional[str]


# ============================================================================
# Display Models (owned by renderers)
# ============================================================================

class DisplaySection:
    """A section to display in the compilation check output."""
    
    def __init__(
        self,
        title: str,
        errors: Mapping[str, Sequence[ErrorProtocol]],
        is_warning: bool = False,
        formatted_lines: Optional[Dict[str, List[str]]] = None
    ):
        self.title = title
        self.errors = errors
        self.is_warning = is_warning
        self.formatted_lines = formatted_lines or {}


class DisplaySummary:
    """Summary information for the final panel."""
    
    def __init__(
        self,
        total_errors: int,
        total_warnings: int,
        total_files: int,
        error_breakdown: Dict[str, int]
    ):
        self.total_errors = total_errors
        self.total_warnings = total_warnings
        self.total_files = total_files
        self.error_breakdown = error_breakdown


def _count_errors(errors_dict: Mapping[str, Sequence[ErrorProtocol]]) -> int:
    """Count total number of errors in an errors dictionary."""
    return sum(len(errors) for errors in errors_dict.values())


def _format_standard_error(error: ErrorProtocol) -> List[str]:
    """Format a standard error (syntax, type, required_defaults) for display."""
    return [f"  Line {error.line}: [{error.code}] {error.message}"]


def _format_import_error(error: ErrorProtocol, max_line_length: int = 100) -> List[str]:
    """Format an import error for display, handling circular import paths."""
    lines = []
    if error.import_path and error.import_path != error.file:
        parts = error.import_path.split(" → ")
        if len(parts) > 1 and parts[-1] == parts[0]:
            parts = parts[:-1]
        
        if len(parts) > 2 or len(error.import_path) > max_line_length - 10:
            lines.append(f"  [yellow]Cycle:[/yellow]")
            for part in parts:
                lines.append(f"    → {part}")
            if len(parts) > 0 and (len(parts) == 1 or parts[-1] != parts[0]):
                lines.append(f"    → {parts[0]}")
        else:
            lines.append(f"  [yellow]Cycle:[/yellow] {error.import_path}")
    
    if len(error.message) > max_line_length:
        wrapped = textwrap.fill(
            error.message,
            width=max_line_length - 2,
            initial_indent="  ",
            subsequent_indent="    ",
            break_long_words=False,
            break_on_hyphens=False
        )
        lines.extend(wrapped.split('\n'))
    else:
        lines.append(f"  {error.message}")
    
    return lines


def _format_unused_import(error: ErrorProtocol) -> str:
    """Format an unused import for display."""
    import_stmt = error.message.replace('Unused import: ', '')
    return f"line {error.line}: {import_stmt}"


def _get_error_formatter(error_type: str):
    """Get the appropriate formatter function for an error type.
    
    Args:
        error_type: Type of error
        
    Returns:
        Formatter function
    """
    if error_type == "syntax" or error_type == "type" or error_type == "required_defaults":
        return _format_standard_error
    if error_type == "import":
        return _format_import_error
    return None


def _format_errors(errors_dict: Mapping[str, Sequence[ErrorProtocol]], error_type: str) -> Dict[str, List[str]]:
    """Format errors based on their type.
    
    Args:
        errors_dict: Dictionary mapping module names to lists of errors
        error_type: Type of error ("syntax", "import", "type", "required_defaults", "unused_imports")
        
    Returns:
        Dictionary mapping module names to formatted error lines
    """
    formatted: Dict[str, List[str]] = {}
    
    for module, errors in errors_dict.items():
        module_lines: List[str] = []
        
        # Sort unused imports by line number
        sorted_errors = sorted(errors, key=lambda x: x.line) if error_type == "unused_imports" else errors
        
        for error in sorted_errors:
            if error_type == "unused_imports":
                module_lines.append(f"  - {_format_unused_import(error)}")
            else:
                formatter = _get_error_formatter(error_type)
                if formatter:
                    module_lines.extend(formatter(error))
        
        if module_lines:
            formatted[module] = module_lines
    
    return formatted


def _create_table(title: str, is_warning: bool, passed: bool, total_files: int, count: int, file_count: int) -> Table:
    """Create a status or warning table for a check section."""
    table = Table(title=title, show_header=True, header_style="bold cyan")
    table.add_column("Status", style="bold")
    table.add_column("Count", justify="right")
    
    if is_warning:
        table.add_row("[yellow]⚠️  Warnings[/yellow]", f"{count} warnings in {file_count} files")
    elif passed:
        table.add_row("[green]✓ Passed[/green]", str(total_files))
    else:
        table.add_row("[red]✗ Failed[/red]", f"{count} errors in {file_count} files")
    
    return table


def _display_error_lines(console: Console, module: str, formatted_lines: Dict[str, List[str]], errors: Sequence[ErrorProtocol], color: str) -> None:
    """Display error lines for a module."""
    console.print(f"\n[bold {color}]{module}[/bold {color}]")
    
    if module in formatted_lines:
        for line in formatted_lines[module]:
            console.print(line)
    else:
        # Fallback: format on the fly if not pre-formatted
        for error in errors:
            console.print(f"  Line {error.line}: [{error.code}] {error.message}")


def _get_error_type_from_title(title: str, is_warning: bool) -> str:
    """Determine error type from section title."""
    if is_warning:
        return "unused_imports"
    title_lower = title.lower()
    if "syntax" in title_lower:
        return "syntax"
    if "import" in title_lower:
        return "import"
    if "type" in title_lower:
        return "type"
    if "required" in title_lower or "default" in title_lower:
        return "required_defaults"
    return "syntax"  # Default fallback


def _display_section(console: Console, section: DisplaySection, total_files: int, show_separator: bool = False) -> None:
    """Display a single check section."""
    error_count = _count_errors(section.errors)
    file_count = len(section.errors)
    
    table = _create_table(
        section.title,
        section.is_warning,
        error_count == 0,
        total_files,
        error_count,
        file_count
    )
    
    if show_separator:
        console.print("\n")
    console.print(table)
    
    if error_count > 0:
        # Format errors if not already formatted
        if not section.formatted_lines:
            error_type = _get_error_type_from_title(section.title, section.is_warning)
            section.formatted_lines = _format_errors(section.errors, error_type)
        
        color = "yellow" if section.is_warning else "red"
        for module, errors in sorted(section.errors.items()):
            if errors:
                _display_error_lines(console, module, section.formatted_lines, errors, color)


def _build_panel_content(summary: DisplaySummary) -> tuple[str, str, str]:
    """Build panel content, title, and border style."""
    unused_warning = f"\n[yellow]⚠️  {summary.total_warnings} unused import(s) found[/yellow]" if summary.total_warnings > 0 else ""
    files_info = f"\nChecked {summary.total_files} files in src/{unused_warning}"
    
    if summary.total_errors == 0:
        content = f"[green]✓ All checks passed[/green]{files_info}"
        title = "[bold green]Compilation Check: SUCCESS[/bold green]"
        border = "green"
    else:
        error_lines = [f"[red]✗ Found {summary.total_errors} error(s)[/red]\n"]
        error_lines.extend(f"{error_type}: {count}" for error_type, count in summary.error_breakdown.items() if count > 0)
        error_lines.append(files_info)
        content = "\n".join(error_lines)
        title = "[bold red]Compilation Check: FAILED[/bold red]"
        border = "red"
    
    return content, title, border


def _display_final_panel(console: Console, summary: DisplaySummary) -> None:
    """Display the final status panel."""
    content, title, border = _build_panel_content(summary)
    console.print()
    console.print(Panel(content, title=title, border_style=border))


def build_display_data(
    syntax_errors: Mapping[str, Sequence[ErrorProtocol]],
    import_errors: Mapping[str, Sequence[ErrorProtocol]],
    unused_imports: Mapping[str, Sequence[ErrorProtocol]],
    type_errors: Mapping[str, Sequence[ErrorProtocol]],
    required_defaults: Mapping[str, Sequence[ErrorProtocol]],
    total_files: int,
    check_types: bool = False
) -> tuple[List[DisplaySection], DisplaySummary]:
    """Build display sections and summary from check results.
    
    This function converts raw check results into display-ready format.
    It handles all display logic including which sections to show and how to format them.
    
    Args:
        syntax_errors: Dictionary mapping module names to syntax errors
        import_errors: Dictionary mapping module names to import errors
        unused_imports: Dictionary mapping module names to unused import warnings
        type_errors: Dictionary mapping module names to type errors
        required_defaults: Dictionary mapping module names to required default violations
        total_files: Total number of files checked
        check_types: Whether type checking was enabled
        
    Returns:
        Tuple of (sections, summary) for display
    """
    # Define error collections with their display metadata
    # Format: (title, errors, is_warning, error_key, always_show)
    error_collections: List[tuple[str, Mapping[str, Sequence[ErrorProtocol]], bool, Optional[str], bool]] = [
        ("Syntax Check", syntax_errors, False, "Syntax errors", True),
        ("Import Check", import_errors, False, "Import errors", True),
    ]
    
    if check_types:
        error_collections.append(("Type Check", type_errors, False, "Type errors", True))
    
    error_collections.extend([
        ("Required Defaults Check", required_defaults, False, "Required defaults", False),
        ("Unused Imports", unused_imports, True, None, False),  # Warnings, not in error breakdown
    ])
    
    # Build sections and count errors in one pass
    sections: List[DisplaySection] = []
    error_counts: Dict[str, int] = {}
    
    for title, errors, is_warning, error_key, always_show in error_collections:
        count = _count_errors(errors)
        
        # Add section if it should always be shown or has errors
        if always_show or count > 0:
            sections.append(DisplaySection(title, errors, is_warning=is_warning))
        
        # Track error counts (exclude warnings)
        if error_key and not is_warning:
            error_counts[error_key] = count
    
    # Build summary
    total_errors = sum(error_counts.values())
    total_unused = _count_errors(unused_imports)
    error_breakdown = {k: v for k, v in error_counts.items() if v > 0}
    
    summary = DisplaySummary(
        total_errors=total_errors,
        total_warnings=total_unused,
        total_files=total_files,
        error_breakdown=error_breakdown
    )
    
    return sections, summary


def display(sections: List[DisplaySection], summary: DisplaySummary) -> None:
    """Display compilation check results.
    
    Args:
        sections: List of DisplaySection instances to display
        summary: DisplaySummary with overall statistics
    """
    console = Console()
    
    for i, section in enumerate(sections):
        _display_section(console, section, summary.total_files, show_separator=(i > 0))
    
    _display_final_panel(console, summary)
