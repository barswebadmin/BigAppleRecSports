"""List Slack channels command."""
import sys
import json

import click
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from ..utils import (
    get_bot_token,
    list_all_channels,
    handle_slack_api_error
)


def format_channels(channels: list) -> str:
    """Format channels list for display."""
    if not channels:
        return "No channels found."
    
    output = []
    output.append(f"\n📺 Slack Channels ({len(channels)} total):\n")
    
    # Group by type
    public_channels = [c for c in channels if not c.get('is_private', False)]
    private_channels = [c for c in channels if c.get('is_private', False)]
    
    if public_channels:
        output.append("🌐 Public Channels:")
        for channel in sorted(public_channels, key=lambda c: c.get('name', '')):
            name = channel.get('name', 'N/A')
            channel_id = channel.get('id', 'N/A')
            archived = " [ARCHIVED]" if channel.get('is_archived', False) else ""
            members = channel.get('num_members', '?')
            output.append(f"  • #{name:<30} ({channel_id}) - {members} members{archived}")
    
    if private_channels:
        output.append("\n🔒 Private Channels:")
        for channel in sorted(private_channels, key=lambda c: c.get('name', '')):
            name = channel.get('name', 'N/A')
            channel_id = channel.get('id', 'N/A')
            archived = " [ARCHIVED]" if channel.get('is_archived', False) else ""
            members = channel.get('num_members', '?')
            output.append(f"  • #{name:<30} ({channel_id}) - {members} members{archived}")
    
    return '\n'.join(output)


@click.command('list')
@click.option('--bot', default='leadership', help='Which bot to use (default: leadership)')
@click.option('--include-archived', is_flag=True, help='Include archived channels')
@click.pass_context
def list_channels_cmd(ctx: click.Context, bot: str, include_archived: bool):
    """
    List all Slack channels visible to the bot.
    
    Note: Only lists public channels. Private channels would require 'groups:read' scope.
    
    Examples:
      bars slack channel list
      bars slack channel list --include-archived
      bars --json slack channel list
    """
    json_output = ctx.obj.get('json_output', False) if ctx.obj else False
    
    try:
        token = get_bot_token(bot)
        client = WebClient(token=token)
        
        if not json_output:
            click.echo("🔍 Fetching channels...", err=True)
        
        channels = list_all_channels(client, display=not json_output)
        
        if not channels:
            if not json_output:
                click.echo("❌ No channels found", err=True)
            sys.exit(1)
        
        # Filter archived channels if requested
        if not include_archived:
            channels = [c for c in channels if not c.get('is_archived', False)]
        
        # Display result
        if json_output:
            click.echo(json.dumps(channels, indent=2))
        else:
            click.echo(format_channels(channels))
    
    except SlackApiError as e:
        handle_slack_api_error(e, json_output)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)

