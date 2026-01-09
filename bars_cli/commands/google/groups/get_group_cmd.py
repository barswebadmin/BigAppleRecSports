"""
Get group command for Google Directory API.
"""

import json
from typing import Optional, Dict, Any

import click

from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.param_types.bars_email_identifier import BARS_EMAIL_IDENTIFIER
from bars_cli._core.utils.json_output import output_json_item, output_json_error

from bars_cli.backend_services.google.directory_client import GroupResource


@click.command('get')
@handle_display_options(display=True, exit_on_error=True)
@click.argument('email', type=BARS_EMAIL_IDENTIFIER, required=False)
@click.pass_context
def get_group_cmd(ctx: click.Context, email: Optional[str] = None) -> Optional[GroupResource]:
    """
    Get a group by email address from Google Workspace.
    
    EMAIL: Group email address (must end with @bigapplerecsports.com)
    
    Examples:
      bars google groups get team@bigapplerecsports.com
      bars --json google groups get team@bigapplerecsports.com
    """
    json_output = ctx.obj.get('json_output', False)
    should_display = ctx.obj.get('should_display', True)
    
    # Prompt for email if not provided
    if not email:
        email = BARS_EMAIL_IDENTIFIER.convert(None, None, ctx)
    
    # Client is guaranteed to be available (enforced in google group initialization)
    client = ctx.meta['google_directory_client']
    
    try:
        group_email = email
        
        # Display lookup message
        if should_display and not json_output:
            click.echo(f"🔍 Looking up group: {group_email}", err=True)
        
        # Get group using Google Directory API
        # groups().get() returns a dict, convert to GroupResource
        group_dict = client.service.groups().get(groupKey=group_email).execute()  # type: ignore[attr-defined]
        group = GroupResource(**group_dict)
        
        if not group:
            error_msg = f"No group found for alias: {group_email}"
            if json_output:
                output_json_error(error_msg)
            else:
                click.echo(f"❌ {error_msg}", err=True)
            raise click.ClickException(error_msg)
        
        # Display result
        if should_display:
            if json_output:
                output_json_item(group)
            else:
                _format_group(group)
        
        return group
        
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


def _format_group(group: GroupResource) -> None:
    """Format group data for display.
    
    Args:
        group: GroupResource Pydantic model from Google Directory API
    """
    output = []
    output.append("\n✅ Group Found!")
    output.append("=" * 60)
    
    output.append(f"{'Email':<15} {group.email or 'N/A'}")
    output.append(f"{'Name':<15} {group.name or 'N/A'}")
    output.append(f"{'ID':<15} {group.id or 'N/A'}")
    
    if group.description:
        output.append(f"{'Description':<15} {group.description}")
    
    if group.direct_members_count:
        output.append(f"{'Members':<15} {group.direct_members_count}")
    
    if group.admin_created is not None:
        admin_created = "Yes" if group.admin_created else "No"
        output.append(f"{'Admin Created':<15} {admin_created}")
    
    if group.aliases:
        aliases = group.aliases
        output.append(f"\nAliases ({len(aliases)}):")
        for alias in aliases:
            output.append(f"  • {alias}")
    
    output.append("=" * 60)
    click.echo('\n'.join(output))

