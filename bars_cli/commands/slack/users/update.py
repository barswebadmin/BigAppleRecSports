"""Update Slack user profile command."""
import sys
import json
from typing import Dict, Any, Optional

import click
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

sys.path.insert(0, 'backend')

from modules.integrations.slack.services.user_lookup_service import UserLookupService
from ..utils import get_bot_token, handle_slack_api_error
from bars_cli._core.prompts import prompt_text_input, prompt_confirmation


def show_profile_changes(
    user: Dict[str, Any],
    profile_updates: Dict[str, str],
    context_info: Optional[Dict[str, str]] = None
) -> bool:
    """
    Display what profile changes will be made.
    
    Returns:
        True if there are actual changes, False if all values are identical
    """
    current_profile = user.get('profile', {})
    
    # Show context
    if context_info:
        for key, value in context_info.items():
            icon = "👤" if key == "User" else "📧" if key == "Email" else "ℹ️"
            click.echo(f"{icon} {key}: {value}")
        click.echo()
    
    # Show changes
    click.echo("🔄 Profile updates that will be made:")
    click.echo("-" * 60)
    
    has_changes = False
    for field, new_value in profile_updates.items():
        old_value = current_profile.get(field, "")
        old_display = old_value if old_value else "(none)"
        new_display = new_value if new_value else "(none)"
        
        if old_value == new_value:
            click.echo(f"  {field}: '{new_display}' (no change)")
        else:
            click.echo(f"  {field}:")
            click.echo(f"    Old: '{old_display}'")
            click.echo(f"    New: '{new_display}'")
            has_changes = True
    
    click.echo("-" * 60)
    
    return has_changes


def apply_profile_updates(client: WebClient, user: Dict[str, Any], profile_updates: Dict[str, str]) -> bool:
    """
    Apply profile updates to Slack user.
    
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
            click.echo(f"❌ Error updating profile: {response.get('error', 'Unknown error')}", err=True)
            return False
            
    except SlackApiError as e:
        click.echo(f"❌ Slack API error: {e.response['error']}", err=True)
        return False


@click.command('update')
@click.argument('identifier', required=False)
@click.option('--title', help="User's title/position")
@click.option('--phone', help="User's phone number")
@click.option('--status-text', help="User's status text")
@click.option('--status-emoji', help="User's status emoji (e.g., :tada:)")
@click.option('--bot', default='leadership', help='Which bot to use (default: leadership)')
@click.option('--dry-run', is_flag=True, help='Preview changes without applying')
@click.pass_context
def update_user_cmd(
    ctx: click.Context,
    identifier: str,
    title: str,
    phone: str,
    status_text: str,
    status_emoji: str,
    bot: str,
    dry_run: bool
):
    """
    Update Slack user profile fields.
    
    Always shows a preview of changes before applying.
    
    IDENTIFIER: User's email address or Slack user ID (e.g., 'U01ABC123').
                If omitted, will prompt for input.
    
    Examples:
      bars slack user update chase@bigapplerecsports.com --title "Commissioner"
      bars slack user update U03LZKQSHEU --title "Director of Kickball"
      bars slack user update user@example.com --title "Commissioner" --phone "+1-555-123-4567"
      bars slack user update user@example.com --status-text "BARS Leadership" --status-emoji ":tada:"
      bars slack user update user@example.com --title "Commissioner" --dry-run
    """
    json_output = ctx.obj.get('json_output', False) if ctx.obj else False
    
    try:
        token = get_bot_token(bot)
        client = WebClient(token=token)
        service = UserLookupService(token)
        
        # Get identifier if not provided
        if not identifier:
            if json_output:
                click.echo('{"error": "Identifier required in JSON mode"}', err=True)
                sys.exit(1)
            identifier = prompt_text_input("Enter user email or ID")
        
        # Look up user
        if not json_output:
            click.echo(f"🔍 Looking up user: {identifier}", err=True)
        
        # Use service to look up user (handles email vs ID)
        user_data = None
        if '@' in identifier:
            user_data = service.lookup_user_by_email(identifier)
        else:
            user_data = service.lookup_user_by_id(identifier)
        
        if not user_data:
            click.echo(f"❌ User not found: {identifier}", err=True)
            sys.exit(1)
        
        if not json_output:
            real_name = user_data.get('real_name', 'Unknown')
            user_id = user_data.get('id', 'Unknown')
            click.echo(f"✅ Found user: {real_name} ({user_id})\n", err=True)
        
        # Build profile updates
        profile_updates = {}
        if title:
            profile_updates["title"] = title
        if phone:
            profile_updates["phone"] = phone
        if status_text:
            profile_updates["status_text"] = status_text
        if status_emoji:
            emoji = status_emoji
            if not emoji.startswith(":"):
                emoji = f":{emoji}"
            if not emoji.endswith(":"):
                emoji = f"{emoji}:"
            profile_updates["status_emoji"] = emoji
        
        # If no flags provided, enter interactive mode
        if not profile_updates:
            if json_output:
                click.echo('{"error": "No updates specified"}', err=True)
                sys.exit(1)
            
            current_profile = user_data.get("profile", {})
            click.echo(f"👤 Current profile for {user_data.get('real_name', 'Unknown')}:")
            click.echo(f"   Title: {current_profile.get('title', '(none)')}")
            click.echo(f"   Phone: {current_profile.get('phone', '(none)')}")
            click.echo(f"   Status: {current_profile.get('status_text', '(none)')}")
            click.echo()
            
            # Prompt for updates
            title_input = prompt_text_input("New title (leave blank to keep current)", allow_empty=True)
            if title_input:
                profile_updates["title"] = title_input
            
            phone_input = prompt_text_input("New phone (leave blank to keep current)", allow_empty=True)
            if phone_input:
                profile_updates["phone"] = phone_input
            
            status_text_input = prompt_text_input("New status text (leave blank to keep current)", allow_empty=True)
            if status_text_input:
                profile_updates["status_text"] = status_text_input
                
                status_emoji_input = prompt_text_input("Status emoji (e.g., :tada:, leave blank for none)", allow_empty=True)
                if status_emoji_input:
                    emoji = status_emoji_input
                    if not emoji.startswith(":"):
                        emoji = f":{emoji}"
                    if not emoji.endswith(":"):
                        emoji = f"{emoji}:"
                    profile_updates["status_emoji"] = emoji
            
            if not profile_updates:
                click.echo("\n⚠️  No updates specified")
                sys.exit(0)
        
        # Show preview
        context = {
            "User": f"{user_data.get('real_name', 'Unknown')} ({user_data.get('name', 'Unknown')})",
            "Email": user_data.get('profile', {}).get('email', 'N/A')
        }
        
        has_changes = show_profile_changes(user_data, profile_updates, context)
        
        if not has_changes:
            click.echo("\n⚠️  No actual changes to make")
            sys.exit(0)
        
        # If dry-run, stop here
        if dry_run:
            click.echo("\n🔍 Dry run - no changes made")
            sys.exit(0)
        
        # Confirm before applying
        if not prompt_confirmation("Press Enter to apply changes, or Ctrl+C to cancel"):
            click.echo("❌ Cancelled")
            sys.exit(1)
        
        # Apply changes
        click.echo("\n⏳ Applying changes...")
        success = apply_profile_updates(client, user_data, profile_updates)
        
        if success:
            click.echo("✅ Changes applied successfully!")
            sys.exit(0)
        else:
            sys.exit(1)
    
    except SlackApiError as e:
        handle_slack_api_error(e, json_output)
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo("\n❌ Cancelled", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)

