"""Retry logic utilities for operations that may need multiple attempts."""

from typing import Any, Callable, Optional

import click_extra as click

from bars_cli._core.validators import ValidationResult
from .decorator_wrappers import create_decorator_wrapper, is_decorator_usage


def retry_operation_until_valid(
    operation: Callable[..., Any],
    validate_result: Callable[[Any], tuple[bool, Optional[str]]],
    *args: Any,
    **kwargs: Any
) -> Any:
    """Retry an operation until it returns a valid result.
    
    Automatically retries on invalid results without prompting the user.
    Keyboard interrupts (Ctrl+C) are handled globally via the signal handler.
    
    This is a generic retry helper that can be used for any operation that might
    return invalid results, such as:
    - List selection (empty list, wrong length, etc.)
    - Text input validation (no results found, invalid format, etc.)
    - API requests that return empty or invalid responses
    - Any function that needs retry logic
    
    Args:
        operation: Callable to execute that returns a result
        validate_result: Function that takes the result and returns (is_valid, error_message).
                        is_valid=True means result is valid and should be returned.
                        is_valid=False means result is invalid and operation should retry.
        *args: Positional arguments to pass to operation
        **kwargs: Keyword arguments to pass to operation
        
    Returns:
        Valid result from operation
        
    Raises:
        KeyboardInterrupt: If user cancels (Ctrl+C) - handled globally
        
    Examples:
        ```python
        # Retry API request until non-empty result
        def validate_api_result(result):
            if isinstance(result, list) and len(result) == 0:
                return False, "No results found. Please try a different search term."
            return True, None
        
        results = retry_operation_until_valid(
            search_api,
            validate_api_result,
            query=user_input
        )
        ```
    """
    while True:
        try:
            result = operation(*args, **kwargs)
        except (KeyboardInterrupt, click.Abort):
            # Raise to let the global handler process it
            raise
        except Exception as e:
            # Unexpected error - display and automatically retry
            error_msg = f"Unexpected error: {e}"
            click.echo("\n" + click.style(f"❌ {error_msg}", fg="red") + "\n", err=True)
            # Automatically retry - continue loop
            continue
        
        # Validate result
        is_valid, error_message = validate_result(result)
        
        if is_valid:
            return result
        
        # Invalid result - display error and automatically retry
        error_msg = error_message or "Invalid result"
        click.echo("\n" + click.style(f"❌ {error_msg}", fg="red"), err=True)
        # Automatically retry - continue loop
        continue

def retry_until_valid(
    operation: Optional[Callable[..., Any]] = None,
    validate_result: Optional[Callable[[Any], ValidationResult]] = None,
    *args: Any,
    **kwargs: Any
) -> Any:
    """Retry an operation until it returns a valid result.
    
    Automatically retries on invalid results without prompting the user.
    Keyboard interrupts (Ctrl+C) are handled globally via the signal handler.
    
    This is a generic retry helper that can be used for any operation that might
    return invalid results, such as:
    - List selection (empty list, wrong length, etc.)
    - Text input validation (no results found, invalid format, etc.)
    - API requests that return empty or invalid responses
    - Any function that needs retry logic
    
    Args:
        operation: Callable to execute that returns a result (when used as function),
                   or None (when used as decorator)
        validate_result: Function that takes the result and returns ValidationResult.
                        Required when used as decorator.
        *args: Positional arguments to pass to operation (function usage only)
        **kwargs: Keyword arguments to pass to operation (function usage only)
        
    Returns:
        Valid result from operation, or a decorator function (when used as decorator)
        
    Raises:
        KeyboardInterrupt: If user cancels (Ctrl+C) - handled globally
        
    Examples:
        ```python
        # Function usage
        def get_input():
            return prompt_text_input("Enter token: ")
        
        validated = retry_until_valid(
            get_input,
            validate_result=validate_auth_token_flexible
        )
        
        # Decorator usage
        @retry_until_valid(validate_result=validate_auth_token_flexible)
        def get_input():
            return prompt_text_input("Enter token: ")
        
        validated = get_input()
        ```
    """
    # Check if validate_result is provided (could be in kwargs if used as decorator)
    actual_validate_result = validate_result or kwargs.get('validate_result')
    
    # Decorator usage: @retry_until_valid(validate_result=func)
    if is_decorator_usage(operation, actual_validate_result):
        # Extract validate_result (guaranteed to be not None at this point)
        decorator_validate_result = validate_result or kwargs.get('validate_result')
        if decorator_validate_result is None:
            raise ValueError("validate_result is required when using as decorator")
        
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            return create_decorator_wrapper(
                func,
                lambda orig_func, func_args, func_kwargs: _retry_loop(
                    orig_func, decorator_validate_result, *func_args, **func_kwargs
                )
            )
        
        return decorator
    
    # Function usage: retry_until_valid(operation, validate_result, ...)
    if validate_result is None:
        raise ValueError("validate_result is required")
    
    if operation is None or not callable(operation):
        raise ValueError("operation must be a callable when using as function")
    
    return _retry_loop(operation, validate_result, *args, **kwargs)


def _retry_loop(
    operation: Callable[..., Any],
    validate_result: Callable[[Any], ValidationResult],
    *args: Any,
    **kwargs: Any
) -> Any:
    """Internal retry loop implementation."""
    while True:
        try:
            result = operation(*args, **kwargs)
        except (KeyboardInterrupt, click.Abort):
            # Raise to let the global handler process it
            raise
        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            click.echo("\n" + click.style(f"❌ {error_msg}", fg="red") + "\n", err=True)
            continue
        
        validation_result = validate_result(result)
        
        if validation_result.input_after_validation is not None:
            return validation_result.input_after_validation
        
        error_msg = validation_result.error_message or "Invalid result"
        click.echo("\n" + click.style(f"❌ {error_msg}", fg="red"), err=True)
        continue

