"""
Get group command for Google Directory API.
"""

from typing import Optional, List

import click

from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.param_types.bars_email_identifier import BARS_EMAIL_IDENTIFIER
from bars_cli._core.utils.json_output import output_json_item, output_json_error

from bars_cli.backend_services.google.directory_client import GroupResource
from bars_cli.commands.google._shared.google_formatters import _format_group


@click.command('get')
@handle_display_options(display=True, exit_on_error=True)
@click.argument('email', type=BARS_EMAIL_IDENTIFIER, required=False)
@click.option('--check-member', 'check_member_email', type=BARS_EMAIL_IDENTIFIER, help='Check if a specific user is already a member of this group')
@click.pass_context
def get_group_cmd(
    ctx: click.Context,
    email: Optional[str] = None,
    check_member_email: Optional[str] = None
) -> Optional[GroupResource]:
    """
    Get a group by email address from Google Workspace.
    
    EMAIL: Group email address (must end with @bigapplerecsports.com)
    
    Examples:
      bars google groups get team@bigapplerecsports.com
      bars google groups get team@bigapplerecsports.com --check-member user@bigapplerecsports.com
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
        
        # Get group using client method (includes members)
        result = client.get_group(group_email, include_members=True)
        group = result.group
        members = result.members
        
        if not group:
            error_msg = f"No group found for alias: {group_email}"
            if json_output:
                output_json_error(error_msg)
            else:
                click.echo(f"❌ {error_msg}", err=True)
            raise click.ClickException(error_msg)
        
        # Check if specific member is already in the group
        if check_member_email:
            member_emails = [member.email.lower() for member in members]
            is_member = check_member_email.lower() in member_emails
            
            if should_display:
                if json_output:
                    import json
                    click.echo(json.dumps({
                        "group_email": group_email,
                        "check_member_email": check_member_email,
                        "is_member": is_member,
                        "member_info": next((m for m in members if m.email.lower() == check_member_email.lower()), None)
                    }, indent=2, default=str))
                else:
                    if is_member:
                        member_info = next((m for m in members if m.email.lower() == check_member_email.lower()), None)
                        role = member_info.role if member_info else "MEMBER"
                        click.echo(f"\n✅ {check_member_email} is already a member of {group_email} (Role: {role})")
                    else:
                        click.echo(f"\nℹ️  {check_member_email} is NOT a member of {group_email}")
            return group
        
        # Display result
        if should_display:
            if json_output:
                output_json_item(group)
            else:
                _format_group(group, members)
        
        return group
        
    except click.ClickException: #TODO: move this more central
        raise
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        
        if json_output:
            output_json_error(error_msg, error_type=error_type)
        else:
            click.echo(f"❌ Unexpected error ({error_type}): {error_msg}", err=True)
        
        raise click.ClickException(error_msg) from e



