"""
Get group command for Google Directory API.
"""

import click
from typing import Optional

from bars_cli._core.param_types.bars_email_identifier import BARS_EMAIL_IDENTIFIER
from backend.modules.integrations.google.directory_client import GoogleDirectoryClient


@click.command('get')
@click.option('--email', type=BARS_EMAIL_IDENTIFIER, required=True, help='Group email address (@bigapplerecsports.com)')
@click.pass_context
def get_group_cmd(ctx: click.Context, email: dict) -> Optional[dict]:
    """
    Get a group by email address from Google Workspace.
    
    Examples:
      bars google directory group get --email team@bigapplerecsports.com
    """
    try:
        group_email = email['email']
        client = GoogleDirectoryClient(subject=ctx.obj.get('google_admin_email'))
        # TODO: Implement get_group method in GoogleDirectoryClient
        click.echo(f"Getting group: {group_email}")
        return None
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()

