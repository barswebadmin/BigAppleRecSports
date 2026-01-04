"""
BARS CLI Main Entry Point.

Uses Click for command-line interface.
"""
import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

import click

from .commands import slack

_json_output = False
if '--json' in sys.argv:
    _json_output = True
    sys.argv.remove('--json')


@click.group()
@click.version_option(version="1.0.0", prog_name="bars")
@click.pass_context
def cli(ctx: click.Context):
    """
    BARS CLI - Command-line interface for BARS operations.
    
    Manage Slack groups, Shopify resources, and leadership provisioning.
    
    Global Options:
      --json    Output as indented JSON
    """
    ctx.ensure_object(dict)
    ctx.obj['json_output'] = _json_output


# Register command groups
cli.add_command(slack.slack)


if __name__ == '__main__':
    cli()

