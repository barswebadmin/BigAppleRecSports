"""Get Slack user details command."""
import sys
import json

import click
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from ..utils import get_bot_token


@click.command('get')
@click.argument('identifier')
@click.option('--bot', default='leadership', help='Which bot to use')
@click.pass_context
def get_user(ctx: click.Context, identifier: str, bot: str):
    """
    Get Slack user details by email or ID.
    
    IDENTIFIER: User's email address or Slack user ID (e.g., 'U01ABC123')
    """
    json_output = ctx.obj.get('json_output', False) if ctx.obj else False
    
    try:
        token = get_bot_token(bot)
        client = WebClient(token=token)
        
        # Determine if identifier is email or ID
        if identifier.startswith('U') and len(identifier) == 11:
            # Looks like a user ID
            response = client.users_info(user=identifier)
            user_data = response.get('user')
        elif '@' in identifier:
            # Looks like an email
            response = client.users_lookupByEmail(email=identifier)
            user_data = response.get('user')
        else:
            click.echo(f"❌ Invalid identifier: '{identifier}'", err=True)
            click.echo("   Must be an email (contains @) or user ID (starts with U)", err=True)
            sys.exit(1)
        
        if not user_data:
            click.echo(f"❌ User '{identifier}' not found.", err=True)
            sys.exit(1)
        
        if json_output:
            click.echo(json.dumps(user_data, indent=2))
        else:
            profile = user_data.get('profile', {})
            click.echo(f"\n👤 User Details:\n")
            click.echo(f"  Name: {user_data.get('real_name', 'N/A')}")
            click.echo(f"  Display Name: {profile.get('display_name', 'N/A')}")
            click.echo(f"  Email: {profile.get('email', 'N/A')}")
            click.echo(f"  ID: {user_data.get('id', 'N/A')}")
            click.echo(f"  Title: {profile.get('title', 'N/A')}")
            click.echo(f"  Phone: {profile.get('phone', 'N/A')}")
            
            if user_data.get('is_admin'):
                click.echo(f"  Role: Workspace Admin")
            elif user_data.get('is_owner'):
                click.echo(f"  Role: Workspace Owner")
            else:
                click.echo(f"  Role: Member")
    
    except SlackApiError as e:
        click.echo(f"❌ Slack API error: {e.response['error']}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)

