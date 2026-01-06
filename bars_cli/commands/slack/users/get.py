"""Get Slack user details command."""
import json
import sys
from typing import Dict, Any, Optional

import click
from slack_sdk.errors import SlackApiError

from bars_cli._core.param_types import SLACK_USER_IDENTIFIER
from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli.models.slack_user import SlackUser

from ..utils import handle_slack_api_error




def format_user(user: SlackUser) -> str:
    """Format user data for display."""
    profile = user.profile
    name = user.real_name or 'N/A'
    email = profile.email or 'N/A'
    display = profile.display_name or 'N/A'
    user_id = user.id
    deleted = user.deleted  # Always present in API response
    title = profile.title
    phone = profile.phone
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


@click.command('get')
@handle_display_options(display=True, exit_on_error=True)
@click.argument('identifier', type=SLACK_USER_IDENTIFIER, required=True)
@click.pass_context
def get_user_cmd(ctx: click.Context, identifier: dict) -> Optional[SlackUser]:
    """
    Get Slack user details by email or ID.
    
    Uses the leadership bot's SlackClient instance.
    
    IDENTIFIER: User's email address or Slack user ID (e.g., 'U01ABC123').
    
    Examples:
      bars slack user get stephen@bigapplerecsports.com
      bars slack user get U03LZKQSHEU
      bars --json slack user get stephen@example.com
    """
    json_output = ctx.obj.get('json_output', False) if ctx.obj else False
    display_override = ctx.obj.get('display_override', True) if ctx.obj else True
    should_display = display_override if display_override is not None else True
    
    try:
        # Get leadership_bot from context meta (initialized at slack group level)
        bot = ctx.meta['leadership_bot']
        
        # Get lookup value
        lookup_value = identifier.get("email") or identifier.get("user_id")
        if not lookup_value:
            error_msg = "Invalid identifier: must provide either email or user_id"
            if should_display:
                if json_output:
                    click.echo(json.dumps({"error": error_msg}, indent=2))
                else:
                    click.echo(f"❌ {error_msg}", err=True)
            raise ValueError(error_msg)
        
        if should_display and not json_output:
            click.echo(f"🔍 Looking up: {lookup_value}", err=True)
        
        # Use leadership_bot's lookup_user method (accepts string directly)
        try:
            user_data = bot.lookup_user(lookup_value)
        except Exception as e:
            error_msg = f"Failed to lookup user '{lookup_value}': {type(e).__name__}: {e}"
            if should_display:
                if json_output:
                    click.echo(json.dumps({"error": error_msg}, indent=2))
                else:
                    click.echo(f"❌ {error_msg}", err=True)
                    import traceback
                    click.echo(traceback.format_exc(), err=True)
            raise
        
        if not user_data:
            error_msg = f"User not found: {lookup_value}"
            if should_display:
                if json_output:
                    click.echo(json.dumps({"error": error_msg}, indent=2))
                else:
                    click.echo(f"❌ {error_msg}", err=True)
                    click.echo(f"💡 Try checking the email/ID spelling or use 'bars slack user list' to see all users", err=True)
            raise click.ClickException(error_msg)
        
        # Convert dict to SlackUser model for type safety
        try:
            user = SlackUser(**user_data)
        except Exception as e:
            error_msg = f"Failed to create user model: {type(e).__name__}: {e}"
            if should_display:
                if json_output:
                    click.echo(json.dumps({"error": error_msg, "data_keys": list(user_data.keys())[:10]}, indent=2))
                else:
                    click.echo(f"❌ {error_msg}", err=True)
                    click.echo(f"💡 Received data with keys: {', '.join(list(user_data.keys())[:10])}", err=True)
            raise
        
        # Display result only if display_override is True
        if should_display:
            if json_output:
                click.echo(json.dumps(user.model_dump(exclude_none=True), indent=2))
            else:
                click.echo(format_user(user))
        
        return user
    
    except SlackApiError as e:
        # Get token from context if available
        token = None
        try:
            bot = ctx.meta.get('leadership_bot')
            if bot and hasattr(bot, 'client') and hasattr(bot.client, 'token'):
                token = bot.client.token
        except Exception:
            pass
        
        # Don't call sys.exit here - let the decorator handle it based on exit_override
        handle_slack_api_error(e, json_output=json_output, token=token, api_method='users.info')
        # Re-raise so decorator can handle exit based on exit_override
        raise
    except (RuntimeError, ValueError, click.ClickException, KeyError):
        # These exceptions are already handled or have good error messages - just re-raise
        # Decorator will handle exit based on exit_override
        raise
    except Exception as e:
        # Show full traceback for unexpected errors
        error_type = type(e).__name__
        error_msg = str(e)
        if should_display:
            if json_output:
                click.echo(json.dumps({"error": error_msg, "type": error_type}, indent=2))
            else:
                click.echo(f"❌ Unexpected error ({error_type}): {error_msg}", err=True)
                click.echo(f"\n💡 Full traceback:", err=True)
                import traceback
                click.echo(traceback.format_exc(), err=True)
        # Re-raise so decorator can handle exit based on exit_override
        raise

