"""User input prompt utilities for BARS CLI."""

import html
import re
from typing import Any, Callable, Optional

import click
import questionary
from prompt_toolkit.styles import Style

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
        prompt: Prompt text (will be styled yellow automatically)
        default_value: Optional default value if user enters nothing
        validate_func: Optional validation function that returns (is_valid, error_message).
                      If provided, automatically retries until valid input.
        type: Optional type converter for click.prompt (e.g., str, int)
        
    Returns:
        User input string (validated if validate_func provided)
    """
    prompt_clean = prompt.lstrip()
    styled_text = click.style(prompt_clean, fg="bright_yellow")
    
    # Build kwargs for click.prompt
    prompt_kwargs = {}
    if default_value is not None:
        prompt_kwargs["default"] = default_value
    if type is not None:
        prompt_kwargs["type"] = type
    
    # No validation - simple prompt
    if validate_func is None:
        return click.prompt(f"\n{styled_text}", **prompt_kwargs)
    
    # With validation - retry until valid
    def get_input() -> str:
        value = click.prompt(f"\n{styled_text}", **prompt_kwargs)
        return normalize_string(value, ["strip"]) or ""
    
    return retry_operation_until_valid(get_input, validate_func)


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
    allowed_options = ["y", "yes", "n", "no"]
    
    def validate_yes_no(value: str) -> tuple[bool, Optional[str]]:
        """Validate input against allowed yes/no options."""
        result = validate_enum(value, allowed_options, case_sensitive=False)
        if result.error_message:
            return False, result.error_message
        return True, None
    
    default_char = "Y/n" if default else "y/N"
    full_prompt = f"{prompt} [{default_char}]"
    
    user_input = prompt_text_input(
        full_prompt,
        default_value="y" if default else "n",
        validate_func=validate_yes_no
    )
    
    return user_input.lower().strip()[0] == "y"


# ============================================================================
# Prompt Selection Utilities
# ============================================================================

def _parse_autocomplete_result(user_input: str, choices_list: list[str]) -> str:
    """Parse autocomplete result to extract the actual option value (case-insensitive).
    
    Handles:
    - "1" or "(1) oauth" → returns "oauth" (option at index 0)
    - "bearer" or "BEARER" → returns "bearer" (properly cased from choices_list)
    - "(2) bearer" → returns "bearer" (option at index 1)
    
    Always performs case-insensitive matching and returns the properly cased
    option from the original choices_list.
    
    Args:
        user_input: The user's input from autocomplete
        choices_list: Original list of choices (without numbering)
        
    Returns:
        The actual option value from choices_list (properly cased)
    """
    user_input_stripped = user_input.strip()
    
    if user_input_stripped:
        # Try numeric input first (e.g., "1" or "(1) oauth")
        try:
            choice_num = int(user_input_stripped)
            if 1 <= choice_num <= len(choices_list):
                return choices_list[choice_num - 1]
        except ValueError:
            pass
        
        # Try numbered label format (e.g., "(1) oauth")
        if user_input_stripped.startswith("(") and ")" in user_input_stripped:
            match = re.match(r"\((\d+)\)", user_input_stripped)
            if match:
                try:
                    choice_num = int(match.group(1))
                    if 1 <= choice_num <= len(choices_list):
                        return choices_list[choice_num - 1]
                except ValueError:
                    pass
        
        # Case-insensitive matching for direct option names
        user_input_lower = user_input_stripped.lower()
        for choice in choices_list:
            if choice.lower() == user_input_lower:
                return choice
    
    # If no match found, return the input as-is (will be validated by retry logic)
    return user_input_stripped


def _get_selection(
    options: list[str],
    default_value: Optional[str] = None,
    use_autocomplete: bool = True
) -> str:
    """Internal helper for selection using either autocomplete or select."""
    numbered_choices = []
    for i, choice in enumerate(options, 1):
        if use_autocomplete:
            # Strip ANSI codes before HTML escaping - ANSI codes break when questionary slices strings for highlighting
            choice_clean = strip_ansi(choice)
            numbered_label = f"({i}) {html.escape(choice_clean)}"
        else:
            numbered_label = f"({i}) {choice}"
        numbered_choices.append(numbered_label)
    
    default_choice = None
    if default_value:
        default_lower = default_value.lower()
        for i, choice in enumerate(options, 1):
            if choice.lower() == default_lower:
                if use_autocomplete:
                    choice_clean = strip_ansi(choice)
                    default_choice = f"({i}) {html.escape(choice_clean)}"
                else:
                    default_choice = f"({i}) {choice}"
                break
        if use_autocomplete and default_choice is None and default_value in numbered_choices:
            default_choice = default_value
    
    # Use Style.from_dict with all required keys to avoid layout structure issues
    custom_style = Style.from_dict({
        'qmark': 'fg:orange italic nobold',
        'question': 'fg:orange italic nobold',
        'answer': 'fg:white bg:black',
        'pointer': 'fg:orange bold',
        'selected': 'fg:white bg:black',
        'instruction': '',
        'text': '',
    })
    
    if use_autocomplete:
        click.secho("Type an option number, or start typing the option itself (press TAB to autocomplete), then ENTER to select that option:", fg='bright_yellow', italic=True)
        user_input = questionary.autocomplete(
            "- ",
            numbered_choices,
            default=default_choice if default_choice else "",
            qmark="",
            style=custom_style
        ).unsafe_ask()
    else:
        # Use simple text input and parse the number manually
        default_prompt = ""
        if default_value:
            default_lower = default_value.lower()
            for i, choice in enumerate(options, 1):
                if choice.lower() == default_lower:
                    default_prompt = str(i)
                    break
        
        user_input = prompt_text_input(
            "Enter option number or name:",
            default_value=default_prompt,
            validate_func=lambda val: (
                True, None
            ) if (val.isdigit() and 1 <= int(val) <= len(options)) or any(opt.lower() == val.lower() for opt in options) else (
                False, f"Must be a number 1-{len(options)} or one of the option names"
            )
        )
        
        # Parse input - if it's a number, convert to numbered format for _parse_autocomplete_result
        if user_input.isdigit():
            num = int(user_input)
            if 1 <= num <= len(options):
                user_input = f"({num}) {options[num-1]}"
        
        # questionary.select may return a Choice object, extract string if needed
        if not isinstance(user_input, str):
            user_input = str(user_input)
    
    if not user_input or (isinstance(user_input, str) and not user_input.strip()):
        if default_value:
            return default_value
        return ""
    
    return _parse_autocomplete_result(str(user_input), options)


# Sentinel value returned when user selects Exit
EXIT_SENTINEL = "__EXIT__"


def prompt_select_from_options(
    display_text: str,
    options: list[str],
    default_value: Optional[str] = None,
    autocomplete: Optional[bool] = True,
    show_current: Optional[str] = None,
) -> str:
    """Prompt user to select from numbered options with autocomplete and arrow key support.
    
    Features:
    - TAB autocomplete for fast selection
    - Arrow key navigation (up/down)
    - Number input (1-N)
    - Name input (case-insensitive)
    - Shows current value for context
    - Styled "Exit" option
    
    Args:
        display_text: Label to display as the header (will be bold and underlined)
        options: List of option strings to choose from
        default_value: Optional default value for the prompt
        autocomplete: If True, use autocomplete (TAB completion).
                     If False, use simple select (manual input, no autocomplete).
        show_current: Optional current value to display for context
        
    Returns:
        Selected option string from the options list, or EXIT_SENTINEL if Exit was selected
        
    Example:
        env = prompt_select_from_options(
            "Select environment",
            ["development", "staging", "production"],
            show_current="production"
        )
        if env == EXIT_SENTINEL:
            click.echo("Cancelled")
            return
    """
    if not options:
        raise ValueError("Options list cannot be empty")
    
    # Append styled Exit option
    exit_option = click.style("Exit", fg="red", bold=True)
    options_with_exit = options + [exit_option]
    
    header_text = f"{display_text}\n"
    click.echo(f"\n{click.style(header_text, bold=True, underline=True)}")
    
    # Show current value if provided (without making it the default)
    if show_current:
        click.echo(f"  Current: {click.style(show_current, fg='cyan', italic=True)}")
        click.echo()
    
    for i, choice in enumerate(options_with_exit, 1):
        if choice == exit_option:
            click.echo(f"  ({i}) {exit_option}")
        else:
            click.echo(f"  ({i}) {click.style(choice, fg='blue')}")
    click.echo()
    
    selected = _get_selection(
        options_with_exit, 
        default_value, 
        use_autocomplete=autocomplete if autocomplete is not None else True
    )
    
    selected_clean = strip_ansi(selected).strip().lower()
    exit_clean = strip_ansi(exit_option).strip().lower()
    
    # Handle numbered format like "(11) Exit" or just "Exit"
    if selected_clean.startswith("(") and ")" in selected_clean:
        selected_clean = selected_clean.split(")", 1)[1].strip()
    
    if selected_clean == exit_clean or selected_clean == "exit":
        return EXIT_SENTINEL
    
    # Validate the selection against original options (not including Exit)
    validation_result = validate_enum(selected, options, case_sensitive=False)
    if validation_result.error_message:
        raise ValueError(validation_result.error_message)
    
    # Return properly cased version (guaranteed to be a string after successful validation)
    if validation_result.input_after_validation is None:
        raise ValueError("Validation succeeded but no value returned")
    return validation_result.input_after_validation


# ============================================================================
# Legacy/Simple Prompt Choice (Kept for Compatibility)
# ============================================================================

def prompt_choice(
    prompt: str,
    choices: list[str],
    default: Optional[str] = None
) -> str:
    """Simple prompt to select from a list of choices (no autocomplete).
    
    For better UX with autocomplete and arrow keys, use prompt_select_from_options() instead.
    
    Args:
        prompt: Prompt text
        choices: List of valid choices
        default: Optional default choice
        
    Returns:
        Selected choice
    
    Example:
        env = prompt_choice(
            "Select environment:",
            ["development", "staging", "production"],
            default="development"
        )
    """
    styled_prompt = click.style(prompt, fg="bright_yellow")
    
    # Display choices
    click.echo(f"\n{styled_prompt}")
    for i, choice in enumerate(choices, 1):
        choice_str = click.style(f"  {i}. {choice}", fg="cyan")
        if default and choice == default:
            choice_str += click.style(" (default)", dim=True)
        click.echo(choice_str)
    
    def validate_choice(value: str) -> tuple[bool, Optional[str]]:
        # Check if it's a number
        try:
            num = int(value)
            if 1 <= num <= len(choices):
                return True, None
        except ValueError:
            pass
        
        # Check if it's a valid choice name (case-insensitive)
        if value.lower() in [c.lower() for c in choices]:
            return True, None
        
        return False, f"Invalid choice. Please enter 1-{len(choices)} or a valid choice name."
    
    # Get input with validation
    selection = prompt_text_input(
        "Enter your choice: ",
        default_value=default,
        validate_func=validate_choice
    )
    
    # Convert to actual choice
    try:
        num = int(selection)
        return choices[num - 1]
    except (ValueError, IndexError):
        # Find by name (case-insensitive)
        for choice in choices:
            if choice.lower() == selection.lower():
                return choice
    
    # Should never reach here due to validation, but return default as fallback
    return default or choices[0]
