"""
Add member command for Google Directory API.
"""

from typing import Optional, Dict, Any

import click_extra as click
from googleapiclient.errors import HttpError

from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.param_types.bars_email_identifier import BARS_EMAIL_IDENTIFIER
from bars_cli._core.utils.json_output import output_json_item, output_json_error

from backend.modules.integrations.google.models.google_directory_resources import MemberResource
from backend.modules.integrations.google.google_api_client import GoogleApiClient
from backend.modules.integrations.google.services.google_directory_service import GoogleDirectoryService, AddMemberResult
from bars_cli.commands.google._shared.google_formatters import _format_member_added


@click.command('add-member')
@handle_display_options(display=True, exit_on_error=True)
@click.argument('group_email', type=BARS_EMAIL_IDENTIFIER, required=False)
@click.argument('user_email', type=BARS_EMAIL_IDENTIFIER, required=False)
@click.pass_context
def add_member_cmd(
    ctx: click.Context,
    group_email: Optional[str] = None,
    user_email: Optional[str] = None
) -> Optional[MemberResource]:
    """
    Add a user to a Google Workspace group.
    
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
        assert group_email is not None
    
    # Prompt for user_email if not provided
    if not user_email:
        user_email = BARS_EMAIL_IDENTIFIER.convert(None, None, ctx)
        assert user_email is not None

    from bars_cli._core.context import get_service
    client: GoogleApiClient = get_service(ctx, 'google_api_client')
    directory_service: GoogleDirectoryService = client.directory_service
    
    try:
        # Display action message
        if should_display and not json_output:
            click.echo(f"🔍 Adding {user_email} to group {group_email}...", err=True)
        
        # Add member using Google Directory API
        result: AddMemberResult = directory_service.add_member_to_group(
            group_email=group_email,
            user_email=user_email
        )
        
        # Display result
        if should_display:
            if json_output:
                if result.is_warning:
                    import json
                    click.echo(json.dumps({
                        "group_email": group_email,
                        "user_email": user_email,
                        "status": "warning",
                        "warning": result.warning,
                        "member": result.member.model_dump()
                    }, indent=2))
                else:
                    output_json_item(result.member)
            else:
                # group_email and user_email are guaranteed to be str at this point
                assert group_email is not None and user_email is not None
                if result.is_warning:
                    click.echo(f"\n⚠️  {result.warning}", err=True)
                    click.echo("   (No action needed)", err=True)
                else:
                    _format_member_added(result.member, group_email, user_email)
        
        return result.member
        
    except click.ClickException:
        raise
    except HttpError as e:
        # Other HttpErrors - display and raise
        # (409 errors are now handled in the backend service)
        error_type = type(e).__name__
        error_msg = str(e)
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


