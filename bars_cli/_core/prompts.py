"""
User input prompt utilities for BARS CLI.

Provides comprehensive prompting functionality including:
- Basic text/confirmation prompts
- Selection from options with autocomplete
- Model-driven prompts from Pydantic models
- Result selection and formatting
"""

import html
import re
from typing import Any, Callable, Dict, Optional, Type, Union, get_origin, get_args

import click_extra as click
import questionary
from questionary import Style
from pydantic import BaseModel

from bars_cli._core.utils import strip_ansi, normalize_string


# ============================================================================
# STYLING UTILITIES
# ============================================================================

def style_field_name(text: str) -> str:
    """Style field names with cyan color."""
    return click.style(text, fg='cyan', bold=True)


def style_required(text: str) -> str:
    """Style required field indicators with red color."""
    return click.style(text, fg='red')


def style_optional(text: str) -> str:
    """Style optional field indicators with yellow color."""
    return click.style(text, fg='yellow')


def style_success(text: str) -> str:
    """Style success messages with green color."""
    return click.style(text, fg='green', bold=True)


def style_error(text: str) -> str:
    """Style error messages with red color."""
    return click.style(text, fg='red', bold=True)


# ============================================================================
# SHARED CONSTANTS AND STYLES
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

# Sentinel values for special selections
EXIT_SENTINEL = "__EXIT__"
DONE_SENTINEL = "__DONE__"


# ============================================================================
# BASIC INPUT PROMPTS
# ============================================================================

def prompt_text_input(
    prompt: str,
    *,
    default_value: Optional[str] = None,
    validate_func: Optional[Callable[[str], tuple[bool, Optional[str]]]] = None,
    input_type: Optional[Any] = None
) -> str:
    """Prompt for text input with optional validation and retry logic.

    Args:
        prompt: Prompt text
        default_value: Optional default value if user enters nothing
        validate_func: Optional validation function that returns (is_valid, error_message).
                      If provided, automatically retries until valid input.
        input_type: Optional type converter (e.g., str, int). Note: questionary handles this via validation.

    Returns:
        User input string (validated if validate_func provided)
    """
    if validate_func:
        def validator(text):
            result = validate_func(text)
            return True if result[0] else (result[1] or False)
    elif input_type is not None:
        def validator(_text):
            return True
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

    if input_type is not None and validate_func is None:
        try:
            return str(input_type(normalized))
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
# SELECTION PROMPTS
# ============================================================================

def _display_grouped_options(options_dict: dict[str, list[dict]], display_all: bool, display_done: bool, display_cancel: bool) -> tuple[list[str], int]:
    """
    Display options grouped by sections and return display list and base option count.
    
    Args:
        options_dict: Dict mapping section names to lists of option dicts
        display_all: Whether to show "All" option
        display_done: Whether to show "Done" option  
        display_cancel: Whether to show "Cancel/Exit" option
        
    Returns:
        Tuple of (display_options_list, base_options_count)
    """
    display_options = []
    base_count = 0
    option_number = 1
    
    for section_name, section_options in options_dict.items():
        # Display section header
        click.echo(f"\n{click.style(section_name, fg='blue', bold=True, underline=True)}")
        
        for opt in section_options:
            if 'value' not in opt or 'display' not in opt:
                raise ValueError(f"Option must have 'value' and 'display' keys: {opt}")
                
            display_options.append(opt['display'])
            base_count += 1
            
            # Display with indentation for section
            click.echo(f"    ({option_number}) {opt['display']}")
            option_number += 1
    
    # Add special options
    all_label = "All"
    done_label = "Done" 
    cancel_label = "Cancel/Exit"
    
    if display_all:
        display_options.append(all_label)
        click.echo(f"  ({option_number}) {click.style(all_label, fg='yellow', bold=True)}")
        option_number += 1
        
    if display_done:
        display_options.append(done_label)
        click.echo(f"  ({option_number}) {click.style(done_label, fg='green', bold=True)}")
        option_number += 1
        
    if display_cancel:
        display_options.append(cancel_label)
        click.echo(f"  ({option_number}) {click.style(cancel_label, fg='red', bold=True)}")
    
    return display_options, base_count


def _display_flat_options(options: list[dict], display_all: bool, display_done: bool, display_cancel: bool) -> list[str]:
    """
    Display options in flat format and return display list.
    
    Args:
        options: List of option dicts with 'value' and 'display' keys
        display_all: Whether to show "All" option
        display_done: Whether to show "Done" option
        display_cancel: Whether to show "Cancel/Exit" option
        
    Returns:
        List of display strings for autocomplete
    """
    all_label = "All"
    done_label = "Done"
    cancel_label = "Cancel/Exit"

    # Build display options (what user sees)
    display_options = [opt['display'] for opt in options]
    if display_all:
        display_options.append(all_label)
    if display_done:
        display_options.append(done_label)
    if display_cancel:
        display_options.append(cancel_label)

    for i, display_opt in enumerate(display_options, 1):
        if display_cancel and display_opt == cancel_label:
            click.echo(f"  ({i}) {click.style(cancel_label, fg='red', bold=True)}")
        elif display_done and display_opt == done_label:
            click.echo(f"  ({i}) {click.style(done_label, fg='green', bold=True)}")
        elif display_all and display_opt == all_label:
            click.echo(f"  ({i}) {click.style(all_label, fg='yellow', bold=True)}")
        else:
            click.echo(f"  ({i}) {display_opt}")
    
    return display_options


def prompt_select_from_options(
    display_text: str,
    options: Union[list[dict], dict[str, list[dict]]],
    current_value: Optional[str] = None,
    current_value_mode: str = "display",
    *,
    display_all: bool = False,
    display_cancel: bool = True,
    display_done: bool = False,
) -> Optional[str]:
    """Prompt user to select from numbered options with autocomplete support.

    Features:
    - TAB autocomplete for fast selection
    - Number input (1-N)
    - Name input (case-insensitive)
    - Shows current value for context
    - Optional "All" option (yellow)
    - Optional "Cancel/Exit" option (red)
    - Optional "Done" option (green)
    - Section grouping support

    Args:
        display_text: Label to display as the header
        options: Either a list of option dicts with 'value' and 'display' keys,
                or a dict mapping section names to lists of option dicts
        current_value: Current value to show/use as default (matches 'value' key)
        current_value_mode: How to handle current_value:
            - "display": Show current value for context only (no default selection)
            - "default": Show current value AND make it the default selection
            - None: Don't show or use current value
        display_all: If True, adds yellow "All" option that returns "All"
        display_cancel: If True, adds red "Cancel/Exit" option that returns None
        display_done: If True, adds green "Done" option that returns DONE_SENTINEL

    Returns:
        - Selected option 'value' from the options list
        - "All" if "All" was selected (when display_all=True)
        - DONE_SENTINEL if "Done" was selected (when display_done=True)
        - None if "Cancel/Exit" was selected (when display_cancel=True)
    """
    if not options:
        raise ValueError("Options cannot be empty")

    # Validate current_value_mode
    if current_value_mode not in [None, "display", "default"]:
        raise ValueError("current_value_mode must be None, 'display', or 'default'")

    # Determine if we have sections and flatten options for processing
    if isinstance(options, dict):
        # Sectioned options
        has_sections = True
        selectable_options = []
        for section_options in options.values():
            selectable_options.extend(section_options)
    else:
        # Flat options
        has_sections = False
        selectable_options = options
    
    # Validate option format for selectable options
    for i, opt in enumerate(selectable_options):
        if not isinstance(opt, dict) or 'value' not in opt or 'display' not in opt:
            raise ValueError(f"Option {i} must be a dict with 'value' and 'display' keys")

    # Find default index and current display based on current_value
    default_idx = None
    current_display = None
    if current_value_mode == "default" and current_value:
        for i, opt in enumerate(selectable_options):
            if opt['value'] == current_value:
                default_idx = i
                current_display = opt['display']
                break

    # Find current display value for showing context
    if current_value_mode in ["display", "default"] and current_value and not current_display:
        for opt in selectable_options:
            if opt['value'] == current_value:
                current_display = opt['display']
                break

    click.echo(f"\n{click.style(display_text, bold=True, underline=True)}")

    # Show current value based on mode
    if current_display and current_value_mode in ["display", "default"]:
        if current_value_mode == "default":
            click.echo(f"  Current: {click.style(current_display, fg='cyan', italic=True)} "
                      f"{click.style('(press ENTER to keep)', fg='yellow', dim=True)}")
        else:  # display mode
            click.echo(f"  Current: {click.style(current_display, fg='cyan', italic=True)}")

    click.echo()

    # Display options using appropriate method
    if has_sections:
        display_options, base_count = _display_grouped_options(
            options, display_all, display_done, display_cancel
        )
    else:
        display_options = _display_flat_options(
            selectable_options, display_all, display_done, display_cancel
        )
        base_count = len(selectable_options)

    click.echo()

    # Build numbered options for autocomplete
    numbered = []
    for i, display_opt in enumerate(display_options, 1):
        numbered.append(f"({i}) {html.escape(strip_ansi(display_opt))}")

    # Only set default in autocomplete if we have a default_idx (current_value_mode="default")
    default_str = (f"({default_idx + 1}) {html.escape(strip_ansi(current_display))}"
                   if default_idx is not None and current_display else "")

    click.secho(
        "Type an option number, or start typing the option itself "
        "(press TAB to autocomplete), then ENTER to select:",
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

    if result is None:
        raise KeyboardInterrupt("Cancelled by user")

    if not result:
        # Empty input - return current_value if in default mode, otherwise None/cancel
        if current_value_mode == "default" and current_value:
            return current_value
        return None if display_cancel else ""

    result_clean = strip_ansi(str(result)).strip().lower()

    match = re.match(r"\(?(\d+)\)?", result_clean)
    if match:
        try:
            num = int(match.group(1))
            if 1 <= num <= base_count:
                return selectable_options[num - 1]['value']

            # Calculate positions for special options
            all_num = base_count + 1 if display_all else None
            done_num = (base_count + (1 if display_all else 0) + 1
                       if display_done else None)
            cancel_num = (base_count + (1 if display_all else 0) +
                         (1 if display_done else 0) + 1 if display_cancel else None)

            if display_all and num == all_num:
                return "All"
            if display_done and num == done_num:
                return DONE_SENTINEL
            if display_cancel and num == cancel_num:
                return None
        except ValueError:
            pass

    # Handle text-based selection
    cancel_label = "Cancel/Exit"
    done_label = "Done"
    all_label = "All"
    
    if display_cancel and result_clean.endswith(cancel_label.lower()):
        return None
    if display_done and result_clean.endswith(done_label.lower()):
        return DONE_SENTINEL
    if display_all and result_clean.endswith(all_label.lower()):
        return "All"

    # Try to match by display text
    for opt in selectable_options:
        display_clean = strip_ansi(opt['display']).strip().lower()
        if display_clean == result_clean or result_clean.endswith(display_clean):
            return opt['value']

    return result_clean


# ============================================================================
# RESULT FORMATTING AND SELECTION
# ============================================================================

def format_result_option(result: dict, fields: list[str],
                        labels: Optional[dict[str, str]] = None) -> str:
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
        label = ((labels.get(field) if labels else None) or
                field.replace('_', ' ').title() + ":")
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
        List of selected result dictionaries (always returns a list, even for
        single selections)
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
        options.append({"value": option_text, "display": option_text})

    selected_option = prompt_select_from_options(
        prompt_text,
        options,
        display_all=allow_all
    )

    if selected_option is None:
        raise KeyboardInterrupt("Cancelled by user")

    if selected_option == "All":
        return results

    return [result_map[selected_option]]


# ============================================================================
# MODEL-DRIVEN PROMPTS
# ============================================================================

def get_field_info(model_class: Type[BaseModel]) -> Dict[str, Dict[str, Any]]:
    """Extract field information from a Pydantic model."""
    fields_info = {}

    for field_name, field_info in model_class.model_fields.items():
        # Skip class attributes that aren't request data fields
        if field_name in ['method', 'endpoint', 'headers', 'params', 'body']:
            continue

        # Skip properties (they show up as fields but aren't actual input fields)
        if (hasattr(model_class, field_name) and
                isinstance(getattr(model_class, field_name), property)):
            continue

        field_data = {
            'name': field_name,
            'type': field_info.annotation,
            'required': field_info.is_required(),
            'default': field_info.default if field_info.default is not ... else None,
            'description': (field_info.description or
                           f"{field_name.replace('_', ' ').title()}"),
            'field_info': field_info
        }

        # Handle Optional types
        origin = get_origin(field_info.annotation)
        if origin is Union:
            args = get_args(field_info.annotation)
            if len(args) == 2 and type(None) in args:
                field_data['type'] = args[0] if args[1] is type(None) else args[1]
                field_data['required'] = False

        fields_info[field_name] = field_data

    return fields_info


def prompt_for_field(field_info: Dict[str, Any], current_value: Any = None) -> Any:
    """Prompt user for a single field value with validation."""
    field_type = field_info['type']
    description = field_info['description']
    required = field_info['required']
    default = field_info.get('default')

    # If we already have a value, return it
    if current_value is not None:
        return current_value

    # Create prompt text
    prompt_text = f"{style_field_name(description)}"
    if required:
        prompt_text += f" {style_required('(required)')}"
    else:
        prompt_text += f" {style_optional('(optional)')}"

    # Handle different field types
    if field_type is str:
        if required:
            while True:
                value = click.prompt(prompt_text, default=default or "",
                                   show_default=bool(default))
                if value.strip():
                    return value.strip()
                click.echo("❌ This field is required and cannot be empty.")

        value = click.prompt(prompt_text, default=default or "",
                           show_default=bool(default))
        return value.strip() if value else None

    if field_type is int:
        return click.prompt(prompt_text, type=int, default=default,
                          show_default=bool(default))

    if field_type is float:
        return click.prompt(prompt_text, type=float, default=default,
                          show_default=bool(default))

    if field_type is bool:
        return click.confirm(prompt_text,
                           default=default if default is not None else False)

    # Fallback to string input for complex types
    if required:
        return click.prompt(prompt_text, default=default or "")

    value = click.prompt(prompt_text, default=default or "",
                       show_default=bool(default))
    return value if value else None


def prompt_model_fields(
    model_class: Type[BaseModel],
    ctx: click.Context,
    current_values: Optional[Dict[str, Any]] = None,
    skip_optional: bool = False,
    interactive: bool = True
) -> Dict[str, Any]:
    """
    Prompt for all fields in a Pydantic model.

    Args:
        model_class: The Pydantic model class to prompt for
        ctx: Click context
        current_values: Dict of already provided values (from CLI args/options)
        skip_optional: If True, skip prompting for optional fields
        interactive: If False, only use provided values (no prompting)

    Returns:
        Dict of field values ready to create the model instance
    """
    current_values = current_values or {}
    fields_info = get_field_info(model_class)
    result = {}

    # Check if we're in JSON output mode (non-interactive)
    json_output = ctx.obj.get('json_output', False) if ctx.obj else False
    should_display = ctx.obj.get('should_display', True) if ctx.obj else True

    if json_output or not should_display or not interactive:
        # Non-interactive mode: only use provided values
        for field_name, field_info in fields_info.items():
            if field_name in current_values:
                result[field_name] = current_values[field_name]
            elif field_info['required']:
                raise click.ClickException(
                    f"Required field '{field_name}' not provided")
        return result

    # Interactive mode: prompt for missing values
    click.echo(f"\n📝 {style_field_name('Configuring')} {model_class.__name__}")
    click.echo("=" * 50)

    # First, handle required fields
    required_fields = {k: v for k, v in fields_info.items() if v['required']}
    if required_fields:
        click.echo(f"\n{style_required('Required Fields:')}")
        for field_name, field_info in required_fields.items():
            current_value = current_values.get(field_name)
            result[field_name] = prompt_for_field(field_info, current_value)

    # Then, handle optional fields
    optional_fields = {k: v for k, v in fields_info.items() if not v['required']}
    if optional_fields and not skip_optional:
        click.echo(f"\n{style_optional('Optional Fields:')}")

        if len(optional_fields) > 1:
            # Ask if user wants to configure optional fields
            configure_optional = click.confirm(
                f"Configure {len(optional_fields)} optional field(s)?",
                default=False
            )
            if not configure_optional:
                # Still include any optional values that were provided via CLI
                for field_name in optional_fields:
                    if field_name in current_values:
                        result[field_name] = current_values[field_name]
                return result

        for field_name, field_info in optional_fields.items():
            current_value = current_values.get(field_name)
            if current_value is not None:
                result[field_name] = current_value
            else:
                # Ask if user wants to set this optional field
                field_desc = field_info['description']
                if click.confirm(f"Set {field_desc.lower()}?", default=False):
                    result[field_name] = prompt_for_field(field_info)

    return result


def create_model_from_prompts(
    model_class: Type[BaseModel],
    ctx: click.Context,
    current_values: Optional[Dict[str, Any]] = None,
    skip_optional: bool = False,
    interactive: bool = True
) -> BaseModel:
    """
    Create a Pydantic model instance by prompting for missing fields.

    Args:
        model_class: The Pydantic model class to create
        ctx: Click context
        current_values: Dict of already provided values (from CLI args/options)
        skip_optional: If True, skip prompting for optional fields
        interactive: If False, only use provided values (no prompting)

    Returns:
        Instance of the model class with all required fields populated
    """
    field_values = prompt_model_fields(
        model_class=model_class,
        ctx=ctx,
        current_values=current_values,
        skip_optional=skip_optional,
        interactive=interactive
    )

    try:
        return model_class(**field_values)
    except Exception as e:
        raise click.ClickException(f"Failed to create {model_class.__name__}: {e}")


def prompt_for_missing_options(options: list[dict], _ctx: click.Context) -> dict:
    """
    Prompt for missing required options and collect all values.
    
    Args:
        options: List of option dictionaries with keys:
            - 'value': Current value (None if not provided)
            - 'display_value': Human-readable name for prompting
            - 'required': Boolean indicating if this option is required
            - 'key': Key to use in returned dictionary
        ctx: Click context for accessing configuration
    
    Returns:
        Dictionary mapping option keys to collected values
    
    Example:
        options = [
            {'value': email, 'display_value': 'Email', 'required': True, 'key': 'email'},
            {'value': name, 'display_value': 'Name', 'required': True, 'key': 'name'},
            {'value': desc, 'display_value': 'Description', 'required': False, 'key': 'description'}
        ]
        values = prompt_for_missing_options(options, ctx)
        # Returns: {'email': 'user@example.com', 'name': 'User Name', 'description': None}
    """
    collected_values = {}
    
    # First, collect all provided values
    for option in options:
        if option['value'] is not None:
            collected_values[option['key']] = option['value']
    
    # Find missing required options
    missing_required = []
    missing_optional = []
    
    for option in options:
        if option['value'] is None:
            if option['required']:
                missing_required.append(option)
            else:
                missing_optional.append(option)
    
    # If no missing required options, we're done
    if not missing_required:
        # Still collect optional values that weren't provided
        for option in missing_optional:
            collected_values[option['key']] = None
        return collected_values
    
    # Prompt for missing required options
    for option in missing_required:
        prompt_text = f"Enter {option['display_value']}: "
        try:
            value = prompt_text_input(prompt_text)
            if not value.strip():
                raise click.ClickException(f"{option['display_value']} is required")
            collected_values[option['key']] = value.strip()
        except KeyboardInterrupt as exc:
            raise click.ClickException("Cancelled by user") from exc
    
    # Prompt for optional values if user wants to provide them
    for option in missing_optional:
        try:
            prompt_text = f"Enter {option['display_value']} (optional, press Enter to skip): "
            value = prompt_text_input(prompt_text)
            collected_values[option['key']] = value.strip() if value and value.strip() else None
        except KeyboardInterrupt:
            # For optional fields, allow skipping on Ctrl+C
            collected_values[option['key']] = None
    
    return collected_values