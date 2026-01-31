"""
BARS CLI Main Entry Point.

Uses Click for command-line interface.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

import sys
import os
from pathlib import Path

# Environment-aware path setup
def setup_paths():
    """Setup paths based on environment."""
    
    # Check if we're in production (Render sets this)
    if os.getenv('RENDER') or os.getenv('PYTHONPATH'):
        # In production, assume paths are already set up
        return
    
    # Development mode - find and add repo paths
    current_file = Path(__file__).resolve()
    repo_root = current_file
    
    # Walk up to find repo root
    for _ in range(10):  # Max 10 levels up
        if (repo_root / "shared_utilities").exists() and (repo_root / "backend").exists():
            # Add paths for development
            for path in [str(repo_root), str(repo_root / "shared_utilities"), str(repo_root / "backend")]:
                if path not in sys.path:
                    sys.path.insert(0, path)
            
            # Load .env file from repo root
            env_file = repo_root / ".env"
            if env_file.exists():
                load_dotenv(env_file)
            
            return
        
        if repo_root.parent == repo_root:
            break
        repo_root = repo_root.parent

# Setup paths
setup_paths()

# Import with fallback
try:
    from paths import get_repo_root
except ImportError:
    def get_repo_root():
        return Path.cwd()

import click_extra as click

from ._core.decorators.handle_display_options import handle_display_options
from ._core.legacy_services import LazyServiceDict, LazyServiceProxy
from ._core.ui.display import display_response
from shared_utilities.api_clients.http_client import SyncHTTPClient
from .commands.slack import slack_grp as slack
from .commands.google import google_grp as google
from .commands.shopify import shopify_group as shopify
from .commands.compare_csv import compare_csv_cmd


@click.group(
    name="bars-cli",
    context_settings={
        "allow_interspersed_args": True,
        "ignore_unknown_options": True
    }
)
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
    
    # Initialize lazy service creation
    # Store LazyServiceProxy objects in ctx.meta that create services on first access
    if '_lazy_services_initialized' not in ctx.meta:
        # Store LazyServiceProxy objects for each service
        # These proxies forward attribute access to the actual service (created on first access)
        for service_key, create_func in LazyServiceDict._SERVICE_CREATORS.items():
            ctx.meta[service_key] = LazyServiceProxy(create_func, service_key)
        ctx.meta['_lazy_services_initialized'] = True
    
    # Initialize shared HTTP client for all commands
    # This creates a single client instance that all commands can use
    if 'http_client' not in ctx.meta:
        # Use sync client by default for CLI commands (simpler, works everywhere)
        # Commands can create async clients if needed for parallel operations
        ctx.meta['http_client'] = SyncHTTPClient(
            timeout=30.0
            # Headers are now set automatically by the client using defaults
            # Content-Type: application/json, Accept: application/json, User-Agent: bars-cli/1.0.0
        )
    
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