"""List Slack channels command."""
import sys
import json
from typing import Optional, List, Dict, Any

import click
from slack_sdk.errors import SlackApiError

from bars_cli._core.decorators.handle_display_options import handle_display_options
from ..utils import handle_slack_api_error


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
@handle_display_options(display=True, exit_on_error=True)
@click.option('--include-archived', is_flag=True, help='Include archived channels')
@click.pass_context
def list_channels_cmd(ctx: click.Context, include_archived: bool) -> Optional[List[Dict[str, Any]]]:
    """
    List all Slack channels visible to the bot.
    
    Note: Only lists public channels. Private channels would require 'groups:read' scope.
    
    Examples:
      bars slack channel list
      bars slack channel list --include-archived
      bars --json slack channel list
    """
    json_output = ctx.obj.get('json_output', False) if ctx.obj else False
    display_override = ctx.obj.get('display_override') if ctx.obj else None
    exit_override = ctx.obj.get('exit_override') if ctx.obj else None
    should_display = display_override if display_override is not None else True
    
    try:
        # Get leadership_bot from context meta (initialized at slack group level)
        bot = ctx.meta['leadership_bot']
        
        if should_display and not json_output:
            click.echo("🔍 Fetching channels...", err=True)
        
        # Use leadership_bot's list_all_channels method
        channels = bot.list_all_channels(include_archived=include_archived)
        
        if not channels:
            error_msg = "No channels found"
            if should_display:
                if json_output:
                    click.echo(json.dumps({"error": error_msg}, indent=2), err=True)
                else:
                    click.echo(f"❌ {error_msg}", err=True)
            if exit_override is None or exit_override:
                sys.exit(1)
            return []
        
        # Display result
        if json_output:
            click.echo(json.dumps(channels, indent=2))
        elif should_display:
            click.echo(format_channels(channels))
        
        return channels
    
    except SlackApiError as e:
        # Get token from bot if available
        token = None
        try:
            bot = ctx.meta.get('leadership_bot')
            if bot and hasattr(bot, 'client') and hasattr(bot.client, 'token'):
                token = bot.client.token
        except Exception:
            pass
        
        handle_slack_api_error(e, json_output=json_output, token=token, api_method='conversations.list')
        if exit_override is None or exit_override:
            sys.exit(1)
        raise
    except Exception as e:
        error_msg = f"Error: {e}"
        if should_display:
            if json_output:
                click.echo(json.dumps({"error": error_msg}, indent=2), err=True)
            else:
                click.echo(f"❌ {error_msg}", err=True)
        if exit_override is None or exit_override:
            sys.exit(1)
        raise

