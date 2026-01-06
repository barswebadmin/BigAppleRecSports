"""Get Slack channel details command."""
import json
import sys

import click
from slack_sdk.errors import SlackApiError

# Import from backend (sys.path is set in main.py)
from modules.integrations.slack.models.slack_channel import SlackChannel

from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.param_types import SLACK_CHANNEL_IDENTIFIER
from ..utils import handle_slack_api_error
from typing import Optional, Dict, Any


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
@handle_display_options(display=True, exit_on_error=True)
@click.argument('identifier', type=SLACK_CHANNEL_IDENTIFIER, required=False)
@click.pass_context
def get_channel_cmd(ctx: click.Context, identifier: Optional[Dict[str, Any]]):
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
    display_override = ctx.obj.get('display_override') if ctx.obj else None
    exit_override = ctx.obj.get('exit_override') if ctx.obj else None
    should_display = display_override if display_override is not None else True
    
    if not identifier:
        error_msg = "Channel identifier required"
        if should_display:
            if json_output:
                click.echo(json.dumps({"error": error_msg}, indent=2), err=True)
            else:
                click.echo(f"❌ {error_msg}", err=True)
        raise click.ClickException(error_msg)
    
    try:
        # Get leadership_bot from context meta (initialized at slack group level)
        bot = ctx.meta['leadership_bot']
        
        # Extract identifier value from dict
        if 'channel_id' in identifier:
            identifier_value = identifier['channel_id']
            if should_display and not json_output:
                click.echo(f"🔍 Looking up channel ID: {identifier_value}", err=True)
        elif 'name' in identifier:
            identifier_value = identifier['name']
            if should_display and not json_output:
                click.echo(f"🔍 Looking up channel name: {identifier_value}", err=True)
        else:
            raise ValueError("Invalid identifier format")
        
        # Use leadership_bot's lookup_channel method
        channel_data = bot.lookup_channel(identifier_value)
        
        if not channel_data:
            error_msg = f"Channel not found: {identifier}"
            if should_display:
                if json_output:
                    click.echo(json.dumps({"error": error_msg}, indent=2), err=True)
                else:
                    click.echo(f"❌ {error_msg}", err=True)
                    click.echo(f"💡 Try checking the name/ID spelling or use 'bars slack channel list' to see all channels", err=True)
            raise click.ClickException(error_msg)
        
        # Display result
        if json_output:
            click.echo(json.dumps(channel_data, indent=2))
        elif should_display:
            click.echo(format_channel(channel_data))
        
        return channel_data
    
    except SlackApiError as e:
        # Get token from bot if available
        token = None
        try:
            bot = ctx.meta.get('leadership_bot')
            if bot and hasattr(bot, 'client') and hasattr(bot.client, 'token'):
                token = bot.client.token
        except Exception:
            pass
        
        handle_slack_api_error(e, json_output=json_output, token=token, api_method='conversations.info')
        if exit_override is None or exit_override:
            sys.exit(1)
        raise
    except (click.ClickException, ValueError) as e:
        if should_display:
            if json_output:
                click.echo(json.dumps({"error": str(e)}, indent=2), err=True)
            else:
                click.echo(f"❌ {e}", err=True)
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

