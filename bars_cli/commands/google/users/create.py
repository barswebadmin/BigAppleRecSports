"""Create user command for Google Directory API."""

import json
from typing import Optional

import click_extra as click

from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.param_types.bars_email_identifier import BARS_EMAIL_IDENTIFIER
from bars_cli._core.utils.json_output import output_json_item, output_json_error
from bars_cli._core.context import get_http_client


@click.command('create', aliases=['create-user'])
@handle_display_options(display=True, exit_on_error=True)
@click.argument('email', type=BARS_EMAIL_IDENTIFIER, required=False)
@click.argument('first_name', required=False)
@click.argument('last_name', required=False)
@click.argument('backup_email', required=False)
@click.option('--password', required=False, help='Initial password')
@click.option('--no-change-password', is_flag=True, default=False)
@click.option('--org-unit-path', required=False)
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
) -> Optional[dict]:
    """
    Create a new user in Google Workspace.
    
    Examples:
      bars google users create user@bigapplerecsports.com "John" "Doe" "backup@example.com"
    """
    json_output = ctx.obj.get('json_output', False)
    should_display = ctx.obj.get('should_display', True)
    
    if not email:
        email = click.prompt('User Email', type=BARS_EMAIL_IDENTIFIER)
    if not first_name:
        first_name = click.prompt('First/Given name', type=str)
    if not last_name:
        last_name = click.prompt('Last/Family name', type=str)
    if not backup_email:
        backup_email = click.prompt('Backup/Recovery email', type=str)
    
    client = get_http_client(ctx)
    endpoint = 'http://localhost:8000/admin/google/users'
    
    payload = {
        'primary_email': email,
        'given_name': first_name,
        'family_name': last_name,
        'recovery_email': backup_email,
        'change_password_at_next_login': not no_change_password
    }
    
    if password:
        payload['password'] = password
    if org_unit_path:
        payload['org_unit_path'] = org_unit_path
    
    try:
        if should_display and not json_output:
            click.echo(f"🔨 Creating user: {email} ({first_name} {last_name})", err=True)
        
        response = client.post(endpoint, json=payload)
        
        if response.status_code in (200, 201):
            response_data = response.json()
            if should_display:
                if json_output:
                    output_json_item(response_data)
                else:
                    click.echo(f"\n✅ User created successfully!", err=True)
                    data = response_data.get('data', {})
                    click.echo("=" * 60, err=True)
                    click.echo(f"{'Email':<15} {data.get('email')}", err=True)
                    click.echo(f"{'Name':<15} {data.get('name')}", err=True)
                    click.echo(f"{'ID':<15} {data.get('id')}", err=True)
                    click.echo("=" * 60, err=True)
            return response_data
        
        error_msg = _extract_error_message(response)
        if json_output:
            output_json_error(error_msg, error_type="APIError")
        else:
            click.echo(f"❌ {error_msg}", err=True)
            click.echo(f"Status Code: {response.status_code}", err=True)
        raise click.ClickException(error_msg)
        
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        
        if json_output:
            output_json_error(error_msg, error_type=error_type)
        else:
            click.echo(f"❌ Unexpected error ({error_type}): {error_msg}", err=True)
        
        raise click.ClickException(error_msg) from e


def _extract_error_message(response) -> str:
    """Extract error message from API response."""
    error_msg = f"API request failed with status {response.status_code}"
    try:
        error_response = response.json()
        if isinstance(error_response, dict):
            if 'message' in error_response:
                error_msg = f"API Error: {error_response['message']}"
            elif 'detail' in error_response:
                detail = error_response['detail']
                if isinstance(detail, dict):
                    if 'message' in detail:
                        error_msg = f"API Error: {detail['message']}"
                    else:
                        error_msg = f"API Error: {detail}"
                elif isinstance(detail, str):
                    error_msg = f"API Error: {detail}"
    except json.JSONDecodeError:
        pass
    return error_msg
