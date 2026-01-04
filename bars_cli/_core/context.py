"""Context utilities for Click CLI commands."""

import os
from typing import Any, Dict, Optional

import click


def init_context(ctx: click.Context, **kwargs: Any) -> None:
    """Initialize Click context with provided configuration.
    
    Stores configuration in ctx.obj for access by commands.
    
    Args:
        ctx: Click context
        **kwargs: Configuration key-value pairs to store in ctx.obj
        
    Example:
        @click.group()
        @click.pass_context
        def cli(ctx):
            init_context(ctx, env="production", debug=False)
    """
    ctx.ensure_object(dict)
    
    # Store all provided kwargs in ctx.obj
    for key, value in kwargs.items():
        ctx.obj[key] = value


def get_context_value(
    ctx: click.Context,
    key: str,
    default: Optional[Any] = None
) -> Any:
    """Get value from context, checking ctx.obj and ctx.meta.
    
    Args:
        ctx: Click context
        key: Key to look up
        default: Default value if key not found
        
    Returns:
        Value from context or default
    """
    # Check ctx.obj first
    if ctx.obj and key in ctx.obj:
        return ctx.obj[key]
    
    # Check ctx.meta second
    if key in ctx.meta:
        return ctx.meta[key]
    
    return default


def set_context_value(ctx: click.Context, key: str, value: Any) -> None:
    """Set value in context.
    
    Args:
        ctx: Click context
        key: Key to set
        value: Value to set
    """
    ctx.ensure_object(dict)
    ctx.obj[key] = value


def get_env_var(key: str, default: Optional[str] = None, ctx: Optional[click.Context] = None) -> Optional[str]:
    """Get environment variable, optionally from context first.
    
    Args:
        key: Environment variable name
        default: Default value if not found
        ctx: Optional Click context to check first
        
    Returns:
        Environment variable value or default
    """
    # Check context first if provided
    if ctx:
        ctx_value = get_context_value(ctx, key)
        if ctx_value is not None:
            return ctx_value
    
    # Check os.environ
    return os.environ.get(key, default)

