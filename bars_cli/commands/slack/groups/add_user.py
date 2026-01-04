"""Add user to Slack usergroup command."""
import sys

import click
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from modules.integrations.slack.services import UsergroupService
from ..utils import get_bot_token


@click.command('add-user')
@click.argument('group_handle')
@click.argument('user_id')
@click.option('--bot', default='leadership', help='Which bot to use')
@click.option('--dry-run', is_flag=True, help='Preview changes without applying')
def add_user_to_group(group_handle: str, user_id: str, bot: str, dry_run: bool):
    """
    Add a user to a usergroup.
    
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
        
        if user_id in current_members:
            click.echo(f"ℹ️  User {user_id} is already in @{group_handle}")
            return
        
        if dry_run:
            click.echo(f"\n🔍 DRY RUN - Would add user {user_id} to @{group_handle}")
            click.echo(f"  Current members: {len(current_members)}")
            click.echo(f"  New total: {len(current_members) + 1}")
            return
        
        success = service.add_user_to_group(group_id, user_id)
        
        if success:
            click.echo(f"✅ Added user {user_id} to @{group_handle}")
        else:
            click.echo(f"❌ Failed to add user to group", err=True)
            sys.exit(1)
    
    except SlackApiError as e:
        click.echo(f"❌ Slack API error: {e.response['error']}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)

