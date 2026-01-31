"""Create group command for Google Directory API."""

import json
from typing import Optional

import click_extra as click

from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.utils.json_output import output_json_item, output_json_error
from bars_cli._core.context import get_http_client
from bars_cli._core.prompts import prompt_for_missing_options


@click.command('create-group', aliases=['create'])
@handle_display_options(display=True, exit_on_error=True)
@click.argument('email', required=False)
@click.argument('name', required=False)
@click.argument('description', required=False)
@click.pass_context
def create_group_cmd(
    ctx: click.Context,
    email: Optional[str] = None,
    name: Optional[str] = None,
    description: Optional[str] = None
) -> Optional[dict]:
    """
    Create a new Google Workspace group.

    EMAIL: Group email address (will append @bigapplerecsports.com if not present)
    NAME: Human-readable name for the group (1-75 characters)
    DESCRIPTION: Optional description for the group (max 300 characters)

    All arguments are optional. If not provided, you'll be prompted for required values.
    Arguments with spaces must be quoted.

    Examples:
        bars google groups create team-leads "Team Leaders" "Leadership coordination"
        bars google groups create team-leads "Team Leaders"
        bars google groups create team-leads
        bars --json google groups create team-leads "Team Leaders" "Leadership team"
    """
    json_output = ctx.obj.get('json_output', False)
    should_display = ctx.obj.get('should_display', True)

    # Define the options we need to collect
    options = [
        {
            'value': email,
            'display_value': 'Group Email',
            'required': True,
            'key': 'email'
        },
        {
            'value': name,
            'display_value': 'Group Name',
            'required': True,
            'key': 'name'
        },
        {
            'value': description,
            'display_value': 'Description (optional)',
            'required': False,
            'key': 'description'
        }
    ]

    # Prompt for missing required options
    try:
        collected_values = prompt_for_missing_options(options, ctx)
        email = collected_values['email']
        name = collected_values['name']
        description = collected_values.get('description')
    
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        
        if json_output:
            output_json_error(error_msg, error_type=error_type)
        else:
            click.echo(f"❌ Unexpected error ({error_type}): {error_msg}", err=True)
        
        raise click.ClickException(error_msg) from e

    # Append domain if not present
    if '@' not in email:
        email = f"{email}@bigapplerecsports.com"

    # Get HTTP client from context (BARS API base URL)
    client = get_http_client(ctx)

    # Prepare API request payload
    payload = {
        'email': email,
        'name': name
    }
    if description:
        payload['description'] = description

    # API endpoint
    endpoint = 'http://localhost:8000/admin/google/groups'

    try:
        # Make the API request
        response = client.post(endpoint, json=payload)

        # Handle successful response
        if response.status_code in (200, 201):
            response_data = response.json()
            if should_display:
                if json_output:
                    output_json_item(response_data)
                else:
                    _display_success_message(email, name, description, response_data)
            return response_data

        # Handle error response
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


def _display_success_message(
    email: str,
    name: str,
    description: Optional[str],
    response_data: dict) -> None:
    """Display success message for group creation."""
    click.echo("\n✅ Group Created Successfully!", err=True)
    click.echo("=" * 60, err=True)
    click.echo(f"{'Email':<15} {email}", err=True)
    click.echo(f"{'Name':<15} {name}", err=True)
    if description:
        click.echo(f"{'Description':<15} {description}", err=True)

    # Display additional info from response if available
    if 'data' in response_data and isinstance(response_data['data'], dict):
        data = response_data['data']
        if 'id' in data:
            click.echo(f"{'Group ID':<15} {data['id']}", err=True)
        if 'admin_created' in data:
            admin_created = "Yes" if data['admin_created'] else "No"
            click.echo(f"{'Admin Created':<15} {admin_created}", err=True)

    click.echo("=" * 60, err=True)
    click.echo(f"\n🎉 Group {email} is ready to use!", err=True)


def _extract_error_message(response) -> str:
    """Extract error message from API response."""
    error_msg = f"API request failed with status {response.status_code}"
    try:
        error_response = response.json()
        if isinstance(error_response, dict):
            # Check top-level fields first
            if 'message' in error_response:
                error_msg = f"API Error: {error_response['message']}"
            elif 'error' in error_response:
                error_msg = f"API Error: {error_response['error']}"
            elif 'detail' in error_response:
                detail = error_response['detail']
                # If detail is a dict (from ValidationAPIError), extract message
                if isinstance(detail, dict):
                    if 'message' in detail:
                        error_msg = f"API Error: {detail['message']}"
                    elif 'error' in detail:
                        error_msg = f"API Error: {detail['error']}"
                    else:
                        error_msg = f"API Error: {detail}"
                # If detail is a string
                elif isinstance(detail, str):
                    error_msg = f"API Error: {detail}"
    except json.JSONDecodeError:
        pass
    return error_msg
