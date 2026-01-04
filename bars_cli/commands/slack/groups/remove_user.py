"""Remove user from Slack usergroup command."""
import sys

import click
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from modules.integrations.slack.services import UsergroupService
from ..utils import get_bot_token


@click.command('remove-user')
@click.argument('group_handle')
@click.argument('user_id')
@click.option('--bot', default='leadership', help='Which bot to use')
@click.option('--dry-run', is_flag=True, help='Preview changes without applying')
def remove_user_from_group(group_handle: str, user_id: str, bot: str, dry_run: bool):
    """
    Remove a user from a usergroup.
    
    GROUP_HANDLE: Usergroup handle (e.g., 'leadership')
    USER_ID: Slack user ID (e.g., 'U01ABC123')
    """
    try:
        token = get_bot_token(bot)
        client = WebClient(token=token)
        service = UsergroupService(client)
        
        # Get group
        group_data = service.get_group_by_handle(group_handle)
        if not group_data:
            click.echo(f"❌ Usergroup '{group_handle}' not found.", err=True)
            sys.exit(1)
        
        group_id = group_data['id']
        current_members = group_data.get('users', [])
        
        if user_id not in current_members:
            click.echo(f"ℹ️  User {user_id} is not in @{group_handle}")
            return
        
        if dry_run:
            click.echo(f"\n🔍 DRY RUN - Would remove user {user_id} from @{group_handle}")
            click.echo(f"  Current members: {len(current_members)}")
            click.echo(f"  New total: {len(current_members) - 1}")
            return
        
        success = service.remove_user_from_group(group_id, user_id)
        
        if success:
            click.echo(f"✅ Removed user {user_id} from @{group_handle}")
        else:
            click.echo(f"❌ Failed to remove user from group", err=True)
            sys.exit(1)
    
    except SlackApiError as e:
        click.echo(f"❌ Slack API error: {e.response['error']}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)

