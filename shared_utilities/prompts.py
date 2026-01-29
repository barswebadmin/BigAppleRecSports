"""User input prompt utilities for BARS CLI."""

import re
from typing import Any, Callable, Optional

import click_extra as click
import questionary
from questionary import Choice, Style

from bars_cli._core.decorators import retry_operation_until_valid
from bars_cli._core.utils import strip_ansi, normalize_string
from bars_cli._core.validators import ValidationResult, validate_enum


# ============================================================================
# Text Input Prompts
# ============================================================================

def prompt_text_input(
    prompt: str,
    *,
    default_value: Optional[str] = None,
    validate_func: Optional[Callable[[str], tuple[bool, Optional[str]]]] = None,
    type: Optional[Any] = None
) -> str:
    """Prompt for text input with optional validation and retry logic.
    
    Args:
        prompt: Prompt text
        default_value: Optional default value if user enters nothing
        validate_func: Optional validation function that returns (is_valid, error_message).
                      If provided, automatically retries until valid input.
        type: Optional type converter (e.g., str, int). Note: questionary handles this via validation.
        
    Returns:
        User input string (validated if validate_func provided)
    """
    if validate_func:
        validator = lambda text: (lambda result: True if result[0] else (result[1] or False))(validate_func(text))
    elif type is not None:
        validator = lambda text: True
    else:
        validator = None
    
    result = questionary.text(
        prompt.lstrip(),
        default=default_value or "",
        validate=validator,
        style=_QUESTIONARY_STYLE
    ).ask()
    
    if result is None:
        raise KeyboardInterrupt("Cancelled by user")
    
    if not result:
        return default_value or ""
    
    normalized = normalize_string(result, ["strip"]) or ""
    
    if type is not None and validate_func is None:
        try:
            return str(type(normalized))
        except (ValueError, TypeError):
            return normalized
    
    return normalized


def prompt_confirmation(
    prompt: str = "Continue?",
    default: bool = True
) -> bool:
    """Prompt user for yes/no confirmation.
    
    Args:
        prompt: Prompt text (default: "Continue?")
        default: Default value if user just presses Enter (default: True)
        
    Returns:
        True if user confirms, False otherwise
    """
    result = questionary.confirm(
        prompt,
        default=default,
        style=_QUESTIONARY_STYLE
    ).ask()
    
    if result is None:
        raise KeyboardInterrupt("Cancelled by user")
    
    return result if result is not None else default


# ============================================================================
# Prompt Selection Utilities
# ============================================================================

# Shared style for questionary prompts
_QUESTIONARY_STYLE = Style([
    ('qmark', 'fg:orange italic nobold'),
    ('question', 'fg:orange italic nobold'),
    ('answer', 'fg:white bg:black'),
    ('pointer', 'fg:orange bold'),
    ('selected', 'fg:white bg:black'),
    ('highlighted', 'fg:orange bold'),
    ('instruction', ''),
    ('text', ''),
])




# Sentinel value returned when user selects Exit
EXIT_SENTINEL = "__EXIT__"
ALL_SENTINEL = "__ALL__"


def prompt_select_from_options(
    display_text: str,
    options: list[str],
    default_value: Optional[str] = None,
    show_current: Optional[str] = None,
    *,
    autocomplete: bool = True,
    display_exit: bool = True,
    display_all: bool = False,
) -> Optional[str]:
    """Prompt user to select from numbered options with autocomplete support.
    
    Features:
    - TAB autocomplete for fast selection
    - Number input (1-N)
    - Name input (case-insensitive)
    - Shows current value for context
    - Optional "All" option
    - Optional "Exit" option
    
    Args:
        display_text: Label to display as the header
        options: List of option strings to choose from
        default_value: Optional default value for the prompt
        show_current: Optional current value to display for context (shown in prompt text)
        
    Returns:
        Selected option string from the options list, ALL_SENTINEL if "All" was selected,
        or None if "Exit" was selected (when display_exit=True)
        
    Example:
        env = prompt_select_from_options(
            "Select environment",
            ["development", "staging", "production"],
            show_current="production"
        )
        if env is None:
            return
    """
    if not options:
        raise ValueError("Options list cannot be empty")
    
    import html

    prompt_text = f"{display_text} (Current: {show_current})" if show_current else display_text
    
    default_idx = None
    if default_value:
        target_lower = default_value.lower()
        for i, opt in enumerate(options):
            if opt.lower() == target_lower:
                default_idx = i
                break
    
    base_options = options.copy()
    all_label = "All"
    exit_label = "Exit"

    display_options: list[str] = base_options.copy()
    if display_all:
        display_options.append(all_label)
    if display_exit:
        display_options.append(exit_label)

    click.echo(f"\n{click.style(display_text, bold=True, underline=True)}")
    if show_current:
        click.echo(f"  Current: {click.style(show_current, fg='cyan', italic=True)}")
    click.echo()

    for i, opt in enumerate(display_options, 1):
        if display_exit and opt == exit_label:
            click.echo(f"  ({i}) {click.style(exit_label, fg='red', bold=True)}")
        elif display_all and opt == all_label:
            click.echo(f"  ({i}) {click.style(all_label, fg='green', bold=True)}")
        else:
            click.echo(f"  ({i}) {opt}")
    click.echo()

    numbered = []
    for i, opt in enumerate(display_options, 1):
        numbered.append(f"({i}) {html.escape(strip_ansi(opt))}")

    default_str = f"({default_idx + 1}) {html.escape(strip_ansi(options[default_idx]))}" if default_idx is not None else ""
    
    if autocomplete:
        click.secho(
            "Type an option number, or start typing the option itself (press TAB to autocomplete), then ENTER to select:",
            fg="bright_yellow",
            italic=True,
        )
        result = questionary.autocomplete(
            "- ",
            numbered,
            default=default_str,
            qmark="",
            style=_QUESTIONARY_STYLE,
        ).ask()
    else:
        default_prompt = ""
        if default_idx is not None:
            default_prompt = str(default_idx + 1)

        result = prompt_text_input(
            "Enter option number or name:",
            default_value=default_prompt,
            validate_func=lambda val: (
                True,
                None,
            )
            if (
                (val.isdigit() and 1 <= int(val) <= len(display_options))
                or any(strip_ansi(opt).strip().lower() == val.strip().lower() for opt in display_options)
            )
            else (False, f"Must be a number 1-{len(display_options)} or one of the option names"),
        )
    
    if result is None:
        raise KeyboardInterrupt("Cancelled by user")
    
    if not result:
        return default_value or (None if display_exit else "")
    
    result_clean = strip_ansi(str(result)).strip().lower()
    
    match = re.match(r"\(?(\d+)\)?", result_clean)
    if match:
        try:
            num = int(match.group(1))
            if 1 <= num <= len(base_options):
                return base_options[num - 1]

            all_num = len(base_options) + 1
            exit_num = len(base_options) + (1 if display_all else 0) + 1

            if display_all and num == all_num:
                return ALL_SENTINEL
            if display_exit and num == exit_num:
                return None
        except ValueError:
            pass

    if display_exit and result_clean.endswith(exit_label.lower()):
        return None
    if display_all and result_clean.endswith(all_label.lower()):
        return ALL_SENTINEL
    
    for opt in base_options:
        opt_clean = strip_ansi(opt).strip().lower()
        if opt_clean == result_clean or result_clean.endswith(opt_clean):
            return opt
    
    return result_clean


def format_result_option(result: dict, fields: list[str], labels: Optional[dict[str, str]] = None) -> str:
    """Format a single result as an option string.
    
    Uses click.style for colors, similar to search command.
    
    Args:
        result: Dictionary representing a result row
        fields: List of field keys to display
        labels: Optional dict mapping field keys to display labels
        
    Returns:
        Formatted option string with blue labels and | separators
    """
    
    parts = []
    for field in fields:
        label = (labels.get(field) if labels else None) or field.replace('_', ' ').title() + ":"
        value = result.get(field, "unknown")
        
        # Format dates if they're datetime objects
        if hasattr(value, 'strftime'):
            value = value.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(value, str) and len(value) > 19:
            value = value[:19]
        
        styled_label = click.style(label, fg="blue")
        parts.append(f"{styled_label} {value}")
    
    separator = click.style("|", fg="blue")
    return f" {separator} ".join(parts)


def prompt_result_selection(
    results: list[dict],
    prompt_text: str,
    fields: list[str],
    labels: Optional[dict[str, str]] = None,
    allow_all: bool = True
) -> list[dict]:
    """Prompt user to select one or all results from a list.
    
    Formats results using provided fields/labels and prompts for selection.
    
    Args:
        results: List of dictionaries to choose from
        prompt_text: Text to display in the prompt header
        fields: List of field keys to display in each option
        labels: Optional dict mapping field keys to display labels
        allow_all: If True, includes "All" option. If False, requires single selection.
        
    Returns:
        List of selected result dictionaries (always returns a list, even for single selections)
    """
    if not results:
        raise ValueError("results list cannot be empty")
    
    if len(results) == 1:
        return results
    
    options = []
    result_map = {}
    
    for result in results:
        option_text = format_result_option(result, fields, labels)
        result_map[option_text] = result
        options.append(option_text)
    
    if allow_all:
        all_option = click.style("All", fg="green", bold=True)
        options_with_all = options + [all_option]
    else:
        options_with_all = options
        all_option = None
    
    selected_option = prompt_select_from_options(prompt_text, options_with_all)

    if selected_option is None:
        raise KeyboardInterrupt("Cancelled by user")
    
    if all_option:
        selected_clean = strip_ansi(selected_option).strip().lower()
        all_clean = strip_ansi(all_option).strip().lower()
        
        if selected_clean == all_clean or selected_clean == "all":
            return results
    
    return [result_map[selected_option]]