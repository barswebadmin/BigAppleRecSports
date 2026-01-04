#!/usr/bin/env python3
"""
Get Slack Channel Details

Looks up a Slack channel by name or ID.

Usage:
    slack-get-channel general
    slack-get-channel C03LZKQSHEU
    slack-get-channel --bot leadership kickball-leadership
    slack-get-channel --json general
    slack-get-channel (lists all channels)

Examples:
    # Lookup by name
    $ slack-get-channel general
    Name: general
    Channel ID: C03LZKQSHEU
    Topic: Company-wide announcements
    Members: 150

    # Lookup by channel ID
    $ slack-get-channel C03LZKQSHEU
    Name: general
    Channel ID: C03LZKQSHEU

    # JSON output
    $ slack-get-channel general --json
    {"id": "C03LZKQSHEU", "name": "general", ...}
    
    # List all channels
    $ slack-get-channel
    Available channels:
      • general (C03LZKQSHEU) - 150 members
      • random (C03LZKRANDOM) - 120 members
      ...
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Optional, Dict, Any, List

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from shared_utils import load_environment
from config.slack import SlackConfig
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_helpers import format_display


def is_channel_id(value: str) -> bool:
    """Check if the value looks like a Slack channel ID (e.g., C03LZKQSHEU)."""
    return value.startswith('C') and len(value) == 11 and value.isalnum()


def get_bot_token(bot_name: str) -> str:
    """Get the Slack bot token for the specified bot."""
    bot_name = bot_name.lower()
    
    bot_map = {
        'leadership': SlackConfig.Bots.Leadership,
        'refunds': SlackConfig.Bots.Refunds,
        'registrations': SlackConfig.Bots.Registrations,
        'payment_assistance': SlackConfig.Bots.PaymentAssistance,
        'exec': SlackConfig.Bots.Exec,
        'dev': SlackConfig.Bots.Dev,
        'web': SlackConfig.Bots.Web,
    }
    
    bot = bot_map.get(bot_name)
    if not bot:
        available = ', '.join(bot_map.keys())
        raise ValueError(f"Unknown bot: {bot_name}. Available: {available}")
    
    return bot.token


def list_all_channels(client: WebClient, display: bool = True) -> List[Dict[str, Any]]:
    """
    List all channels visible to the bot.
    
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
                types="public_channel,private_channel",
                cursor=cursor,
                limit=200
            )
            
            if response['ok']:
                channels.extend(response['channels'])
                cursor = response.get('response_metadata', {}).get('next_cursor')
                if not cursor:
                    break
            else:
                if display:
                    print(f"❌ Error listing channels: {response.get('error', 'Unknown error')}", file=sys.stderr)
                return []
        
        return channels
        
    except SlackApiError as e:
        if display:
            print(f"❌ Error listing channels: {e.response['error']}", file=sys.stderr)
        return []


def lookup_channel_by_name(client: WebClient, channel_name: str, display: bool = True) -> Optional[Dict[str, Any]]:
    """
    Look up a Slack channel by name.
    
    Args:
        client: Initialized Slack WebClient
        channel_name: Channel name (with or without # prefix)
        display: If True, print status messages
        
    Returns:
        Channel dict if found, None otherwise
    """
    # Remove # prefix if present
    channel_name = channel_name.lstrip('#').lower()
    
    channels = list_all_channels(client, display=False)
    
    for channel in channels:
        if channel.get('name', '').lower() == channel_name:
            return channel
    
    if display:
        print(f"❌ Channel not found: {channel_name}", file=sys.stderr)
    return None


def lookup_channel_by_id(client: WebClient, channel_id: str, display: bool = True) -> Optional[Dict[str, Any]]:
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
                print(f"❌ Channel not found: {channel_id}", file=sys.stderr)
            return None
    except SlackApiError as e:
        if display:
            print(f"❌ Error looking up channel ID: {e.response['error']}", file=sys.stderr)
        return None


def get_channel(client: WebClient, identifier: str, display: bool = True) -> Optional[Dict[str, Any]]:
    """
    Look up a Slack channel by name or ID.
    
    Args:
        client: Initialized Slack WebClient
        identifier: Channel name or ID
        display: If True, print status messages and errors
        
    Returns:
        Channel dict if found, None otherwise
    """
    if is_channel_id(identifier):
        if display:
            print(f"🔍 Looking up channel ID: {identifier}", file=sys.stderr)
        return lookup_channel_by_id(client, identifier, display=display)
    else:
        if display:
            print(f"🔍 Looking up channel name: {identifier}", file=sys.stderr)
        return lookup_channel_by_name(client, identifier, display=display)


def format_channel(channel: Dict[str, Any]) -> str:
    """Format channel data for display (formatted output only)."""
    name = channel.get('name', 'N/A')
    channel_id = channel.get('id', 'N/A')
    is_private = channel.get('is_private', False)
    is_archived = channel.get('is_archived', False)
    
    output = []
    output.append(f"Name: #{name}")
    output.append(f"Channel ID: {channel_id}")
    
    if is_private:
        output.append("Type: Private Channel 🔒")
    else:
        output.append("Type: Public Channel")
    
    if is_archived:
        output.append("⚠️  Status: ARCHIVED")
    
    # Add optional fields if present
    topic = channel.get('topic', {}).get('value')
    if topic:
        output.append(f"Topic: {topic}")
    
    purpose = channel.get('purpose', {}).get('value')
    if purpose:
        output.append(f"Purpose: {purpose}")
    
    num_members = channel.get('num_members')
    if num_members is not None:
        output.append(f"Members: {num_members}")
    
    return '\n'.join(output)


def display_channels_list(channels: List[Dict[str, Any]]):
    """Display a formatted list of all channels."""
    if not channels:
        print("No channels found.", file=sys.stderr)
        return
    
    # Sort by name
    channels = sorted(channels, key=lambda c: c.get('name', '').lower())
    
    print(f"📺 Available channels ({len(channels)} total):")
    print()
    
    for channel in channels:
        name = channel.get('name', 'unknown')
        channel_id = channel.get('id', 'unknown')
        num_members = channel.get('num_members', 0)
        is_private = channel.get('is_private', False)
        is_archived = channel.get('is_archived', False)
        
        privacy = "🔒" if is_private else "  "
        status = " (archived)" if is_archived else ""
        
        print(f"  {privacy} #{name:<30s} ({channel_id}) - {num_members} members{status}")


def main():
    parser = argparse.ArgumentParser(
        description="Look up Slack channel by name or ID",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    slack-get-channel general
    slack-get-channel C03LZKQSHEU
    slack-get-channel --bot leadership kickball-leadership
    slack-get-channel --json general
    slack-get-channel (lists all channels)
        """
    )
    
    parser.add_argument(
        'identifier',
        nargs='?',
        help='Channel name or ID (if omitted, lists all channels)'
    )
    
    parser.add_argument(
        '--bot',
        default='leadership',
        choices=['leadership', 'refunds', 'registrations', 'payment_assistance', 'exec', 'dev', 'web'],
        help='Which Slack bot token to use (default: leadership)'
    )
    
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output raw JSON response'
    )
    
    parser.add_argument(
        '--env',
        default='production',
        choices=['development', 'staging', 'production'],
        help='Environment to use (default: production)'
    )
    
    args = parser.parse_args()
    
    # Load environment
    load_environment(args.env)
    
    # Get bot token
    try:
        token = get_bot_token(args.bot)
    except ValueError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)
    
    # Create Slack client
    client = WebClient(token=token)
    
    # If no identifier, list all channels
    if not args.identifier:
        if args.json:
            channels = list_all_channels(client, display=False)
            print(json.dumps(channels, indent=2))
        else:
            channels = list_all_channels(client, display=True)
            display_channels_list(channels)
        sys.exit(0)
    
    # Look up specific channel
    channel = get_channel(client, args.identifier, display=not args.json)
    
    # Display result
    if channel:
        if not args.json:
            print("", file=sys.stderr)  # Blank line before output
        print(format_display(channel, formatter_func=format_channel, should_format=not args.json))
        print()
        sys.exit(0)
    else:
        if not args.json:
            print(f"❌ Channel not found: {args.identifier}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

