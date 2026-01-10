"""Common decorator wrapper utilities for creating consistent decorators.

This module provides reusable helpers for creating decorators that follow
common patterns, reducing code duplication across decorator implementations.
"""

from functools import wraps
from typing import Any, Callable, Optional


def create_decorator_wrapper(
    func: Callable[..., Any],
    wrapper_logic: Callable[[Callable[..., Any], tuple, dict], Any]
) -> Callable[..., Any]:
    """Create a standard decorator wrapper with @wraps preservation.
    
    Args:
        func: The function to wrap
        wrapper_logic: A function that takes (original_func, args, kwargs) and returns the result.
                      This function should call the original_func with potentially modified args/kwargs.
    
    Returns:
        A wrapped function that preserves metadata via @wraps
    
    Example:
        def my_wrapper_logic(original_func, args, kwargs):
            # Modify args/kwargs
            modified_kwargs = {**kwargs, 'extra': 'value'}
            return original_func(*args, **modified_kwargs)
        
        @create_decorator_wrapper(my_func, my_wrapper_logic)
        def my_func(...):
            ...
    """
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return wrapper_logic(func, args, kwargs)
    
    return wrapper


def create_decorator_factory(
    decorator_logic: Callable[[Callable[..., Any]], Callable[..., Any]]
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Create a decorator factory that returns a decorator function.
    
    This is a helper for the common pattern:
        def my_decorator(...):
            def decorator(func):
                def wrapper(...):
                    ...
                return wrapper
            return decorator
    
    Args:
        decorator_logic: A function that takes the original function and returns a wrapper.
                        Should use create_decorator_wrapper internally.
    
    Returns:
        A decorator function that can be applied with @ syntax
    
    Example:
        def my_decorator_factory(param):
            return create_decorator_factory(
                lambda func: create_decorator_wrapper(
                    func,
                    lambda orig_func, args, kwargs: orig_func(*args, **{**kwargs, 'param': param})
                )
            )
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        return decorator_logic(func)
    
    return decorator


def is_decorator_usage(
    first_arg: Any,
    required_param: Optional[Any] = None,
    *,
    check_callable: bool = True
) -> bool:
    """Determine if a function is being used as a decorator vs function call.
    
    Common pattern: When first_arg is None/not callable and required_param is provided,
    the function is being used as a decorator factory.
    
    Args:
        first_arg: The first argument (typically the function/operation parameter)
        required_param: A required parameter that must be provided for decorator usage
        check_callable: If True, also checks if first_arg is callable (default: True)
    
    Returns:
        True if being used as decorator, False if being used as function
    
    Example:
        def my_decorator(operation=None, validate_func=None):
            if is_decorator_usage(operation, validate_func):
                # Decorator usage: @my_decorator(validate_func=func)
                return create_decorator_factory(...)
            else:
                # Function usage: my_decorator(operation, validate_func)
                return operation(...)
    """
    if required_param is None:
        return False
    
    if check_callable:
        return (first_arg is None or not callable(first_arg))
    else:
        return first_arg is None

