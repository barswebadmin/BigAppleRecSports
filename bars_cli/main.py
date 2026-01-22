"""
BARS CLI Main Entry Point.

Uses Click for command-line interface.
"""
import os
import sys
from pathlib import Path
from typing import Any
from dotenv import load_dotenv

backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

import click

from ._core.decorators.handle_display_options import handle_display_options
from ._core.context import LazyServiceDict, LazyServiceProxy
from .commands.slack import slack
from .commands.shopify import shopify
from .commands.google import google
# from ._core.command_registry import discover_commands


def load_environment(env: str = "production"):
    """Load environment variables based on specified environment."""
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)
    
    if env:
        os.environ["ENVIRONMENT"] = env.lower()


@click.group(
    context_settings={
        "allow_interspersed_args": True,
        "ignore_unknown_options": True
    }
)
@click.version_option(version="1.0.0", prog_name="bars")
@click.option(
    '--json',
    'json_output',
    is_flag=True,
    default=False,
    help='Output as indented JSON (can be placed anywhere in command)'
)
@click.option(
    '--env',
    type=click.Choice(['development', 'staging', 'production'], case_sensitive=False),
    default='production',
    help='Environment to use (default: production)'
)
@handle_display_options(display=True, exit_on_error=True)
@click.pass_context
def cli(ctx: click.Context, json_output: bool, env: str):
    """
    BARS CLI - Command-line interface for BARS operations.
    
    Manage Slack groups, Shopify resources, and leadership provisioning.
    
    Global Options:
      --json    Output as indented JSON (can be placed anywhere in command)
      --env     Environment to use (development, staging, production)
    """
    ctx.ensure_object(dict)
    ctx.obj['json_output'] = json_output
    ctx.obj['environment'] = env
    # should_display will be set by handle_display_options decorator when commands run
    
    load_environment(env)
    
    # Initialize lazy service creation
    # Store LazyServiceProxy objects in ctx.meta that create services on first access
    if '_lazy_services_initialized' not in ctx.meta:
        # Store LazyServiceProxy objects for each service
        # These proxies forward attribute access to the actual service (created on first access)
        for service_key, create_func in LazyServiceDict._SERVICE_CREATORS.items():
            ctx.meta[service_key] = LazyServiceProxy(create_func, service_key)
        ctx.meta['_lazy_services_initialized'] = True
    
    # Initialize admin_bot lazily and store in context (via slack group)
    # This avoids import-time errors and makes it available to all child commands
    # Don't initialize here - let commands initialize on first use via helper function
    # This prevents import errors when CLI is just being imported/registered
    
# Auto-discover and register all commands recursively
# discover_commands(cli, commands_pkg)

# Manual command registration
cli.add_command(slack)
cli.add_command(shopify)
cli.add_command(google)


if __name__ == '__main__':
    cli()

