"""List Slack users command."""
import json
import sys
from typing import List, Dict, Any, cast, Optional

import click
from slack_sdk.errors import SlackApiError

from backend_services.slack.models.slack_user import SlackUser
from bars_cli._core.decorators.handle_display_options import handle_display_options

from ..utils import handle_slack_api_error
from .._shared.slack_formatters import format_users


def format_users(users: list[SlackUser]) -> str:
    """Format users list for display."""
    if not users:
        return "No users found."
    
    output = []
    output.append(f"\n👥 Slack Users ({len(users)} total):\n")
    
    # Group by status
    # deleted and is_bot are always present in API responses, use direct access
    active_users = [u for u in users if not u.deleted and not u.is_bot]
    bots = [u for u in users if u.is_bot]
    deleted_users = [u for u in users if u.deleted]
    
    if active_users:
        output.append("✅ Active Users:")
        for user in sorted(active_users, key=lambda u: u.real_name or ''):
            name = user.real_name or 'N/A'
            user_id = user.id
            email = user.email or 'N/A'
            title = user.title or ''
            title_display = f" - {title}" if title else ""
            output.append(f"  • {name:<30} ({user_id}) {email}{title_display}")
    
    if bots:
        output.append(f"\n🤖 Bots ({len(bots)}):")
        for bot in sorted(bots, key=lambda u: u.real_name or ''):
            name = bot.real_name or 'N/A'
            bot_id = bot.id
            output.append(f"  • {name:<30} ({bot_id})")
    
    if deleted_users:
        output.append(f"\n🗑️  Deleted Users ({len(deleted_users)}):")
        for user in sorted(deleted_users, key=lambda u: u.real_name or ''):
            name = user.real_name or 'N/A'
            user_id = user.id
            output.append(f"  • {name:<30} ({user_id})")
    
    return '\n'.join(output)


@click.command('list')
@handle_display_options(display=True, exit_on_error=True)
@click.option('--include-bots', is_flag=False, help='Include bot accounts')
@click.option('--include-deleted', is_flag=False, help='Include deleted users')
@click.pass_context
def list_users_cmd(ctx: click.Context, include_bots: bool, include_deleted: bool) -> Optional[List[SlackUser]]:
    """
    List all Slack users visible to the leadership bot.
    
    By default, only shows active human users (no bots, no deleted users).
    
    Examples:
      bars slack user list
      bars slack user list --include-bots
      bars slack user list --include-deleted
      bars --json slack user list
    """
    json_output = ctx.obj.get('json_output', False) if ctx.obj else False
    
    try:
        if not json_output:
            click.echo("🔍 Fetching users...", err=True)
        
        # Get admin_bot from context meta (initialized at slack group level)
        bot = ctx.meta['admin_bot']
        
        # Get all users using leadership bot's client method
        from bars_cli.backend_services.slack.user_lookup import list_all_users
        users_data = list_all_users(bot.client)
        
        if not users_data:
            if not json_output:
                click.echo("❌ No users found", err=True)
            return None
        
        # Convert dicts to SlackUser models for type safety
        # Type assertion: users_data is guaranteed to be List[Dict[str, Any]] at this point
        users_list = cast(List[Dict[str, Any]], users_data)
        users = [SlackUser(**user_dict) for user_dict in users_list]
        
        # Filter based on options
        if not include_bots:
            users = [u for u in users if not u.is_bot]
        
        if not include_deleted:
            users = [u for u in users if not u.deleted]
        
        # Display result (decorator handles whether to display based on flags)
        if json_output:
            click.echo(json.dumps([u.model_dump(exclude_none=True) for u in users], indent=2))
        else:
            click.echo(format_users(users))
        
        return users
    
    except SlackApiError as e:
        # Get token from context if available
        token = None
        try:
            bot = ctx.meta.get('admin_bot')
            if bot and hasattr(bot, 'client') and hasattr(bot.client, 'token'):
                token = bot.client.token
        except Exception:
            pass
        
        handle_slack_api_error(e, json_output=json_output, token=token, api_method='users.list')
        raise
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise

