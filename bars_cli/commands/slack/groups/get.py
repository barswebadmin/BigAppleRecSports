"""Get Slack usergroup details command."""
import sys
import json

import click
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from modules.integrations.slack.services import UsergroupService
from ..utils import get_bot_token


@click.command('get')
@click.argument('identifier')
@click.option('--bot', default='leadership', help='Which bot to use')
@click.pass_context
def get_group(ctx: click.Context, identifier: str, bot: str):
    """
    Get usergroup details by name or ID.
    
    IDENTIFIER: Usergroup handle (e.g., 'leadership') or ID (e.g., 'S03LZKQSHEU')
    """
    json_output = ctx.obj.get('json_output', False) if ctx.obj else False
    
    try:
        token = get_bot_token(bot)
        client = WebClient(token=token)
        service = UsergroupService(client)
        
        # Try as ID first (starts with S and is 11 chars)
        if identifier.startswith('S') and len(identifier) == 11:
            group_data = service.get_group_by_id(identifier)
        else:
            # Try as handle
            group_data = service.get_group_by_handle(identifier)
        
        if not group_data:
            click.echo(f"❌ Usergroup '{identifier}' not found.", err=True)
            sys.exit(1)
        
        if json_output:
            click.echo(json.dumps(group_data, indent=2))
        else:
            click.echo(f"\n📊 Usergroup Details:\n")
            click.echo(f"  Name: {group_data['name']}")
            click.echo(f"  Handle: @{group_data['handle']}")
            click.echo(f"  ID: {group_data['id']}")
            
            users = group_data.get('users', [])
            click.echo(f"  Members: {len(users)}")
            
            if users:
                click.echo(f"\n  Member IDs:")
                for user_id in users:
                    click.echo(f"    - {user_id}")
    
    except SlackApiError as e:
        click.echo(f"❌ Slack API error: {e.response['error']}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)

