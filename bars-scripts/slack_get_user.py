#!/usr/bin/env python3
"""
Get Slack User Details

Looks up a Slack user by email address or user ID.

Usage:
    slack-get-user stephen@bigapplerecsports.com
    slack-get-user U03LZKQSHEU
    slack-get-user --bot refunds U12345ABC
    slack-get-user --json stephen@example.com
    slack-get-user (prompts for email/ID)

Examples:
    # Lookup by email
    $ slack-get-user stephen@bigapplerecsports.com
    Name: Stephen Torres
    Email: stephen@bigapplerecsports.com
    Display: Stephen (He/Him/His)
    User ID: U03LZKQSHEU

    # Lookup by user ID
    $ slack-get-user U03LZKQSHEU
    Name: Stephen Torres
    Email: stephen@bigapplerecsports.com
    Display: Stephen (He/Him/His)
    User ID: U03LZKQSHEU

    # JSON output
    $ slack-get-user stephen@bigapplerecsports.com --json
    {"id": "U03LZKQSHEU", "real_name": "Stephen Torres", ...}
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Optional, Dict, Any

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from shared_utils import load_environment
from config.slack import SlackConfig
from slack_sdk import WebClient
from slack_helpers import format_display


def is_email(value: str) -> bool:
    """Check if the value looks like an email address."""
    return '@' in value and '.' in value


def is_user_id(value: str) -> bool:
    """Check if the value looks like a Slack user ID (e.g., U03LZKQSHEU)."""
    return value.startswith('U') and len(value) == 11 and value.isalnum()


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


def lookup_user_by_email(client: WebClient, email: str, display: bool = True) -> Optional[Dict[str, Any]]:
    """Look up a Slack user by email address."""
    try:
        response = client.users_lookupByEmail(email=email)
        if response['ok']:
            return response['user']
        else:
            return None
    except Exception as e:
        if display:
            print(f"❌ Error looking up email: {e}", file=sys.stderr)
        return None


def lookup_user_by_id(client: WebClient, user_id: str, display: bool = True) -> Optional[Dict[str, Any]]:
    """Look up a Slack user by user ID."""
    try:
        response = client.users_info(user=user_id)
        if response['ok']:
            return response['user']
        else:
            return None
    except Exception as e:
        if display:
            print(f"❌ Error looking up user ID: {e}", file=sys.stderr)
        return None


def get_user(client: WebClient, identifier: str, display: bool = True) -> Optional[Dict[str, Any]]:
    """
    Look up a Slack user by email or user ID.
    
    Args:
        client: Initialized Slack WebClient
        identifier: Email address or user ID
        display: If True, print status messages and errors
        
    Returns:
        User dict if found, None otherwise
    """
    if is_email(identifier):
        if display:
            print(f"🔍 Looking up email: {identifier}", file=sys.stderr)
        return lookup_user_by_email(client, identifier, display=display)
    elif is_user_id(identifier):
        if display:
            print(f"🔍 Looking up user ID: {identifier}", file=sys.stderr)
        return lookup_user_by_id(client, identifier, display=display)
    else:
        if display:
            print(f"❌ Error: '{identifier}' doesn't look like an email or user ID", file=sys.stderr)
            print("   Email should contain '@' and '.'", file=sys.stderr)
            print("   User ID should start with 'U' and be 11 characters", file=sys.stderr)
        return None


def format_user(user: Dict[str, Any]) -> str:
    """Format user data for display (formatted output only)."""
    profile = user.get('profile', {})
    name = user.get('real_name', 'N/A')
    email = profile.get('email', 'N/A')
    display = profile.get('display_name', 'N/A')
    user_id = user.get('id', 'N/A')
    deleted = user.get('deleted', False)
    
    output = []
    output.append(f"Name: {name}")
    output.append(f"Email: {email}")
    output.append(f"Display: {display}")
    output.append(f"User ID: {user_id}")
    
    if deleted:
        output.append("⚠️  Status: DELETED")
    
    # Add optional fields if present
    title = profile.get('title')
    if title:
        output.append(f"Title: {title}")
    
    phone = profile.get('phone')
    if phone:
        output.append(f"Phone: {phone}")
    
    timezone = user.get('tz_label')
    if timezone:
        output.append(f"Timezone: {timezone}")
    
    return '\n'.join(output)


def prompt_for_input() -> str:
    """Prompt user for email or user ID."""
    print("Enter Slack user email or user ID:", file=sys.stderr)
    return input().strip()


def main():
    parser = argparse.ArgumentParser(
        description="Look up Slack user by email or user ID",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    slack-get-user stephen@bigapplerecsports.com
    slack-get-user U03LZKQSHEU
    slack-get-user --bot refunds U12345ABC
    slack-get-user --json stephen@example.com
        """
    )
    
    parser.add_argument(
        'identifier',
        nargs='?',
        help='Email address or user ID (if omitted, will prompt)'
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
    
    # Get identifier (from arg or prompt)
    identifier = args.identifier
    if not identifier:
        try:
            identifier = prompt_for_input()
        except (EOFError, KeyboardInterrupt):
            print("\n❌ Cancelled", file=sys.stderr)
            sys.exit(1)
    
    if not identifier:
        print("❌ Error: Email or user ID required", file=sys.stderr)
        sys.exit(1)
    
    # Get bot token
    try:
        token = get_bot_token(args.bot)
    except ValueError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)
    
    # Create Slack client
    client = WebClient(token=token)
    
    # Look up user
    user = get_user(client, identifier, display=not args.json)
    
    # Display result
    if user:
        if not args.json:
            print("", file=sys.stderr)  # Blank line before output
        print(format_display(user, formatter_func=format_user, should_format=not args.json))
        print()
        sys.exit(0)
    else:
        if not args.json:
            print(f"❌ User not found: {identifier}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

