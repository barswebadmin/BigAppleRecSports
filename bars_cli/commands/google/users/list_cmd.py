"""
List users command for Google Directory API.
"""

from typing import List

import click

from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.utils.json_output import output_json_list, output_json_error

from bars_cli.backend_services.google.directory_client import UserResource


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


def _format_users_list(users: List[UserResource]) -> None:
    """Format users list for display.
    
    Args:
        users: List of UserResource Pydantic models from Google Directory API
    """
    output = []
    output.append(f"\n✅ Found {len(users)} user(s)")
    output.append("=" * 80)
    
    for user in users:
        email = user.primary_email or 'N/A'
        full_name = user.name.full_name if user.name and user.name.full_name else 'N/A'
        suspended = "Suspended" if user.suspended else "Active"
        is_admin = "Admin" if user.is_admin else ""
        admin_label = f" [{is_admin}]" if is_admin else ""
        
        output.append(f"{email:<40} {full_name:<30} {suspended}{admin_label}")
    
    output.append("=" * 80)
    click.echo('\n'.join(output))

