"""Get Slack user details command."""
from typing import Dict, Any, Optional

import click

from bars_cli._core.param_types import SLACK_USER_IDENTIFIER
from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli.backend_services.slack.models.slack_user import SlackUser
from bars_cli.commands.slack._shared.command_helpers import handle_slack_get_command




def format_user(user: SlackUser) -> str:
    """Format user data for display."""
    name = user.real_name or 'N/A'
    email = user.email or 'N/A'
    display = user.display_name or 'N/A'
    user_id = user.id
    deleted = user.deleted  # Always present in API response
    title = user.title
    phone = user.phone
    is_admin = user.is_admin or False  # Optional, may be None
    is_owner = user.is_owner or False  # Optional, may be None
    timezone = user.tz_label
    
    output = []
    output.append("\n👤 User Details:\n")
    output.append(f"  Name: {name}")
    output.append(f"  Email: {email}")
    output.append(f"  Display: {display}")
    output.append(f"  User ID: {user_id}")
    
    if deleted:
        output.append("  ⚠️  Status: DELETED")
    
    if title:
        output.append(f"  Title: {title}")
    
    if phone:
        output.append(f"  Phone: {phone}")
    
    if is_admin:
        output.append("  Role: Workspace Admin")
    elif is_owner:
        output.append("  Role: Workspace Owner")
    else:
        output.append("  Role: Member")
    
    if timezone:
        output.append(f"  Timezone: {timezone}")
    
    return '\n'.join(output)


def _extract_user_identifier(identifier: Dict[str, Any]) -> str:
    """Extract user identifier value from dict."""
    return identifier.get("email") or identifier.get("user_id") or identifier.get("identifier", "")


def _format_user_for_display(user_data: Dict[str, Any]) -> str:
    """Format user data for display, handling both dict and SlackUser model."""
    # Convert to SlackUser model if it's a dict
    if isinstance(user_data, dict):
        try:
            user = SlackUser(**user_data)
        except Exception:
            # Fallback to dict if model creation fails
            user = user_data
    else:
        user = user_data
    
    return format_user(user)


@click.command('get')
@handle_display_options(display=True, exit_on_error=True)
@click.argument('identifier', type=SLACK_USER_IDENTIFIER, required=True)
@click.pass_context
def get_user_cmd(ctx: click.Context, identifier: Dict[str, Any]) -> Optional[SlackUser]:
    """
    Get Slack user details by email or ID.
    
    Uses the leadership bot's SlackClient instance.
    
    IDENTIFIER: User's email address or Slack user ID (e.g., 'U01ABC123').
    
    Examples:
      bars slack user get stephen@bigapplerecsports.com
      bars slack user get U03LZKQSHEU
      bars --json slack user get stephen@example.com
    """
    from bars_cli.commands.slack._shared.command_helpers import get_admin_bot
    
    bot = get_admin_bot(ctx)
    
    # Convert result to SlackUser model if it's a dict
    result = handle_slack_get_command(
        ctx=ctx,
        identifier=identifier,
        lookup_method=bot.lookup_user,
        format_func=_format_user_for_display,
        entity_name="user",
        identifier_required_msg="User identifier is required (email or user ID)",
        extract_identifier_value=_extract_user_identifier
    )
    
    # Convert dict to SlackUser model for type safety
    if result and isinstance(result, dict):
        try:
            return SlackUser(**result)  # type: ignore[return-value]
        except Exception:
            # Return dict if model creation fails (shouldn't happen, but handle gracefully)
            return None  # type: ignore[return-value]
    
    return result  # type: ignore[return-value]

