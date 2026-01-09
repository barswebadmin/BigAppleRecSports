"""
Get user command for Google Directory API.
"""

from typing import Optional

import click

from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.param_types.bars_email_identifier import BARS_EMAIL_IDENTIFIER
from bars_cli._core.utils.json_output import output_json_item, output_json_error

from bars_cli.backend_services.google.directory_client import UserResource


@click.command('get')
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
    client = ctx.meta['google_directory_client']
    
    try:
        user_email = email
        
        # Display lookup message
        if should_display and not json_output:
            click.echo(f"🔍 Looking up user: {user_email}", err=True)
        
        # Get user using Google Directory API
        # users().get() returns a dict, convert to UserResource
        user_dict = client.service.users().get(userKey=user_email).execute()  # type: ignore[attr-defined]
        user = UserResource(**user_dict)
        
        if not user:
            error_msg = f"No user found for email: {user_email}"
            if json_output:
                output_json_error(error_msg)
            else:
                click.echo(f"❌ {error_msg}", err=True)
            raise click.ClickException(error_msg)
        
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


def _format_user(user: UserResource) -> None:
    """Format user data for display.
    
    Args:
        user: UserResource Pydantic model from Google Directory API
    """
    output = []
    output.append("\n✅ User Found!")
    output.append("=" * 60)
    
    output.append(f"{'Email':<15} {user.primary_email or 'N/A'}")
    
    if user.name:
        full_name = user.name.full_name or 'N/A'
        given_name = user.name.given_name or ''
        family_name = user.name.family_name or ''
        if full_name != 'N/A':
            output.append(f"{'Name':<15} {full_name}")
        elif given_name or family_name:
            output.append(f"{'Name':<15} {given_name} {family_name}".strip())
    
    output.append(f"{'ID':<15} {user.id or 'N/A'}")
    
    if user.suspended is not None:
        suspended = "Yes" if user.suspended else "No"
        output.append(f"{'Suspended':<15} {suspended}")
    
    if user.is_admin is not None:
        is_admin = "Yes" if user.is_admin else "No"
        output.append(f"{'Admin':<15} {is_admin}")
    
    if user.org_unit_path:
        output.append(f"{'Org Unit':<15} {user.org_unit_path}")
    
    if user.aliases:
        aliases = user.aliases
        output.append(f"\nAliases ({len(aliases)}):")
        for alias in aliases:
            output.append(f"  • {alias}")
    
    output.append("=" * 60)
    click.echo('\n'.join(output))

