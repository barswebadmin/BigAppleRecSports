"""
Add member command for Google Directory API.
"""

from typing import Optional, Dict, Any

import click

from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.param_types.bars_email_identifier import BARS_EMAIL_IDENTIFIER
from bars_cli._core.utils.json_output import output_json_item, output_json_error

from bars_cli.backend_services.google.directory_client import MemberResource


def _add_member_impl(
    ctx: click.Context,
    group_email: Optional[str] = None,
    user_email: Optional[str] = None
) -> Optional[MemberResource]:
    """
    GROUP_EMAIL: Group email address (must end with @bigapplerecsports.com)
    USER_EMAIL: User email address (must end with @bigapplerecsports.com)
    
    Examples:
      bars google groups add_member team@bigapplerecsports.com user@bigapplerecsports.com
      bars google groups add_user dodgeball joe
    """
    json_output = ctx.obj.get('json_output', False)
    should_display = ctx.obj.get('should_display', True)
    
    # Prompt for group_email if not provided
    if not group_email:
        group_email = BARS_EMAIL_IDENTIFIER.convert(None, None, ctx)
    
    # Prompt for user_email if not provided
    if not user_email:
        user_email = BARS_EMAIL_IDENTIFIER.convert(None, None, ctx)
    
    # Client is guaranteed to be available (enforced in google group initialization)
    client = ctx.meta['google_directory_client']
    
    try:
        # Display action message
        if should_display and not json_output:
            click.echo(f"🔍 Adding {user_email} to group {group_email}...", err=True)
        
        # Add member using Google Directory API
        member: MemberResource = client.add_member_to_group(
            group_email=group_email,
            user_email=user_email
        )
        
        # Display result
        if should_display:
            if json_output:
                output_json_item(member)
            else:
                _format_member_added(member, group_email, user_email)
        
        return member
        
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


@click.command('add_member')
@handle_display_options(display=True, exit_on_error=True)
@click.argument('group_email', type=BARS_EMAIL_IDENTIFIER, required=False)
@click.argument('user_email', type=BARS_EMAIL_IDENTIFIER, required=False)
@click.pass_context
def add_member_cmd(
    ctx: click.Context,
    group_email: Optional[str] = None,
    user_email: Optional[str] = None
) -> Optional[MemberResource]:
    """Add a user to a Google Workspace group."""
    return _add_member_impl(ctx, group_email, user_email)


@click.command('add_user', hidden=True)
@handle_display_options(display=True, exit_on_error=True)
@click.argument('group_email', type=BARS_EMAIL_IDENTIFIER, required=False)
@click.argument('user_email', type=BARS_EMAIL_IDENTIFIER, required=False)
@click.pass_context
def add_user_cmd(
    ctx: click.Context,
    group_email: Optional[str] = None,
    user_email: Optional[str] = None
) -> Optional[MemberResource]:
    """Add a user to a Google Workspace group (alias for add_member)."""
    return _add_member_impl(ctx, group_email, user_email)


def _format_member_added(member: MemberResource, group_email: str, user_email: str) -> None:
    """Format member addition result for display.
    
    Args:
        member: MemberResource Pydantic model from Google Directory API
        group_email: Group email address
        user_email: User email address that was added
    """
    output = []
    output.append("\n✅ Member Added Successfully!")
    output.append("=" * 60)
    output.append(f"{'Group':<15} {group_email}")
    output.append(f"{'User':<15} {user_email}")
    output.append(f"{'Role':<15} {member.role or 'MEMBER'}")
    output.append(f"{'Member ID':<15} {member.id or 'N/A'}")
    output.append("=" * 60)
    click.echo('\n'.join(output))

