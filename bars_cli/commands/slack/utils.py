"""
Shared utilities for Slack CLI commands.
"""
from typing import Optional, Dict, Any, List
import sys

import click
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

sys.path.insert(0, 'backend')
from config import config


def get_bot_token(bot_name: str) -> str:
    """
    Get Slack bot token by bot name.
    
    Args:
        bot_name: Name of the bot (dev, exec, leadership, etc.)
        
    Returns:
        Bot token string
        
    Raises:
        click.BadParameter: If bot name is invalid
    """
    bot_name = bot_name.lower()
    
    bot_map = {
        'dev': config.Slack.Bots.Dev,
        'exec': config.Slack.Bots.Exec,
        'leadership': config.Slack.Bots.Leadership,
        'payment_assistance': config.Slack.Bots.PaymentAssistance,
        'refunds': config.Slack.Bots.Refunds,
        'registrations': config.Slack.Bots.Registrations,
        'web': config.Slack.Bots.Web,
    }
    
    bot = bot_map.get(bot_name)
    if not bot:
        available = ', '.join(bot_map.keys())
        raise click.BadParameter(
            f"Unknown bot: {bot_name}. Available: {available}",
            param_hint='--bot'
        )
    
    return bot.token


def list_all_channels(
    client: WebClient,
    display: bool = True
) -> list:
    """
    List all public channels visible to the bot.
    
    Note: Only lists public channels. Private channels would require 'groups:read' scope.
    
    Args:
        client: Initialized Slack WebClient
        display: If True, print status messages
        
    Returns:
        List of channel dicts
    """
    try:
        channels = []
        cursor = None
        
        while True:
            response = client.conversations_list(
                types="public_channel",
                cursor=cursor,
                limit=200
            )
            
            if response['ok']:
                response_channels = response.get('channels', [])
                if response_channels:
                    channels.extend(response_channels)
                cursor = response.get('response_metadata', {}).get('next_cursor')
                if not cursor:
                    break
            else:
                if display:
                    click.echo(f"❌ Error listing channels: {response.get('error', 'Unknown error')}", err=True)
                return []
        
        return channels
        
    except SlackApiError as e:
        if display:
            error_msg = e.response['error']
            click.echo(f"❌ Error listing channels: {error_msg}", err=True)
            if error_msg == 'missing_scope':
                click.echo(f"   Full response: {e.response}", err=True)
        return []


def lookup_channel_by_name(
    client: WebClient,
    channel_name: str,
    display: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Look up a Slack channel by name.
    
    Args:
        client: Initialized Slack WebClient
        channel_name: Channel name (with or without # prefix)
        display: If True, print status messages
        
    Returns:
        Channel dict if found, None otherwise
    """
    channel_name = channel_name.lstrip('#').lower()
    
    channels = list_all_channels(client, display=False)
    
    for channel in channels:
        if channel.get('name', '').lower() == channel_name:
            return channel
    
    if display:
        click.echo(f"❌ Channel not found: {channel_name}", err=True)
    return None


def lookup_channel_by_id(
    client: WebClient,
    channel_id: str,
    display: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Look up a Slack channel by ID.
    
    Args:
        client: Initialized Slack WebClient
        channel_id: Slack channel ID
        display: If True, print status messages
        
    Returns:
        Channel dict if found, None otherwise
    """
    try:
        response = client.conversations_info(channel=channel_id)
        if response['ok']:
            return response['channel']
        else:
            if display:
                click.echo(f"❌ Channel not found: {channel_id}", err=True)
            return None
    except SlackApiError as e:
        if display:
            error_msg = e.response['error']
            click.echo(f"❌ Error looking up channel ID: {error_msg}", err=True)
            if error_msg == 'missing_scope':
                click.echo(f"   Full response: {e.response}", err=True)
        return None


def handle_slack_api_error(e: SlackApiError, json_output: bool = False) -> None:
    """
    Handle SlackApiError consistently across commands.
    
    Args:
        e: SlackApiError exception
        json_output: If True, suppress detailed error output
    """
    import json
    
    error_msg = e.response['error']
    click.echo(f"❌ Slack API error: {error_msg}", err=True)
    
    if not json_output and error_msg == 'missing_scope':
        click.echo(f"   Missing scope detected. Full response:", err=True)
        click.echo(f"   {json.dumps(e.response.data, indent=2)}", err=True)

