"""Remove member command for Google Directory API."""

import json
from typing import Optional

import click_extra as click

from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.param_types.bars_email_identifier import BARS_EMAIL_IDENTIFIER
from bars_cli._core.utils.json_output import output_json_item, output_json_error
from bars_cli._core.context import get_http_client


@click.command('remove-member', aliases=['remove-user'])
@handle_display_options(display=True, exit_on_error=True)
@click.argument('group_email', type=BARS_EMAIL_IDENTIFIER, required=False)
@click.argument('user_email', type=BARS_EMAIL_IDENTIFIER, required=False)
@click.pass_context
def remove_member_cmd(
    ctx: click.Context,
    group_email: Optional[str] = None,
    user_email: Optional[str] = None
) -> Optional[dict]:
    """
    Remove a user from a Google Workspace group.

    GROUP_EMAIL: Group email address (will append @bigapplerecsports.com if not present)
    USER_EMAIL: User email address (will append @bigapplerecsports.com if not present)

    Examples:
        bars google groups remove-member team-leads user
        bars google groups remove-user dodgeball joe
        bars --json google groups remove-member team-leads user
    """
    json_output = ctx.obj.get('json_output', False)
    should_display = ctx.obj.get('should_display', True)

    # Prompt for group_email if not provided
    if not group_email:
        group_email = click.prompt('Group Email', type=BARS_EMAIL_IDENTIFIER)

    # Prompt for user_email if not provided
    if not user_email:
        user_email = click.prompt('User Email', type=BARS_EMAIL_IDENTIFIER)

    # Append domain if not present
    if '@' not in group_email:
        group_email = f"{group_email}@bigapplerecsports.com"
    if '@' not in user_email:
        user_email = f"{user_email}@bigapplerecsports.com"

    # Get HTTP client from context (BARS API base URL)
    client = get_http_client(ctx)

    # API endpoint
    endpoint = f'http://localhost:8000/admin/google/groups/{group_email}/members/{user_email}'

    try:
        # Display action message
        if should_display and not json_output:
            click.echo(f"➖ Removing {user_email} from group {group_email}...", err=True)

        # Make the API request
        response = client.delete(endpoint)

        # Handle successful response
        if response.status_code in (200, 204):
            response_data = response.json() if response.status_code == 200 else {
                "group_email": group_email,
                "member_email": user_email,
                "message": "Member removed from group successfully"
            }
            
            if should_display:
                if json_output:
                    output_json_item(response_data)
                else:
                    _display_success_message(group_email, user_email, response_data)
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
    group_email: str,
    user_email: str,
    response_data: dict) -> None:
    """Display success message for member removal."""
    message = response_data.get('message', 'Member removed successfully')
    
    click.echo(f"\n✅ {message}", err=True)
    click.echo("=" * 60, err=True)
    click.echo(f"{'Group':<15} {group_email}", err=True)
    click.echo(f"{'Member':<15} {user_email}", err=True)
    click.echo("=" * 60, err=True)


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
