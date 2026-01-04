#!/usr/bin/env python3
"""
Update Slack user profile fields.

Always shows a preview of changes before applying, then prompts for confirmation.

Usage:
    slack-update-user user@example.com --title "Commissioner"
    slack-update-user U01234ABCDE --title "Director of Kickball"
    slack-update-user user@example.com --title "Commissioner" --phone "+1-555-123-4567"
    slack-update-user user@example.com --status-text "BARS Leadership" --status-emoji ":tada:"
    
Examples:
    # Update title only (shows preview, then prompts for confirmation)
    slack-update-user chase@bigapplerecsports.com --title "Commissioner"
    
    # Update multiple fields
    slack-update-user chase@bigapplerecsports.com \
        --title "Commissioner of Dodgeball" \
        --phone "+1-555-123-4567" \
        --status-text "BARS Leadership Team"
    
    # Dry run only (preview without applying)
    slack-update-user chase@bigapplerecsports.com --title "Commissioner" --dry-run
    
    # Interactive mode
    slack-update-user
"""

import sys
import argparse
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent directory to path for backend imports
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from slack_get_user import get_user, get_bot_token
from slack_helpers import (
    dry_run_and_confirm,
    show_slack_user_context,
    build_profile_changes
)
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


def apply_profile_updates(client: WebClient, user: Dict[str, Any], profile_updates: Dict[str, str]) -> bool:
    """
    Apply profile updates to Slack user.
    
    Args:
        client: Initialized Slack WebClient
        user: Slack user dict from get_user()
        profile_updates: Dict of profile fields to update
        
    Returns:
        True if successful, False otherwise
    """
    user_id = user.get("id", "")
    
    try:
        response = client.users_profile_set(
            user=user_id,
            profile=profile_updates
        )
        
        if response["ok"]:
            return True
        else:
            print(f"❌ Error updating profile: {response.get('error', 'Unknown error')}", file=sys.stderr)
            return False
            
    except SlackApiError as e:
        print(f"❌ Slack API error: {e.response['error']}", file=sys.stderr)
        return False


def interactive_mode(client: WebClient, bot_name: str):
    """Interactive mode to prompt for user and updates."""
    print("🤖 Update Slack User Profile (Interactive Mode)")
    print(f"Bot: {bot_name}")
    print()
    
    # Get user identifier
    identifier = input("Enter user email or ID: ").strip()
    if not identifier:
        print("❌ No identifier provided", file=sys.stderr)
        sys.exit(1)
    
    # Look up user
    user = get_user(client, identifier, display=True)
    if not user:
        print(f"❌ User not found: {identifier}", file=sys.stderr)
        sys.exit(1)
    
    # Get current profile
    current_profile = user.get("profile", {})
    
    print(f"\n👤 Current profile for {user.get('real_name', 'Unknown')}:")
    print(f"   Title: {current_profile.get('title', '(none)')}")
    print(f"   Phone: {current_profile.get('phone', '(none)')}")
    print(f"   Status: {current_profile.get('status_text', '(none)')}")
    print()
    
    # Prompt for updates
    profile_updates = {}
    
    title = input(f"New title (leave blank to keep current): ").strip()
    if title:
        profile_updates["title"] = title
    
    phone = input(f"New phone (leave blank to keep current): ").strip()
    if phone:
        profile_updates["phone"] = phone
    
    status_text = input(f"New status text (leave blank to keep current): ").strip()
    if status_text:
        profile_updates["status_text"] = status_text
        
        status_emoji = input(f"Status emoji (e.g., :tada:, leave blank for none): ").strip()
        if status_emoji:
            if not status_emoji.startswith(":"):
                status_emoji = f":{status_emoji}"
            if not status_emoji.endswith(":"):
                status_emoji = f"{status_emoji}:"
            profile_updates["status_emoji"] = status_emoji
    
    if not profile_updates:
        print("\n⚠️  No updates specified")
        sys.exit(0)
    
    # Use shared dry-run and confirm workflow
    print()
    context = show_slack_user_context(user)
    changes = build_profile_changes(user, profile_updates)
    
    success = dry_run_and_confirm(
        title="Profile updates",
        changes=changes,
        apply_func=lambda: apply_profile_updates(client, user, profile_updates),
        context_info=context,
        dry_run=False
    )
    
    sys.exit(0 if success else 1)


def main():
    parser = argparse.ArgumentParser(
        description="Update Slack user profile fields",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Update title only
  slack-update-user chase@bigapplerecsports.com --title "Commissioner"
  
  # Update multiple fields
  slack-update-user chase@bigapplerecsports.com \\
      --title "Commissioner" \\
      --phone "+1-555-123-4567" \\
      --status-text "BARS Leadership Team"
  
  # Interactive mode
  slack-update-user
  
  # Dry run
  slack-update-user chase@bigapplerecsports.com --title "Commissioner" --dry-run
        """
    )
    
    parser.add_argument(
        "identifier",
        nargs="?",
        help="User email or Slack ID (if omitted, enters interactive mode)"
    )
    parser.add_argument(
        "--title",
        help="User's title/position"
    )
    parser.add_argument(
        "--phone",
        help="User's phone number"
    )
    parser.add_argument(
        "--status-text",
        help="User's status text"
    )
    parser.add_argument(
        "--status-emoji",
        help="User's status emoji (e.g., :tada:)"
    )
    parser.add_argument(
        "--bot",
        default="Leadership",
        choices=["Leadership", "Dev", "Exec", "Refunds", "Registrations", "Web"],
        help="Slack bot to use (default: Leadership)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without prompting to apply (always shows preview first)"
    )
    
    args = parser.parse_args()
    
    # Get bot token
    try:
        token = get_bot_token(args.bot.lower())
    except ValueError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)
    
    client = WebClient(token=token)
    
    # Interactive mode if no identifier provided
    if not args.identifier:
        interactive_mode(client, args.bot)
        return
    
    # Look up user (display=False to avoid duplicate messages)
    user = get_user(client, args.identifier, display=False)
    if not user:
        print(f"❌ User not found: {args.identifier}", file=sys.stderr)
        sys.exit(1)
    
    print(f"✅ Found user: {user.get('real_name', 'Unknown')} ({user.get('id', 'Unknown')})")
    print()
    
    # Build profile updates
    profile_updates = {}
    if args.title:
        profile_updates["title"] = args.title
    if args.phone:
        profile_updates["phone"] = args.phone
    if args.status_text:
        profile_updates["status_text"] = args.status_text
    if args.status_emoji:
        emoji = args.status_emoji
        if not emoji.startswith(":"):
            emoji = f":{emoji}"
        if not emoji.endswith(":"):
            emoji = f"{emoji}:"
        profile_updates["status_emoji"] = emoji
    
    if not profile_updates:
        print("⚠️  No profile updates specified. Use --title, --phone, --status-text, or --status-emoji", file=sys.stderr)
        print("Or run without arguments for interactive mode", file=sys.stderr)
        sys.exit(1)
    
    # Use shared dry-run and confirm workflow
    context = show_slack_user_context(user)
    changes = build_profile_changes(user, profile_updates)
    
    success = dry_run_and_confirm(
        title="Profile updates",
        changes=changes,
        apply_func=lambda: apply_profile_updates(client, user, profile_updates),
        context_info=context,
        dry_run=args.dry_run
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

