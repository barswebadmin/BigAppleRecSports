"""
List users command for Google Directory API.
"""

from typing import List

import click

from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.utils.json_output import output_json_list, output_json_error

from bars_cli.backend_services.google.directory_client import UserResource
from bars_cli.commands.google._shared.google_formatters import _format_users_list


@click.command('list')
@handle_display_options(display=True, exit_on_error=True)
@click.pass_context
def list_users_cmd(ctx: click.Context) -> List[UserResource]:
    """
    List all users in Google Workspace.
    
    Examples:
      bars google users list
      bars --json google users list
    """
    json_output = ctx.obj.get('json_output', False)
    should_display = ctx.obj.get('should_display', True)
    
    # Client is guaranteed to be available (enforced in google group initialization)
    client = ctx.meta['google_directory_client']
    
    try:
        # Display lookup message
        if should_display and not json_output:
            click.echo("🔍 Fetching all users...", err=True)
        
        # List all users using Google Directory API
        users: List[UserResource] = client.list_all_users()
        
        if not users:
            if should_display and not json_output:
                click.echo("ℹ️  No users found.")
            return []
        
        # Display result
        if should_display:
            if json_output:
                output_json_list(users)
            else:
                _format_users_list(users)
        
        return users
        
    except click.ClickException:
        raise
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        
        if json_output:
            output_json_error(error_msg, error_type=error_type)
        else:
            click.echo(f"❌ Unexpected error ({error_type}): {error_msg}", err=True)
        
        raise click.ClickException(error_msg) from e



