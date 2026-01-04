"""Get Slack channel details command."""
import sys
import json

import click
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

sys.path.insert(0, 'backend')
from modules.integrations.slack.models.slack_channel import SlackChannel

from ..utils import (
    get_bot_token,
    lookup_channel_by_id,
    lookup_channel_by_name,
    handle_slack_api_error
)


def format_channel(channel: dict) -> str:
    """Format channel data for display."""
    name = channel.get('name', 'N/A')
    channel_id = channel.get('id', 'N/A')
    is_private = channel.get('is_private', False)
    is_archived = channel.get('is_archived', False)
    
    output = []
    output.append("\n📺 Channel Details:\n")
    output.append(f"  Name: #{name}")
    output.append(f"  Channel ID: {channel_id}")
    
    if is_private:
        output.append("  Type: Private Channel 🔒")
    else:
        output.append("  Type: Public Channel")
    
    if is_archived:
        output.append("  ⚠️  Status: ARCHIVED")
    
    topic = channel.get('topic', {}).get('value')
    if topic:
        output.append(f"  Topic: {topic}")
    
    purpose = channel.get('purpose', {}).get('value')
    if purpose:
        output.append(f"  Purpose: {purpose}")
    
    num_members = channel.get('num_members')
    if num_members is not None:
        output.append(f"  Members: {num_members}")
    
    return '\n'.join(output)


@click.command('get')
@click.argument('identifier', required=False)
@click.option('--bot', default='leadership', help='Which bot to use (default: leadership)')
@click.pass_context
def get_channel_cmd(ctx: click.Context, identifier: str, bot: str):
    """
    Get Slack channel details by name or ID.
    
    IDENTIFIER: Channel name (with or without #) or Slack channel ID (e.g., 'C01ABC123').
                If omitted, will prompt for input.
    
    Examples:
      bars slack channel get general
      bars slack channel get kickball-leadership
      bars slack channel get C092RU7R6PL
      bars --json slack channel get general
    """
    json_output = ctx.obj.get('json_output', False) if ctx.obj else False
    
    # Prompt for identifier if not provided
    if not identifier:
        try:
            click.echo("Enter Slack channel name or ID:", err=True)
            identifier = input().strip()
        except (EOFError, KeyboardInterrupt):
            click.echo("\n❌ Cancelled", err=True)
            sys.exit(1)
    
    if not identifier:
        click.echo("❌ Error: Channel name or ID required", err=True)
        sys.exit(1)
    
    try:
        token = get_bot_token(bot)
        client = WebClient(token=token)
        
        # Lookup channel by ID or name
        if SlackChannel.is_valid_channel_id(identifier):
            if not json_output:
                click.echo(f"🔍 Looking up channel ID: {identifier}", err=True)
            channel_data = lookup_channel_by_id(client, identifier, display=not json_output)
        else:
            if not json_output:
                click.echo(f"🔍 Looking up channel name: {identifier}", err=True)
            channel_data = lookup_channel_by_name(client, identifier, display=not json_output)
        
        if not channel_data:
            if not json_output:
                click.echo(f"❌ Channel not found: {identifier}", err=True)
            sys.exit(1)
        
        # Display result
        if json_output:
            click.echo(json.dumps(channel_data, indent=2))
        else:
            click.echo(format_channel(channel_data))
    
    except SlackApiError as e:
        handle_slack_api_error(e, json_output)
        sys.exit(1)
    except click.BadParameter as e:
        click.echo(f"❌ {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)

