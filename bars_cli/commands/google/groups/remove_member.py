"""
Remove member command for Google Directory API.
"""

from typing import Optional

import click

from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.param_types.bars_email_identifier import BARS_EMAIL_IDENTIFIER
from bars_cli._core.utils.json_output import output_json_error


def _remove_member_impl(
    ctx: click.Context,
    group_email: Optional[str] = None,
    user_email: Optional[str] = None
) -> dict[str, str]:
    """
    GROUP_EMAIL: Group email address (must end with @bigapplerecsports.com)
    USER_EMAIL: User email address (must end with @bigapplerecsports.com)
    
    Examples:
      bars google groups remove_member team@bigapplerecsports.com user@bigapplerecsports.com
      bars google groups remove_user dodgeball joe
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
    from bars_cli._core.context import get_service
    client = get_service(ctx, 'google_api_client')
    
    try:
        # Display action message
        if should_display and not json_output:
            click.echo(f"🔍 Removing {user_email} from group {group_email}...", err=True)
        
        # Remove member using Google Directory API
        client.remove_member_from_group(
            group_email=group_email,
            user_email=user_email
        )
        
        # Display result
        result = {
            "group_email": group_email,
            "user_email": user_email,
            "status": "removed"
        }
        
        if should_display:
            if json_output:
                from bars_cli._core.utils.json_output import output_json_item
                output_json_item(result)
            else:
                output = []
                output.append("\n✅ Member Removed Successfully!")
                output.append("=" * 60)
                output.append(f"{'Group':<15} {group_email}")
                output.append(f"{'User':<15} {user_email}")
                output.append("=" * 60)
                click.echo('\n'.join(output))
        
        return result
        
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


@click.command('remove_member')
@handle_display_options(display=True, exit_on_error=True)
@click.argument('group_email', type=BARS_EMAIL_IDENTIFIER, required=False)
@click.argument('user_email', type=BARS_EMAIL_IDENTIFIER, required=False)
@click.pass_context
def remove_member_cmd(
    ctx: click.Context,
    group_email: Optional[str] = None,
    user_email: Optional[str] = None
) -> dict[str, str]:
    """Remove a user from a Google Workspace group."""
    return _remove_member_impl(ctx, group_email, user_email)


@click.command('remove_user', hidden=True)
@handle_display_options(display=True, exit_on_error=True)
@click.argument('group_email', type=BARS_EMAIL_IDENTIFIER, required=False)
@click.argument('user_email', type=BARS_EMAIL_IDENTIFIER, required=False)
@click.pass_context
def remove_user_cmd(
    ctx: click.Context,
    group_email: Optional[str] = None,
    user_email: Optional[str] = None
) -> dict[str, str]:
    """Remove a user from a Google Workspace group (alias for remove_member)."""
    return _remove_member_impl(ctx, group_email, user_email)

