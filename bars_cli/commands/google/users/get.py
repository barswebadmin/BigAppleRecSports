"""
Get user command for Google Directory API.
"""

from typing import Optional

import click_extra as click

from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.param_types.bars_email_identifier import BARS_EMAIL_IDENTIFIER
from bars_cli._core.utils.json_output import output_json_item, output_json_error

from bars_cli.backend_services.google.models.google_directory_resources import UserResource
from bars_cli.commands.google._shared.google_formatters import _format_user


@click.command('get', aliases=['get-user'])
@handle_display_options(display=True, exit_on_error=True)
@click.argument('email', type=BARS_EMAIL_IDENTIFIER, required=False)
@click.pass_context
def get_user_cmd(ctx: click.Context, email: Optional[str] = None) -> Optional[UserResource]:
    """
    Get a user by email address from Google Workspace.
    
    EMAIL: User email address (must end with @bigapplerecsports.com)
    
    Examples:
      bars google users get user@bigapplerecsports.com
      bars --json google users get user@bigapplerecsports.com
    """
    json_output = ctx.obj.get('json_output', False)
    should_display = ctx.obj.get('should_display', True)
    
    # Prompt for email if not provided
    if not email:
        email = BARS_EMAIL_IDENTIFIER.convert(None, None, ctx)
    
    # Client is guaranteed to be available (enforced in google group initialization)
    from bars_cli._core.context import get_service
    client = get_service(ctx, 'google_api_client')
    
    try:
        user_email = email
        
        # Display lookup message
        if should_display and not json_output:
            click.echo(f"🔍 Looking up user: {user_email}", err=True)
        
        # Get user using directory client method
        user = client.get_user(user_email)
        
        # Display result
        if should_display:
            if json_output:
                output_json_item(user)
            else:
                _format_user(user)
        
        return user
        
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


