"""Remove user from Slack usergroup command."""
import sys

import click
from slack_sdk.errors import SlackApiError

from bars_cli._core.param_types import SLACK_GROUP_IDENTIFIER, SLACK_USER_IDENTIFIER


@click.command('remove-user')
@click.argument('group_identifier', type=SLACK_GROUP_IDENTIFIER)
@click.argument('user_identifier', type=SLACK_USER_IDENTIFIER)
@click.option('--bot', default='leadership', help='Which bot to use')
@click.option('--dry-run', is_flag=True, help='Preview changes without applying')
@click.pass_context
def remove_slack_user_from_group(ctx: click.Context, group_identifier: dict, user_identifier: dict, bot: str, dry_run: bool):
    """
    Remove a user from a usergroup.
    
    GROUP_IDENTIFIER: Usergroup identifier (ID, name, or handle)
    USER_IDENTIFIER: User identifier (ID, email, handle, or display name)
    """
    # Service is guaranteed to be available (initialized in slack group)
    slack_service = ctx.meta['slack_service']
    
    try:
        # Resolve group identifier
        group_data = slack_service.resolve_group_identifier(group_identifier, bot)
        if not group_data:
            click.echo(f"❌ Usergroup not found.", err=True)
            sys.exit(1)
        
        group_id = group_data['id']
        group_handle = group_data.get('handle', group_data.get('name', 'unknown'))
        current_members = group_data.get('users', [])
        
        # Resolve user identifier
        user_data = slack_service.resolve_user_identifier(user_identifier, bot)
        if not user_data:
            click.echo(f"❌ User not found.", err=True)
            sys.exit(1)
        
        user_id = user_data['id']
        
        if user_id not in current_members:
            click.echo(f"ℹ️  User {user_id} is not in @{group_handle}")
            return
        
        if dry_run:
            click.echo(f"\n🔍 DRY RUN - Would remove user {user_id} from @{group_handle}")
            click.echo(f"  Current members: {len(current_members)}")
            click.echo(f"  New total: {len(current_members) - 1}")
            return
        
        service = slack_service.get_usergroup_service(bot)
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

