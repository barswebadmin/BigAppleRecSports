"""Context utilities for Click CLI commands."""

import os
from typing import Any, Dict, Optional, Callable

import click

# Import global config
import sys
from pathlib import Path
backend_path = Path(__file__).parent.parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))
from config import config


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


def init_service_callbacks(ctx: click.Context) -> None:
    """Initialize service creation callbacks in context meta.
    
    Sets up callbacks for creating Shopify, Slack, and Google services.
    These callbacks can be called lazily by domain commands.
    
    Args:
        ctx: Click context
    """
    # Shopify service callback
    def create_shopify_service() -> Any:
        """Create ShopifyService instance. Raises exception on failure."""
        environment = ctx.obj.get('environment', 'production') if ctx.obj else 'production'
        from bars_cli.backend_services.shopify.services import ShopifyService
        return ShopifyService(environment=environment)
    
    # Slack service callback
    def create_slack_service() -> Any:
        """Create SlackService instance. Raises exception on failure."""
        from bars_cli.backend_services.slack.slack_service import SlackService
        return SlackService()
    
    # Google Directory client callback
    def create_google_directory_client() -> Any:
        """Create GoogleDirectoryClient instance. Raises exception on failure."""
        from bars_cli.backend_services.google.directory_client import GoogleDirectoryClient
        
        # Get subject from config if available (for domain-wide delegation)
        # Priority: 1) GOOGLE.SUBJECT env var, 2) subject field in service account JSON
        global_config = ctx.meta.get('config') or config
        google_config = getattr(global_config, 'GOOGLE', None) if global_config else None
        subject = None
        
        # First try env var (GOOGLE.SUBJECT)
        if google_config and hasattr(google_config, 'SUBJECT'):
            subject = getattr(google_config, 'SUBJECT', None)
        
        # If not found, try extracting from service account JSON
        if not subject and google_config:
            service_account = getattr(google_config, 'SERVICE_ACCOUNT', None)
            if isinstance(service_account, dict) and 'subject' in service_account:
                subject = service_account.get('subject')
        
        return GoogleDirectoryClient(subject=subject)
    
    # Google Sheets client callback
    def create_google_sheets_client() -> Any:
        """Create GoogleSheetsClient instance. Raises exception on failure."""
        from bars_cli.backend_services.google.sheets_client import GoogleSheetsClient
        return GoogleSheetsClient()
    
    # Store callbacks in meta
    ctx.meta['_create_shopify_service'] = create_shopify_service
    ctx.meta['_create_slack_service'] = create_slack_service
    ctx.meta['_create_google_directory_client'] = create_google_directory_client
    ctx.meta['_create_google_sheets_client'] = create_google_sheets_client


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

