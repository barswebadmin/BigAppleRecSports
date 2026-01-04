"""
BARS CLI Main Entry Point.

Uses Click for command-line interface.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

import click

from .commands import slack

_json_output = False
if '--json' in sys.argv:
    _json_output = True
    sys.argv.remove('--json')


def load_environment(env: str = "production"):
    """Load environment variables based on specified environment."""
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)
    
    if env:
        os.environ["ENVIRONMENT"] = env.lower()


@click.group()
@click.version_option(version="1.0.0", prog_name="bars")
@click.option(
    '--env',
    type=click.Choice(['development', 'staging', 'production'], case_sensitive=False),
    default='production',
    help='Environment to use (default: production)'
)
@click.pass_context
def cli(ctx: click.Context, env: str):
    """
    BARS CLI - Command-line interface for BARS operations.
    
    Manage Slack groups, Shopify resources, and leadership provisioning.
    
    Global Options:
      --json    Output as indented JSON
      --env     Environment to use (development, staging, production)
    """
    ctx.ensure_object(dict)
    ctx.obj['json_output'] = _json_output
    ctx.obj['environment'] = env
    
    load_environment(env)


# Register command groups
cli.add_command(slack.slack)


if __name__ == '__main__':
    cli()

