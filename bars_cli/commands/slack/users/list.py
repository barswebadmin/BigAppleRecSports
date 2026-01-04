"""List Slack users command."""
import sys
import json

import click
from slack_sdk.errors import SlackApiError

sys.path.insert(0, 'backend')

from modules.integrations.slack.services.user_lookup_service import UserLookupService
from ..utils import get_bot_token, handle_slack_api_error


def format_users(users: list) -> str:
    """Format users list for display."""
    if not users:
        return "No users found."
    
    output = []
    output.append(f"\n👥 Slack Users ({len(users)} total):\n")
    
    # Group by status
    active_users = [u for u in users if not u.get('deleted', False) and not u.get('is_bot', False)]
    bots = [u for u in users if u.get('is_bot', False)]
    deleted_users = [u for u in users if u.get('deleted', False)]
    
    if active_users:
        output.append("✅ Active Users:")
        for user in sorted(active_users, key=lambda u: u.get('real_name', '')):
            name = user.get('real_name', 'N/A')
            user_id = user.get('id', 'N/A')
            email = user.get('profile', {}).get('email', 'N/A')
            title = user.get('profile', {}).get('title', '')
            title_display = f" - {title}" if title else ""
            output.append(f"  • {name:<30} ({user_id}) {email}{title_display}")
    
    if bots:
        output.append(f"\n🤖 Bots ({len(bots)}):")
        for bot in sorted(bots, key=lambda u: u.get('real_name', '')):
            name = bot.get('real_name', 'N/A')
            bot_id = bot.get('id', 'N/A')
            output.append(f"  • {name:<30} ({bot_id})")
    
    if deleted_users:
        output.append(f"\n🗑️  Deleted Users ({len(deleted_users)}):")
        for user in sorted(deleted_users, key=lambda u: u.get('real_name', '')):
            name = user.get('real_name', 'N/A')
            user_id = user.get('id', 'N/A')
            output.append(f"  • {name:<30} ({user_id})")
    
    return '\n'.join(output)


@click.command('list')
@click.option('--bot', default='leadership', help='Which bot to use (default: leadership)')
@click.option('--include-bots', is_flag=True, help='Include bot accounts')
@click.option('--include-deleted', is_flag=True, help='Include deleted users')
@click.pass_context
def list_users_cmd(ctx: click.Context, bot: str, include_bots: bool, include_deleted: bool):
    """
    List all Slack users visible to the bot.
    
    By default, only shows active human users (no bots, no deleted users).
    
    Examples:
      bars slack user list
      bars slack user list --include-bots
      bars slack user list --include-deleted
      bars --json slack user list
    """
    json_output = ctx.obj.get('json_output', False) if ctx.obj else False
    
    try:
        token = get_bot_token(bot)
        service = UserLookupService(token)
        
        if not json_output:
            click.echo("🔍 Fetching users...", err=True)
        
        # Get all users
        users = service.client.list_all_users()
        
        if not users:
            if not json_output:
                click.echo("❌ No users found", err=True)
            sys.exit(1)
        
        # Filter based on options
        if not include_bots:
            users = [u for u in users if not u.get('is_bot', False)]
        
        if not include_deleted:
            users = [u for u in users if not u.get('deleted', False)]
        
        # Display result
        if json_output:
            click.echo(json.dumps(users, indent=2))
        else:
            click.echo(format_users(users))
    
    except SlackApiError as e:
        handle_slack_api_error(e, json_output)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)

