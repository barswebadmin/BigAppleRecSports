"""
Reusable prompt utilities for interactive scripts.
Handles both TTY and non-TTY environments gracefully.
"""
import sys
from typing import Optional


def is_interactive() -> bool:
    """Check if we're running in an interactive terminal."""
    return sys.stdin.isatty() and sys.stdout.isatty()


def prompt_choice(
    question: str,
    choices: dict[str, str],
    default: Optional[str] = None,
    allow_non_interactive: bool = False
) -> str:
    """
    Prompt user to choose from a set of options.
    
    Args:
        question: The question to ask
        choices: Dict mapping choice keys to descriptions (e.g., {'c': 'Continue', 'e': 'Exit'})
        default: Default choice if user presses Enter (optional)
        allow_non_interactive: If True, returns default in non-interactive mode; if False, raises error
    
    Returns:
        The selected choice key
    
    Example:
        action = prompt_choice(
            "What would you like to do?",
            {
                'c': 'Continue anyway',
                'r': 'Retry after fixes',
                'e': 'Exit'
            },
            default='e'
        )
    """
    if not is_interactive():
        if allow_non_interactive and default:
            return default
        raise RuntimeError("Cannot prompt for input in non-interactive mode")
    
    # Display question
    print(f"\n❓ {question}")
    
    # Display choices
    choice_keys = list(choices.keys())
    for key in choice_keys:
        default_marker = " [default]" if key == default else ""
        print(f"  ({key}) {choices[key]}{default_marker}")
    
    # Get valid choice keys as comma-separated string
    valid_choices = '/'.join(choice_keys)
    
    # Prompt loop
    while True:
        response = input(f"\nChoice [{valid_choices}]: ").strip().lower()
        
        # Use default if no input
        if not response and default:
            return default
        
        # Validate choice
        if response in choice_keys:
            return response
        
        print(f"❌ Invalid choice. Please enter one of: {', '.join(choice_keys)}")


def confirm(message: str, default: bool = False) -> bool:
    """
    Simple yes/no confirmation prompt.
    
    Args:
        message: The confirmation message
        default: Default value if user presses Enter
    
    Returns:
        True if confirmed, False otherwise
    
    Example:
        if confirm("Do you want to continue?", default=False):
            print("Continuing...")
    """
    if not is_interactive():
        return default
    
    default_str = "Y/n" if default else "y/N"
    response = input(f"{message} [{default_str}]: ").strip().lower()
    
    if not response:
        return default
    
    return response in ['y', 'yes']

