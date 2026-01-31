"""Context utilities for Click CLI commands."""
import warnings
from typing import Any, Optional

import click_extra as click
from shared_utilities.api_clients.http_client import AsyncHTTPClient


# ============================================================================
# HTTP Client Management (Post-Migration)
# ============================================================================

def get_http_client(
    ctx: click.Context, 
    base_url: Optional[str] = 'https://bars-backend.loca.lt', 
    username: Optional[str] = "Username",
    password: Optional[str] = "BigAp123",
    custom_headers: Optional[dict] = None,
) -> AsyncHTTPClient:
    """Get HTTP client from context with BARS API base URL.

    After migration, all CLI commands will hit the BARS API, so we use a single
    HTTP client with the pre-configured base URL.

    Args:
        ctx: Click context
        base_url: Base URL for the API
        username: Username for basic auth
        password: Password for basic auth
        custom_headers: Additional headers to add/override

    Returns:
        AsyncHTTPClient instance configured for BARS API
    """
    if "http_client" in ctx.meta:
        return ctx.meta["http_client"]

    # Build auth dict if credentials provided
    auth = None
    if username and password:
        auth = {
            'username': username,
            'password': password
        }

    ctx.meta['http_client'] = AsyncHTTPClient(
        base_url=base_url, 
        auth=auth,
        custom_headers=custom_headers
    )
    return ctx.meta['http_client']


def get_async_http_client(
    ctx: click.Context, 
    base_url: Optional[str] = 'https://bars-backend.loca.lt', 
    username: Optional[str] = "Username",
    password: Optional[str] = "BigAp123",
    custom_headers: Optional[dict] = None,
) -> AsyncHTTPClient:
    """Alias for get_http_client for clarity in async contexts.
    
    This is the same as get_http_client() but with a more explicit name
    for use in async commands.
    """
    return get_http_client(ctx, base_url, username, password, custom_headers)

# ============================================================================
# Core Context Utilities
# ============================================================================

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
    ctx.meta['http_client'] = get_http_client(ctx)
    # Store all provided kwargs in ctx.obj
    for key, value in kwargs.items():
        ctx.obj[key] = value

@lambda f: f  # Deprecated
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

@lambda f: f  # Deprecated
def set_context_value(ctx: click.Context, key: str, value: Any) -> None:
    """Set value in context.

    Args:
        ctx: Click context
        key: Key to set
        value: Value to set
    """
    ctx.ensure_object(dict)
    ctx.obj[key] = value


def get_display_context(ctx: click.Context) -> tuple[bool, bool]:
    """Extract display context from Click context.

    Reads json_output and display_override from ctx.obj, which are set:
    - json_output: Set in main CLI group from --json flag
    - display_override: Set by handle_display_options decorator

    Args:
        ctx: Click context object

    Returns:
        Tuple of (json_output, should_display)
    """
    json_output = ctx.obj.get('json_output', False) if ctx.obj else False
    display_override = ctx.obj.get('display_override', True) if ctx.obj else True
    should_display = display_override if display_override is not None else True
    return json_output, should_display