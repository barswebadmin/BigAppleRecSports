"""
Get group command for Google Directory API.
"""

import json
from typing import Optional

import click_extra as click

from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.param_types.bars_email_identifier import BARS_EMAIL_IDENTIFIER
from bars_cli._core.utils.json_output import output_json_item, output_json_error
from bars_cli._core.context import get_http_client


@click.command('get')
@handle_display_options(display=True, exit_on_error=True)
@click.argument('email', type=BARS_EMAIL_IDENTIFIER, required=False)
@click.pass_context
def get_group_cmd(
    ctx: click.Context,
    email: Optional[str] = None
) -> Optional[dict]:
    """
    Get a group by email address from Google Workspace.

    EMAIL: Group email address (must end with @bigapplerecsports.com)

    Examples:
      bars google groups get team@bigapplerecsports.com
      bars --json google groups get team@bigapplerecsports.com
    """
    json_output = ctx.obj.get('json_output', False)
    should_display = ctx.obj.get('should_display', True)

    # Prompt for email if not provided
    if not email:
        email = BARS_EMAIL_IDENTIFIER.convert(None, None, ctx)

    # Get HTTP client from context (BARS API base URL)
    client = get_http_client(ctx)

    try:
        group_email = email

        # Display lookup message
        if should_display and not json_output:
            click.echo(f"🔍 Looking up group: {group_email}", err=True)

        # API endpoint - use path parameter instead of query params
        endpoint = f'http://localhost:8000/admin/google/groups/{group_email}'

        # Make the API request
        response = client.get(endpoint)

        # Handle successful response
        if response.status_code == 200:
            response_data = response.json()

            # Extract group data from response
            # Response structure: {success: true, data: {id, email, name, members: [...]}, message, timestamp}
            if 'data' in response_data:
                group_data = response_data['data']
                
                if not group_data:
                    error_msg = f"No group found for email: {group_email}"
                    if json_output:
                        output_json_error(error_msg)
                    else:
                        click.echo(f"❌ {error_msg}", err=True)
                    raise click.ClickException(error_msg)

                # Extract members from group data
                members_data = group_data.get('members', [])

                # Display result
                if should_display:
                    if json_output:
                        output_json_item(group_data)
                    else:
                        _format_group(group_data, members_data)

                return group_data

            error_msg = "Invalid response format from API"
            if json_output:
                output_json_error(error_msg)
            else:
                click.echo(f"❌ {error_msg}", err=True)
            raise click.ClickException(error_msg)

        # Handle error response
        if response.status_code == 404:
            error_msg = f"Group not found: {group_email}"
            if json_output:
                output_json_error(error_msg, error_type="NotFound")
            else:
                click.echo(f"❌ {error_msg}", err=True)
            raise click.ClickException(error_msg)

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


def _format_group(group: dict, members: list[dict]) -> None:
    """Format group data for display.
    
    Args:
        group: Group data dict from API
        members: List of member dicts
    """
    output = []
    output.append("\n✅ Group Found!")
    output.append("=" * 60)
    
    output.append(f"{'Alias Email':<15} {group.get('email', 'N/A')}")
    output.append(f"{'Name':<15} {group.get('name', 'N/A')}")
    output.append(f"{'ID':<15} {group.get('id', 'N/A')}")
    
    if group.get('description'):
        output.append(f"{'Description':<15} {group['description']}")
    
    if members:
        output.append(f"\nMembers ({len(members)}):")
        for member in members:
            role = member.get('role', 'MEMBER')
            email = member.get('email', 'N/A')
            output.append(f"  • {email} ({role})")
    
    if group.get('aliases'):
        aliases = group['aliases']
        output.append(f"\nAliases ({len(aliases)}):")
        for alias in aliases:
            output.append(f"  • {alias}")
    
    output.append("=" * 60)
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