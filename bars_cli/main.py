"""
BARS CLI Main Entry Point.

Uses Click for command-line interface.
"""
import os
import sys
from pathlib import Path
from typing import Any
from dotenv import load_dotenv

# Add project root to Python path so 'backend' module can be imported
# This ensures imports work both when installed via pipx and when run directly
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import click_extra as click

from ._core.decorators.handle_display_options import handle_display_options
from ._core.context import LazyServiceDict, LazyServiceProxy
from ._core.ui.display import display_response
from .commands.slack import slack_grp as slack
from .commands.google import google_grp as google
from .commands.shopify import shopify_group as shopify
from .commands.compare_csv import compare_csv_cmd


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
    # Set display_response function in context for commands to use
    ctx.obj['display_response'] = display_response
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

# Manual command registration
cli.add_command(slack)
cli.add_command(shopify)
cli.add_command(google)
cli.add_command(compare_csv_cmd)


if __name__ == '__main__':
    try:
        cli()
    except (KeyboardInterrupt, click.Abort):
        sys.exit(0)

