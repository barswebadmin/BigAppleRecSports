"""
Add member command for Google Directory API.
"""

from typing import Optional, Dict, Any

import click
from googleapiclient.errors import HttpError

from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.param_types.bars_email_identifier import BARS_EMAIL_IDENTIFIER
from bars_cli._core.utils.json_output import output_json_item, output_json_error

from bars_cli.backend_services.google.directory_client import MemberResource
from bars_cli.commands.google._shared.google_formatters import _format_member_added


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
                # group_email and user_email are guaranteed to be str at this point
                assert group_email is not None and user_email is not None
                _format_member_added(member, group_email, user_email)
        
        return member
        
    except click.ClickException:
        raise
    except HttpError as e:
        # Check if this is a 409 Conflict error (member already exists)
        error_msg = str(e)
        is_duplicate = False
        
        # Check for HttpError with status 409
        if hasattr(e, 'resp') and hasattr(e.resp, 'status'):
            if e.resp.status == 409:
                is_duplicate = True
        elif '409' in error_msg or 'duplicate' in error_msg.lower() or 'already exists' in error_msg.lower():
            is_duplicate = True
        
        if is_duplicate:
            # Member already exists - handle gracefully
            if should_display:
                if json_output:
                    import json
                    click.echo(json.dumps({
                        "group_email": group_email,
                        "user_email": user_email,
                        "status": "already_member",
                        "message": f"{user_email} is already a member of {group_email}"
                    }, indent=2))
                else:
                    click.echo(f"\nℹ️  {user_email} is already a member of {group_email}")
                    click.echo("   (No action needed)")
            
            # Try to get the existing member info
            if group_email and user_email:
                try:
                    members = client.list_group_members(group_email)
                    user_email_lower = user_email.lower()
                    existing_member = next((m for m in members if m.email.lower() == user_email_lower), None)
                    if existing_member:
                        return existing_member
                except Exception:
                    pass
            
            # Return None to indicate member already exists (not an error)
            return None
        else:
            # Other HttpErrors - display and raise
            error_type = type(e).__name__
            if json_output:
                output_json_error(error_msg, error_type=error_type)
            else:
                click.echo(f"❌ Unexpected error ({error_type}): {error_msg}", err=True)
            
            raise click.ClickException(error_msg) from e
    except Exception as e:
        # Other non-HttpError exceptions
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


