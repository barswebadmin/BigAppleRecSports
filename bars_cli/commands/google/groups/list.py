"""
List groups command for Google Directory API.
"""

import json

import click_extra as click

from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.utils.json_output import output_json_list, output_json_error
from bars_cli._core.context import get_http_client


@click.command('list')
@handle_display_options(display=True, exit_on_error=True)
@click.pass_context
def list_groups_cmd(ctx: click.Context) -> list[dict]:
    """
    List all groups in Google Workspace.
    
    Examples:
      bars google groups list
      bars --json google groups list
    """
    json_output = ctx.obj.get('json_output', False)
    should_display = ctx.obj.get('should_display', True)
    
    # Get HTTP client from context (BARS API base URL)
    client = get_http_client(ctx)
    
    try:
        # Display lookup message
        if should_display and not json_output:
            click.echo("🔍 Fetching all groups...", err=True)
        
        # API endpoint
        endpoint = 'http://localhost:8000/admin/google/groups'
        
        # Make the API request
        response = client.get(endpoint)
        
        # Handle successful response
        if response.status_code == 200:
            response_data = response.json()
            
            # Extract groups data from response
            if 'data' in response_data:
                groups = response_data['data']
                
                if not groups:
                    if should_display and not json_output:
                        click.echo("ℹ️  No groups found.")
                    return []
                
                # Display result
                if should_display:
                    if json_output:
                        output_json_list(groups)
                    else:
                        _format_groups_list(groups)
                
                return groups
            
            error_msg = "Invalid response format from API"
            if json_output:
                output_json_error(error_msg)
            else:
                click.echo(f"❌ {error_msg}", err=True)
            raise click.ClickException(error_msg)
        
        # Handle error response
        error_msg = _extract_error_message(response)
        if json_output:
            output_json_error(error_msg, error_type="APIError")
        else:
            click.echo(f"❌ {error_msg}", err=True)
            click.echo(f"Status Code: {response.status_code}", err=True)
        raise click.ClickException(error_msg)
        
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


def _format_groups_list(groups: list[dict]) -> None:
    """Format groups list for display.
    
    Args:
        groups: List of group dicts from API
    """
    output = []
    output.append(f"\n✅ Found {len(groups)} group(s)")
    output.append("=" * 80)
    
    for group in groups:
        email = group.get('email', 'N/A')
        name = group.get('name', 'N/A')
        members_count = group.get('direct_members_count', 'N/A')
        output.append(f"{email:<40} {name:<30} ({members_count} members)")
    
    output.append("=" * 80)
    click.echo('\n'.join(output))


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
                if isinstance(error_response['detail'], str):
                    error_msg = f"API Error: {error_response['detail']}"
    except json.JSONDecodeError:
        pass
    return error_msg


