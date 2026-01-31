"""List users command for Google Directory API."""

import json

import click_extra as click

from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.utils.json_output import output_json_list, output_json_error
from bars_cli._core.context import get_http_client


@click.command('list', aliases=['list-users'])
@handle_display_options(display=True, exit_on_error=True)
@click.option('--max-results', default=500, help='Maximum number of users to return')
@click.pass_context
def list_users_cmd(ctx: click.Context, max_results: int = 500) -> list:
    """
    List all users in Google Workspace.
    
    Examples:
      bars google users list
      bars --json google users list
    """
    json_output = ctx.obj.get('json_output', False)
    should_display = ctx.obj.get('should_display', True)
    
    client = get_http_client(ctx)
    endpoint = f'http://localhost:8000/admin/google/users?max_results={max_results}'
    
    try:
        if should_display and not json_output:
            click.echo("🔍 Fetching all users...", err=True)
        
        response = client.get(endpoint)
        
        if response.status_code == 200:
            response_data = response.json()
            data = response_data.get('data', {})
            users = data.get('users', [])
            
            if not users:
                if should_display and not json_output:
                    click.echo("ℹ️  No users found.", err=True)
                return []
            
            if should_display:
                if json_output:
                    output_json_list(users)
                else:
                    click.echo(f"\n✅ Found {len(users)} users", err=True)
                    click.echo("=" * 60, err=True)
                    for user in users:
                        click.echo(f"• {user.get('email')} - {user.get('name')}", err=True)
                    click.echo("=" * 60, err=True)
            return users
        
        error_msg = _extract_error_message(response)
        if json_output:
            output_json_error(error_msg, error_type="APIError")
        else:
            click.echo(f"❌ {error_msg}", err=True)
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
                if isinstance(detail, str):
                    error_msg = f"API Error: {detail}"
    except json.JSONDecodeError:
        pass
    return error_msg
