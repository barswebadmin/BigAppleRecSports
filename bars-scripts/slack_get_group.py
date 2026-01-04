#!/usr/bin/env python3
"""
Get Slack User Group Details

Looks up a Slack user group (usergroup) by name or ID.

Usage:
    slack-get-group leadership
    slack-get-group S03LZKQSHEU
    slack-get-group --bot leadership executive-board
    slack-get-group --json leadership
    slack-get-group (lists all groups)

Examples:
    # Lookup by name
    $ slack-get-group leadership
    Name: Leadership
    Group ID: S03LZKQSHEU
    Handle: @leadership
    Members: 15

    # Lookup by group ID
    $ slack-get-group S03LZKQSHEU
    Name: Leadership
    Group ID: S03LZKQSHEU

    # JSON output
    $ slack-get-group leadership --json
    {"id": "S03LZKQSHEU", "name": "Leadership", ...}
    
    # List all groups
    $ slack-get-group
    Available user groups:
      • Leadership (S03LZKQSHEU) - @leadership - 15 members
      • Executive Board (S03LZKEXECUT) - @exec-board - 12 members
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


def is_group_id(value: str) -> bool:
    """Check if the value looks like a Slack user group ID (e.g., S03LZKQSHEU)."""
    return value.startswith('S') and len(value) == 11 and value.isalnum()


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


def list_all_groups(client: WebClient, display: bool = True) -> List[Dict[str, Any]]:
    """
    List all user groups visible to the bot.
    
    Args:
        client: Initialized Slack WebClient
        display: If True, print status messages
        
    Returns:
        List of user group dicts
    """
    try:
        response = client.usergroups_list(
            include_count=True,
            include_disabled=True,
            include_users=True
        )
        
        if response['ok']:
            return response['usergroups']
        else:
            if display:
                print(f"❌ Error listing user groups: {response.get('error', 'Unknown error')}", file=sys.stderr)
            return []
        
    except SlackApiError as e:
        if display:
            print(f"❌ Error listing user groups: {e.response['error']}", file=sys.stderr)
        return []


def lookup_group_by_name(client: WebClient, group_name: str, display: bool = True) -> Optional[Dict[str, Any]]:
    """
    Look up a Slack user group by name or handle.
    
    Args:
        client: Initialized Slack WebClient
        group_name: Group name or handle (with or without @ prefix)
        display: If True, print status messages
        
    Returns:
        User group dict if found, None otherwise
    """
    # Remove @ prefix if present
    search_name = group_name.lstrip('@').lower()
    
    groups = list_all_groups(client, display=False)
    
    for group in groups:
        name = group.get('name', '').lower()
        handle = group.get('handle', '').lower()
        
        if name == search_name or handle == search_name:
            return group
    
    if display:
        print(f"❌ User group not found: {group_name}", file=sys.stderr)
    return None


def lookup_group_by_id(client: WebClient, group_id: str, display: bool = True) -> Optional[Dict[str, Any]]:
    """
    Look up a Slack user group by ID.
    
    Args:
        client: Initialized Slack WebClient
        group_id: Slack user group ID
        display: If True, print status messages
        
    Returns:
        User group dict if found, None otherwise
    """
    groups = list_all_groups(client, display=False)
    
    for group in groups:
        if group.get('id') == group_id:
            return group
    
    if display:
        print(f"❌ User group not found: {group_id}", file=sys.stderr)
    return None


def get_group(client: WebClient, identifier: str, display: bool = True) -> Optional[Dict[str, Any]]:
    """
    Look up a Slack user group by name, handle, or ID.
    
    Args:
        client: Initialized Slack WebClient
        identifier: Group name, handle, or ID
        display: If True, print status messages and errors
        
    Returns:
        User group dict if found, None otherwise
    """
    if is_group_id(identifier):
        if display:
            print(f"🔍 Looking up user group ID: {identifier}", file=sys.stderr)
        return lookup_group_by_id(client, identifier, display=display)
    else:
        if display:
            print(f"🔍 Looking up user group name: {identifier}", file=sys.stderr)
        return lookup_group_by_name(client, identifier, display=display)


def format_group(group: Dict[str, Any]) -> str:
    """Format user group data for display (formatted output only)."""
    name = group.get('name', 'N/A')
    group_id = group.get('id', 'N/A')
    handle = group.get('handle', 'N/A')
    is_disabled = group.get('date_delete', 0) != 0
    
    output = []
    output.append(f"Name: {name}")
    output.append(f"Group ID: {group_id}")
    output.append(f"Handle: @{handle}")
    
    if is_disabled:
        output.append("⚠️  Status: DISABLED")
    
    # Add optional fields if present
    description = group.get('description')
    if description:
        output.append(f"Description: {description}")
    
    user_count = group.get('user_count')
    if user_count is not None:
        output.append(f"Members: {user_count}")
    
    # Show users if available
    users = group.get('users', [])
    if users and len(users) <= 20:  # Only show if reasonable number
        output.append(f"User IDs: {', '.join(users)}")
    
    return '\n'.join(output)


def display_groups_list(groups: List[Dict[str, Any]]):
    """Display a formatted list of all user groups."""
    if not groups:
        print("No user groups found.", file=sys.stderr)
        return
    
    # Sort by name
    groups = sorted(groups, key=lambda g: g.get('name', '').lower())
    
    print(f"👥 Available user groups ({len(groups)} total):")
    print()
    
    for group in groups:
        name = group.get('name', 'unknown')
        group_id = group.get('id', 'unknown')
        handle = group.get('handle', 'unknown')
        user_count = group.get('user_count', 0)
        is_disabled = group.get('date_delete', 0) != 0
        
        status = " (disabled)" if is_disabled else ""
        
        print(f"  • {name:<30s} ({group_id}) - @{handle} - {user_count} members{status}")


def main():
    parser = argparse.ArgumentParser(
        description="Look up Slack user group by name or ID",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    slack-get-group leadership
    slack-get-group S03LZKQSHEU
    slack-get-group --bot leadership executive-board
    slack-get-group --json leadership
    slack-get-group (lists all groups)
        """
    )
    
    parser.add_argument(
        'identifier',
        nargs='?',
        help='Group name, handle, or ID (if omitted, lists all groups)'
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
    
    # If no identifier, list all groups
    if not args.identifier:
        if args.json:
            groups = list_all_groups(client, display=False)
            print(json.dumps(groups, indent=2))
        else:
            groups = list_all_groups(client, display=True)
            display_groups_list(groups)
        sys.exit(0)
    
    # Look up specific group
    group = get_group(client, args.identifier, display=not args.json)
    
    # Display result
    if group:
        if not args.json:
            print("", file=sys.stderr)  # Blank line before output
        print(format_display(group, formatter_func=format_group, should_format=not args.json))
        print()
        sys.exit(0)
    else:
        if not args.json:
            print(f"❌ User group not found: {args.identifier}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

