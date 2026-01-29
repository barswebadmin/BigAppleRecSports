"""List Slack channels command."""
import sys
import json
from typing import Optional, List, Dict, Any

import click_extra as click
from slack_sdk.errors import SlackApiError

from bars_cli._core.decorators.handle_display_options import handle_display_options
from ..utils import handle_slack_api_error
from .._shared.slack_formatters import format_channels




@click.command('list', aliases=['list-channels'])
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
        # Get leadership_bot from context meta (has channel access)
        bot = ctx.meta.get('leadership_bot')
        
        # If leadership_bot not in meta, try to initialize it
        if not bot:
            try:
                from bars_cli.backend_services.slack.bot_apps.bot_apps import leadership_bot
                ctx.meta['leadership_bot'] = leadership_bot
                bot = leadership_bot
            except Exception as e:
                error_msg = f"Failed to initialize leadership bot: {e}"
                if should_display:
                    if json_output:
                        click.echo(json.dumps({"error": error_msg}, indent=2), err=True)
                    else:
                        click.echo(f"❌ {error_msg}", err=True)
                if exit_override is None or exit_override:
                    sys.exit(1)
                raise
        
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
        except (KeyError, Exception):
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

