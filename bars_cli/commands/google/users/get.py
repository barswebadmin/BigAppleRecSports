"""Get user command for Google Directory API."""

import json
from typing import Optional

import click_extra as click

from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.param_types.bars_email_identifier import BARS_EMAIL_IDENTIFIER
from bars_cli._core.utils.json_output import output_json_item, output_json_error
from bars_cli._core.context import get_http_client


@click.command('get', aliases=['get-user'])
@handle_display_options(display=True, exit_on_error=True)
@click.argument('email', type=BARS_EMAIL_IDENTIFIER, required=False)
@click.pass_context
def get_user_cmd(ctx: click.Context, email: Optional[str] = None) -> Optional[dict]:
    """
    Get a user by email address from Google Workspace.
    
    EMAIL: User email address (must end with @bigapplerecsports.com)
    
    Examples:
      bars google users get user@bigapplerecsports.com
      bars --json google users get user@bigapplerecsports.com
    """
    json_output = ctx.obj.get('json_output', False)
    should_display = ctx.obj.get('should_display', True)
    
    if not email:
        email = click.prompt('User Email', type=BARS_EMAIL_IDENTIFIER)
    
    client = get_http_client(ctx)
    endpoint = f'http://localhost:8000/admin/google/users/{email}'
    
    try:
        if should_display and not json_output:
            click.echo(f"🔍 Looking up user: {email}", err=True)
        
        response = client.get(endpoint)
        
        if response.status_code == 200:
            response_data = response.json()
            if should_display:
                if json_output:
                    output_json_item(response_data)
                else:
                    click.echo(f"\n✅ User Found!", err=True)
                    click.echo("=" * 60, err=True)
                    data = response_data.get('data', {})
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
            elif 'error' in error_response:
                error_msg = f"API Error: {error_response['error']}"
            elif 'detail' in error_response:
                detail = error_response['detail']
                if isinstance(detail, dict):
                    if 'message' in detail:
                        error_msg = f"API Error: {detail['message']}"
                    elif 'error' in detail:
                        error_msg = f"API Error: {detail['error']}"
                    else:
                        error_msg = f"API Error: {detail}"
                elif isinstance(detail, str):
                    error_msg = f"API Error: {detail}"
    except json.JSONDecodeError:
        pass
    return error_msg
