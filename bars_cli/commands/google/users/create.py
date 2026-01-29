"""
Create user command for Google Directory API.
"""

from typing import Optional
import time

import click_extra as click

from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.param_types.bars_email_identifier import BARS_EMAIL_IDENTIFIER
from bars_cli._core.utils.json_output import output_json_item, output_json_error

from bars_cli.backend_services.google.models.google_directory_resources import UserResource
from bars_cli.commands.google._shared.google_formatters import _format_user


@click.command('create', aliases=['create-user'])
@handle_display_options(display=True, exit_on_error=True)
@click.argument('email', type=BARS_EMAIL_IDENTIFIER, required=False)
@click.argument('first_name', required=False)
@click.argument('last_name', required=False)
@click.argument('backup_email', required=False)
@click.option('--password', required=False, help='Initial password (user will be required to change on first login if not provided)')
@click.option('--no-change-password', 'no_change_password', is_flag=True, default=False, help='Do not require password change on next login')
@click.option('--org-unit-path', 'org_unit_path', required=False, help='Organizational unit path (e.g., "/Staff" or "/Students")')
@click.pass_context
def create_user_cmd(
    ctx: click.Context,
    email: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    backup_email: Optional[str] = None,
    password: Optional[str] = None,
    no_change_password: bool = False,
    org_unit_path: Optional[str] = None
) -> Optional[UserResource]:
    """
    Create a new user in Google Workspace.
    
    EMAIL: User email address (must end with @bigapplerecsports.com)
    
    FIRST_NAME: User's first/given name
    
    LAST_NAME: User's last/family name
    
    BACKUP_EMAIL: Recovery/backup email address for the user
    
    Examples:
      bars google users create user@bigapplerecsports.com "John" "Doe" "backup@example.com"
      bars google users create user@bigapplerecsports.com "Jane" "Smith" "backup@example.com" --password "TempPass123!"
      bars --json google users create user@bigapplerecsports.com "Bob" "Jones" "backup@example.com"
    """
    json_output = ctx.obj.get('json_output', False)
    should_display = ctx.obj.get('should_display', True)
    
    # Prompt for email if not provided
    if not email:
        email = BARS_EMAIL_IDENTIFIER.convert(None, None, ctx)
    
    # Prompt for first_name if not provided
    if not first_name:
        first_name = click.prompt('First/Given name', type=str)
    
    # Prompt for last_name if not provided
    if not last_name:
        last_name = click.prompt('Last/Family name', type=str)
    
    # Prompt for backup_email if not provided
    if not backup_email:
        backup_email = click.prompt('Backup/Recovery email', type=str)
    
    # Prompt for password if not provided
    if not password:
        password = click.prompt('Password', type=str, default='', show_default=False, hide_input=True)
        if not password:
            password = None  # Convert empty string to None
            if should_display and not json_output:
                click.echo("⚠️  No password provided - user will be required to set password on first login", err=True)
    
    # Client is guaranteed to be available (enforced in google group initialization)
    start_time = time.time()
    from bars_cli._core.context import get_service
    client = get_service(ctx, 'google_api_client')
    client_init_time = time.time() - start_time
    if should_display and not json_output:
        click.echo(f"[DEBUG] Client initialization took {client_init_time:.2f}s", err=True)
    
    try:
        user_email = email
        
        # Display creation message
        if should_display and not json_output:
            click.echo(f"🔨 Creating user: {user_email} ({first_name} {last_name})", err=True)
        
        # Create user using directory client method
        api_start_time = time.time()
        user = client.create_user(
            primary_email=user_email,
            given_name=first_name,
            family_name=last_name,
            recovery_email=backup_email,
            password=password,
            change_password_at_next_login=not no_change_password,
            org_unit_path=org_unit_path
        )
        api_time = time.time() - api_start_time
        if should_display and not json_output:
            click.echo(f"[DEBUG] API call took {api_time:.2f}s", err=True)
        
        # Display result
        if should_display:
            if json_output:
                output_json_item(user)
            else:
                click.echo(f"\n✅ User created successfully!", err=True)
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
