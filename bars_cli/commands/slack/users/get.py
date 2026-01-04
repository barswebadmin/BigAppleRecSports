"""Get Slack user details command."""
import sys
import json

import click
from slack_sdk.errors import SlackApiError

sys.path.insert(0, 'backend')
from modules.integrations.slack.services.user_lookup_service import UserLookupService

sys.path.insert(0, '.')
from bars_cli._core.param_types import SLACK_USER_IDENTIFIER

from ..utils import (
    get_bot_token,
    handle_slack_api_error
)


def format_user(user: dict) -> str:
    """Format user data for display."""
    profile = user.get('profile', {})
    name = user.get('real_name', 'N/A')
    email = profile.get('email', 'N/A')
    display = profile.get('display_name', 'N/A')
    user_id = user.get('id', 'N/A')
    deleted = user.get('deleted', False)
    
    output = []
    output.append("\n👤 User Details:\n")
    output.append(f"  Name: {name}")
    output.append(f"  Email: {email}")
    output.append(f"  Display: {display}")
    output.append(f"  User ID: {user_id}")
    
    if deleted:
        output.append("  ⚠️  Status: DELETED")
    
    title = profile.get('title')
    if title:
        output.append(f"  Title: {title}")
    
    phone = profile.get('phone')
    if phone:
        output.append(f"  Phone: {phone}")
    
    if user.get('is_admin'):
        output.append("  Role: Workspace Admin")
    elif user.get('is_owner'):
        output.append("  Role: Workspace Owner")
    else:
        output.append("  Role: Member")
    
    timezone = user.get('tz_label')
    if timezone:
        output.append(f"  Timezone: {timezone}")
    
    return '\n'.join(output)


@click.command('get')
@click.argument('identifier', type=SLACK_USER_IDENTIFIER, required=False)
@click.option('--bot', default='leadership', help='Which bot to use (default: leadership)')
@click.pass_context
def get_user_cmd(ctx: click.Context, identifier: dict, bot: str):
    """
    Get Slack user details by email or ID.
    
    IDENTIFIER: User's email address or Slack user ID (e.g., 'U01ABC123').
                If omitted, will prompt for input.
    
    Examples:
      bars slack user get stephen@bigapplerecsports.com
      bars slack user get U03LZKQSHEU
      bars --json slack user get stephen@example.com
    """
    json_output = ctx.obj.get('json_output', False) if ctx.obj else False
    
    try:
        token = get_bot_token(bot)
        service = UserLookupService(token)
        
        # identifier is a dict with either {"email": str} or {"user_id": str}
        user_data = None
        if "email" in identifier:
            email = identifier["email"]
            if not json_output:
                click.echo(f"🔍 Looking up email: {email}", err=True)
            user_data = service.lookup_user_by_email(email)
        elif "user_id" in identifier:
            user_id = identifier["user_id"]
            if not json_output:
                click.echo(f"🔍 Looking up user ID: {user_id}", err=True)
            user_data = service.lookup_user_by_id(user_id)
        
        # Display result
        if not user_data:
            lookup_value = identifier.get("email") or identifier.get("user_id")
            if not json_output:
                click.echo(f"❌ User not found: {lookup_value}", err=True)
            sys.exit(1)
        
        if json_output:
            click.echo(json.dumps(user_data, indent=2))
        else:
            click.echo(format_user(user_data))
    
    except SlackApiError as e:
        handle_slack_api_error(e, json_output)
        sys.exit(1)
    except click.BadParameter as e:
        click.echo(f"❌ {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)

