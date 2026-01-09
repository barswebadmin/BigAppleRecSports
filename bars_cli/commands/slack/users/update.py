"""Update Slack user profile command."""
import json
import re
import sys
from typing import Dict, Any, Optional

import click
from slack_sdk.errors import SlackApiError

from bars_cli.models.slack_user import SlackUser, SlackUserProfile
from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.decorators.profile_options import profile_options_from_model
from bars_cli._core.prompts import prompt_text_input, prompt_confirmation, prompt_select_from_options, EXIT_SENTINEL
from bars_cli._core.param_types import SLACK_USER_IDENTIFIER

from ..utils import handle_slack_api_error
from .get import get_user_cmd


def show_profile_changes(
    user: SlackUser,
    profile_updates: Dict[str, str],
    context_info: Optional[Dict[str, str]] = None
) -> bool:
    """
    Display what profile changes will be made.
    
    Returns:
        True if there are actual changes, False if all values are identical
    """
    # Dynamically get current values from profile
    current_profile = {}
    for field in profile_updates.keys():
        current_value = getattr(user.profile, field, None)
        current_profile[field] = current_value
    
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


def format_option(field: str, value: str) -> str:
    """
    Format a field option with current value.
    
    Args:
        field: Field name (e.g., 'first_name', 'email')
        value: Current value to display
        
    Returns:
        Formatted string like "First Name (Current: value)" or "First Name (Current: (none))"
    """
    # Split on underscore and capitalize first letter of each word
    formatted_field = ' '.join(word.capitalize() for word in field.split('_'))
    current_value = value if value else "(none)"
    return f"{formatted_field} (Current: {current_value})"


def prompt_and_update_field(
    field_name: str,
    current_value: str,
    prompt_text: str,
    profile_updates: Dict[str, Any]
) -> bool:
    """
    Prompt for a new field value and add to profile_updates if different.
    
    Args:
        field_name: Field name (e.g., 'first_name', 'email')
        current_value: Current value (may be empty string or '(none)')
        prompt_text: Prompt text for user input
        profile_updates: Dict to update with new value
        
    Returns:
        True if field was updated, False otherwise
    """
    # Normalize current_value - treat empty string and '(none)' as empty
    normalized_current = current_value if current_value and current_value != '(none)' else ''
    default_value = normalized_current
    
    new_value = prompt_text_input(prompt_text, default_value=default_value)
    
    # Only update if new value is different from current
    if new_value and new_value != normalized_current:
        profile_updates[field_name] = new_value
        return True
    
    return False


def extract_pronouns_from_display_name(display_name: str) -> Optional[str]:
    """Extract pronouns from display_name if present (typically in parentheses)."""
    if not display_name:
        return None
    # Match pattern like "Name (pronouns)" or "Name (He/Him/His)"
    match = re.search(r'\(([^)]+)\)', display_name)
    if match:
        return match.group(1)
    return None


def append_pronouns_to_display_name(display_name: str, pronouns: Optional[str] = None) -> str:
    """
    Append or replace pronouns in display_name.
    
    If pronouns are provided, removes any existing parentheses and appends new ones.
    If pronouns are None/empty, removes existing parentheses.
    
    Args:
        display_name: Current display_name (may already have pronouns in parentheses)
        pronouns: New pronouns to append, or None to remove
        
    Returns:
        Updated display_name with pronouns appended or removed
    """
    if not display_name:
        return display_name
    
    # Remove existing parentheses and any trailing whitespace
    base_name = re.sub(r'\s*\([^)]+\)\s*$', '', display_name).rstrip()
    
    # If no pronouns provided, return base name without parentheses
    if not pronouns:
        return base_name
    
    # Append pronouns in parentheses
    return f"{base_name} ({pronouns})"


def sync_pronouns_with_display_name(
    profile_updates: Dict[str, Any],
    user: SlackUser,
    pronouns: Optional[str] = None
) -> None:
    """
    Sync pronouns with display_name in profile_updates.
    
    If pronouns are provided, updates display_name to include them.
    If display_name is updated and pronouns exist, preserves pronouns in display_name.
    
    Args:
        profile_updates: Dictionary of profile updates to modify
        user: Current SlackUser instance
        pronouns: Optional new pronouns value (if None, uses current profile pronouns)
    """
    if pronouns is None:
        pronouns = getattr(user.profile, 'pronouns', None)
    
    # Get display_name to update (from updates or current profile)
    display_name_to_update = profile_updates.get('display_name') or user.profile.display_name or ""
    
    # Append pronouns to display_name
    updated_display_name = append_pronouns_to_display_name(display_name_to_update, pronouns)
    
    if updated_display_name:
        profile_updates["display_name"] = updated_display_name
        profile_updates["display_name_normalized"] = updated_display_name


def build_profile_updates_from_flags(
    profile_fields: Dict[str, Any],
    user: SlackUser
) -> Dict[str, Any]:
    """
    Build profile_updates dictionary from command-line flags.
    
    Handles special formatting (e.g., status_emoji) and syncs pronouns with display_name.
    Also handles custom fields if title appears to be a custom field.
    
    Args:
        profile_fields: Dictionary of field values from command-line flags
        user: Current SlackUser instance
        
    Returns:
        Dictionary of profile updates ready for API call
    """
    profile_updates = {}
    
    # Check if title might be a custom field (if user has custom fields with title value)
    title_custom_field_id = None
    if 'title' in profile_fields and profile_fields['title']:
        # Check if there's a custom field that matches the current title
        # This is a heuristic - we'll try updating both standard and custom field
        if hasattr(user, 'profile') and hasattr(user.profile, '__dict__'):
            # Try to find custom field ID for title (common pattern: Xf03VDUS6D17)
            # We'll update both standard title and check response for custom field
            pass
    
    for field, value in profile_fields.items():
        if value:
            # Special handling for status_emoji (ensure proper format)
            if field == 'status_emoji':
                emoji = value
                if not emoji.startswith(":"):
                    emoji = f":{emoji}"
                if not emoji.endswith(":"):
                    emoji = f"{emoji}:"
                profile_updates[field] = emoji
            else:
                profile_updates[field] = value
    
    # Sync pronouns with display_name if pronouns are being updated
    if 'pronouns' in profile_updates:
        sync_pronouns_with_display_name(profile_updates, user, profile_updates['pronouns'])
    
    # If display_name is being updated, preserve pronouns from profile
    if 'display_name' in profile_updates and 'pronouns' not in profile_updates:
        sync_pronouns_with_display_name(profile_updates, user)
    
    return profile_updates


def lookup_user_by_identifier(
    ctx: click.Context,
    identifier: Optional[dict],
    json_output: bool
) -> SlackUser:
    """
    Look up a user by identifier, handling errors appropriately.
    
    Args:
        ctx: Click context
        identifier: User identifier dict (email or user_id)
        json_output: Whether to output JSON format errors
    
    Returns:
        SlackUser instance
        
    Raises:
        SystemExit: If identifier is missing (JSON mode) or user lookup fails
    """
    # Get identifier if not provided
    if not identifier:
        if json_output:
            click.echo('{"error": "Identifier required in JSON mode"}', err=True)
            sys.exit(1)
        identifier_str = prompt_text_input("Enter user email or ID")
        identifier = {"email": identifier_str} if "@" in identifier_str else {"user_id": identifier_str}
    
    # Invoke get command with display=False, exit=False, json_output=False
    identifier_value = identifier.get("email") or identifier.get("user_id")
    child_ctx = get_user_cmd.make_context('get', [str(identifier_value)], parent=ctx)
    child_ctx.ensure_object(dict)
    if ctx.obj:
        child_ctx.obj.update(ctx.obj)
    child_ctx.obj['display_override'] = False
    child_ctx.obj['exit_override'] = False
    child_ctx.obj['json_output'] = False
    
    try:
        return get_user_cmd.invoke(child_ctx)
    except (click.ClickException, ValueError, Exception) as e:
        lookup_value = identifier.get("email") or identifier.get("user_id")
        if json_output:
            error_msg = str(e) if str(e) else f"User lookup failed: {lookup_value}"
            click.echo(json.dumps({"error": error_msg}, indent=2), err=True)
        else:
            click.echo(f"❌ {str(e) if str(e) else f'User lookup failed: {lookup_value}'}", err=True)
        sys.exit(1)


def handle_pronouns_update(
    profile_updates: Dict[str, Any],
    current_pronouns: Optional[str],
    current_display_name: str
) -> None:
    """
    Handle pronouns field update, syncing with display_name.
    
    Args:
        profile_updates: Dictionary to update with changes
        current_pronouns: Current pronouns value
        current_display_name: Current display_name value
    """
    new_pronouns = prompt_text_input(
        "New pronouns (e.g., He/Him/His, She/Her/Hers, They/Them/Theirs)",
        default_value=current_pronouns or ""
    )
    
    if new_pronouns != current_pronouns:
        profile_updates["pronouns"] = new_pronouns if new_pronouns else ""
        
        # Update display_name to append/replace pronouns
        display_name_to_update = profile_updates.get("display_name", current_display_name)
        if display_name_to_update == '(none)':
            display_name_to_update = ""
        
        updated_display_name = append_pronouns_to_display_name(
            display_name_to_update,
            new_pronouns if new_pronouns else None
        )
        
        if updated_display_name:
            profile_updates["display_name"] = updated_display_name
            profile_updates["display_name_normalized"] = updated_display_name


def handle_display_name_update(
    profile_updates: Dict[str, Any],
    current_display_name: str,
    current_profile: SlackUserProfile
) -> None:
    """
    Handle display_name field update, preserving pronouns.
    
    Args:
        profile_updates: Dictionary to update with changes
        current_display_name: Current display_name value
        current_profile: Current user profile
    """
    new_display_name = prompt_text_input(
        "New display name",
        default_value=current_display_name if current_display_name != '(none)' else ""
    )
    
    if new_display_name and new_display_name != current_display_name:
        # Get pronouns from current profile or pending updates
        pronouns_to_preserve = getattr(current_profile, 'pronouns', None)
        if not pronouns_to_preserve and "pronouns" in profile_updates:
            pronouns_to_preserve = profile_updates["pronouns"]
        
        # Remove any existing parentheses from the new display_name
        base_display_name = re.sub(r'\s*\([^)]+\)\s*$', '', new_display_name).rstrip()
        
        # Append pronouns if they exist
        if pronouns_to_preserve:
            updated_display_name = f"{base_display_name} ({pronouns_to_preserve})"
        else:
            updated_display_name = base_display_name
        
        profile_updates["display_name"] = updated_display_name
        profile_updates["display_name_normalized"] = updated_display_name


def collect_interactive_updates(user: SlackUser) -> Dict[str, Any]:
    """
    Collect profile updates interactively from user.
    
    Args:
        user: Current SlackUser instance
        
    Returns:
        Dictionary of profile updates
    """
    profile_updates = {}
    current_profile = user.profile
    
    # Extract current values
    current_values = {
        'first_name': current_profile.first_name or '',
        'last_name': current_profile.last_name or '',
        'pronouns': getattr(current_profile, 'pronouns', None) or extract_pronouns_from_display_name(current_profile.display_name or ''),
        'display_name': current_profile.display_name or '',
        'email': current_profile.email or '',
        'title': current_profile.title or '',
        'phone': current_profile.phone or '',
    }
    
    # Field selection options with current values inline
    field_options = [
        format_option("first_name", current_values['first_name']),
        format_option("last_name", current_values['last_name']),
        format_option("pronouns", current_values['pronouns'] or ''),
        format_option("display_name", current_values['display_name'] or ''),
        format_option("email", current_values['email']),
        format_option("title", current_values['title']),
        format_option("phone", current_values['phone']),
        "Image"
    ]
    
    # Field handler dispatch table
    field_handlers = {
        "First Name": lambda: prompt_and_update_field("first_name", current_values['first_name'], "New first name", profile_updates),
        "Last Name": lambda: prompt_and_update_field("last_name", current_values['last_name'], "New last name", profile_updates),
        "Pronouns": lambda: handle_pronouns_update(profile_updates, current_values['pronouns'], current_values['display_name']),
        "Display Name": lambda: handle_display_name_update(profile_updates, current_values['display_name'], current_profile),
        "Email": lambda: prompt_and_update_field("email", current_values['email'], "New email", profile_updates),
        "Title": lambda: prompt_and_update_field("title", current_values['title'], "New title", profile_updates),
        "Phone": lambda: prompt_and_update_field("phone", current_values['phone'], "New phone", profile_updates),
        "Image": lambda: click.echo("⚠️  Image updates are not yet supported via CLI\n💡 Use Slack's UI to update profile images"),
    }
    
    # Loop to allow multiple field updates
    while True:
        selected_field = prompt_select_from_options(
            "Select field to update",
            field_options,
            show_current="Select a field to update"
        )
        
        if selected_field == EXIT_SENTINEL:
            break
        
        # Extract field name from option (remove "(Current: ...)" part)
        field_name = selected_field.split(" (Current:")[0].strip()
        
        # Dispatch to appropriate handler
        handler = field_handlers.get(field_name)
        if handler:
            handler()
        else:
            click.echo(f"⚠️  Unknown field: {field_name}")
        
        # Ask if user wants to update another field
        click.echo()
        continue_updating = prompt_confirmation("Update another field?", default=False)
        if not continue_updating:
            break
    
    return profile_updates


def _has_actual_changes(user: SlackUser, profile_updates: Dict[str, Any]) -> bool:
    """Check if profile_updates contain any actual changes from current profile."""
    current_profile = user.profile
    for field, new_value in profile_updates.items():
        current_value = getattr(current_profile, field, None)
        if str(current_value) != str(new_value):
            return True
    return False


def _handle_no_changes(user: SlackUser, profile_updates: Dict[str, Any], json_output: bool) -> None:
    """Handle the case where no actual changes are detected."""
    if json_output:
        click.echo(json.dumps({
            "error": "No actual changes to make",
            "message": "All provided values match current profile values"
        }, indent=2), err=True)
        sys.exit(0)
    
    context = {
        "User": f"{user.real_name or 'Unknown'} ({user.name})",
        "Email": user.profile.email or 'N/A'
    }
    show_profile_changes(user, profile_updates, context)
    click.echo("\n⚠️  No actual changes to make")
    
    def validate_choice(value: str) -> tuple[bool, Optional[str]]:
        normalized = value.lower().strip()
        if normalized in ['c', 'continue', 'e', 'exit']:
            return True, None
        return False, "Please enter 'c' to continue or 'e' to exit"
    
    choice = prompt_text_input(
        "Continue (c) or Exit (e)? [E]",
        default_value="e",
        validate_func=validate_choice
    )
    
    if choice.lower().strip()[0] == 'e':
        sys.exit(0)


def _execute_profile_update(
    bot: Any,
    user: SlackUser,
    profile_updates: Dict[str, Any],
    json_output: bool
) -> None:
    """Execute the profile update API call and handle the response."""
    if not json_output:
        click.echo("\n🔍 Applying changes and logging response...")
        # Check which token will be used
        bot_token = bot.client.token
        user_token = getattr(bot.client, '_user_token', None)
        token_preview = f"{bot_token[:10]}...{bot_token[-4:]}" if bot_token and len(bot_token) > 14 else "***"
        token_type = "Bot Token" if bot_token and bot_token.startswith('xoxb-') else "User Token" if bot_token and bot_token.startswith('xoxp-') else "Unknown"
        click.echo(f"🔑 Bot Token: {token_preview} ({token_type})")
        if user_token:
            user_token_preview = f"{user_token[:10]}...{user_token[-4:]}" if len(user_token) > 14 else "***"
            click.echo(f"🔑 User Token: {user_token_preview} (will be used for users.profile.set)")
        else:
            click.echo(f"⚠️  No User Token configured - users.profile.set requires User Token!")
        click.echo("\n📤 Payload being sent:")
        click.echo(json.dumps({"user": user.id, "profile": profile_updates}, indent=2))
        click.echo()
    
    # Check token info before making the call
    if not json_output:
        user_token = getattr(bot.client, '_user_token', None)
        if user_token:
            # Try to get info about the token owner
            try:
                import requests
                headers = {'Authorization': f'Bearer {user_token}', 'Content-Type': 'application/json'}
                auth_response = requests.post('https://slack.com/api/auth.test', headers=headers, timeout=5)
                if auth_response.status_code == 200:
                    auth_data = auth_response.json()
                    if auth_data.get('ok'):
                        token_user_id = auth_data.get('user_id')
                        token_user_name = auth_data.get('user')
                        click.echo(f"🔍 User Token info:")
                        click.echo(f"   Token belongs to user: {token_user_name} ({token_user_id})")
                        click.echo(f"   User being updated: {user.name} ({user.id})")
                        if token_user_id == user.id:
                            click.echo(f"   ⚠️  Token is for the same user - this should work for self-updates")
                        else:
                            click.echo(f"   ✅ Token is for different user - should work for updating others")
                        click.echo()
            except Exception as e:
                click.echo(f"   ⚠️  Could not verify token owner: {e}")
                click.echo()
    
    # Log the exact call being made
    if not json_output:
        click.echo(f"🔍 Calling update_user_profile with:")
        click.echo(f"   user_id: {user.id}")
        click.echo(f"   profile: {json.dumps(profile_updates, indent=2)}")
        click.echo()
    
    result = bot.client.update_user_profile(
        user_id=user.id,
        profile=profile_updates
    )
    
    # Log the raw result
    if not json_output:
        click.echo(f"📥 Raw result from update_user_profile:")
        click.echo(f"   success: {result.get('success')}")
        click.echo(f"   error: {result.get('error', 'None')}")
        click.echo(f"   response type: {type(result.get('response'))}")
        click.echo()
    
    if result.get("success"):
        response = result.get("response", {})
        response_data = response.data if hasattr(response, 'data') else dict(response) if hasattr(response, '__dict__') else response
        
        # Check if the update actually took effect
        update_succeeded = True
        mismatched_fields = []
        if isinstance(response_data, dict) and 'profile' in response_data:
            returned_profile = response_data['profile']
            for field, requested_value in profile_updates.items():
                returned_value = returned_profile.get(field)
                if returned_value != requested_value:
                    update_succeeded = False
                    mismatched_fields.append((field, requested_value, returned_value))
        
        # Log response details
        if not json_output:
            click.echo(f"📥 Response details:")
            click.echo(f"   response type: {type(response)}")
            click.echo(f"   has 'data' attr: {hasattr(response, 'data')}")
            if hasattr(response, 'data'):
                click.echo(f"   response.data type: {type(response.data)}")
            click.echo(f"   response_data keys: {list(response_data.keys()) if isinstance(response_data, dict) else 'N/A'}")
            if isinstance(response_data, dict) and 'profile' in response_data:
                returned_profile = response_data['profile']
                click.echo(f"   response_data['profile']['title']: {returned_profile.get('title', 'N/A')}")
                if 'fields' in returned_profile:
                    click.echo(f"   Custom fields found: {list(returned_profile['fields'].keys())}")
            click.echo()
        
        if json_output:
            click.echo(json.dumps(response_data, indent=2, default=str))
        else:
            if update_succeeded:
                click.echo("✅ Changes applied successfully")
            else:
                click.echo("⚠️  API returned success, but response shows old values:")
                for field, requested, returned in mismatched_fields:
                    click.echo(f"   {field}: requested '{requested}', but response shows '{returned}'")
                click.echo("\n🔄 Verifying update by fetching user again...")
                try:
                    # Fetch the user again to see if the update actually took effect
                    # (Slack API response might show cached/old values)
                    import time
                    time.sleep(0.5)  # Brief delay to allow Slack to process
                    refreshed_user = bot.lookup_user(user.id)
                    if refreshed_user:
                        # Handle both SlackUser object and dict returns
                        if isinstance(refreshed_user, dict):
                            refreshed_title = refreshed_user.get('profile', {}).get('title')
                        else:
                            refreshed_title = refreshed_user.profile.title if hasattr(refreshed_user, 'profile') else None
                        
                        if refreshed_title == profile_updates.get('title'):
                            click.echo(f"✅ Verification: Title was actually updated to '{refreshed_title}'")
                            click.echo("   (The API response showed old cached data, but the update worked)")
                        else:
                            click.echo(f"❌ Verification: Title is still '{refreshed_title}' (update did not take effect)")
                            # Check if title is a custom field
                            if isinstance(response_data, dict) and 'profile' in response_data:
                                profile = response_data['profile']
                                if 'fields' in profile and 'Xf03VDUS6D17' in profile['fields']:
                                    custom_field_value = profile['fields']['Xf03VDUS6D17'].get('value')
                                    click.echo(f"   Custom field Xf03VDUS6D17 value: '{custom_field_value}'")
                                    click.echo("\n💡 The 'title' field appears to be a custom field in your workspace.")
                                    click.echo("   The standard 'title' field may not be updating because:")
                                    click.echo("   1. 'Title' is configured as a custom field (ID: Xf03VDUS6D17)")
                                    click.echo("   2. Custom fields require updating via the 'fields' parameter")
                                    click.echo("   3. Check Slack Admin → Configure Profile to see field configuration")
                            click.echo("\n💡 Possible causes:")
                            # Check if User Token is from a bot user
                            user_token = getattr(bot.client, '_user_token', None)
                            if user_token:
                                click.echo("   1. ⚠️  User Token may not have sufficient permissions")
                                click.echo("      → User Tokens are tied to the user who authorized them")
                                click.echo("      → To update other users' profiles, you need:")
                                click.echo("        • `users.profile:write` scope (you have this)")
                                click.echo("        • `admin.users:write` scope (may be missing)")
                                click.echo("        • Token from workspace Owner/Primary Owner (not just Admin)")
                                click.echo("        • Workspace on paid plan")
                                click.echo("      → Go to: https://api.slack.com/apps → Your App → OAuth & Permissions")
                                click.echo("      → Add `admin.users:write` to User Token Scopes")
                                click.echo("      → Reinstall app as Owner/Primary Owner (not Admin)")
                            click.echo("   2. Field might be locked by admin (check Slack Admin → Profile Settings)")
                            click.echo("   3. Token might not have sufficient permissions or role level")
                            click.echo("   4. Field might be synced from external system (SCIM/SSO)")
                            click.echo("   5. Workspace plan restrictions (updating other users requires paid plan)")
                    else:
                        click.echo("⚠️  Could not verify - failed to fetch user")
                except Exception as e:
                    click.echo(f"⚠️  Could not verify update: {e}")
            click.echo("\n📋 Raw API Response:")
            click.echo(json.dumps(response_data, indent=2, default=str))
            click.echo()
        sys.exit(0)
    else:
        error_msg = result.get("error", "Unknown error")
        scope_info = result.get("scope_info", {})
        
        if json_output:
            output = {
                'error': error_msg,
                'error_type': 'slack_api_error',
                'response': result.get("response", {})
            }
            if scope_info:
                output['scope_info'] = scope_info
            click.echo(json.dumps(output, indent=2, default=str), err=True)
        else:
            click.echo(f"❌ {error_msg}", err=True)
            if scope_info:
                click.echo(f"\n🔑 Token Type: {scope_info.get('token_type', 'Unknown')}", err=True)
                click.echo(f"🔑 Token: {scope_info.get('token_preview', 'Unknown')}", err=True)
                click.echo(f"📋 Current Scopes: {', '.join(scope_info.get('current_scopes', [])) if scope_info.get('current_scopes') else 'none'}", err=True)
                if scope_info.get('required_scope'):
                    click.echo(f"⚠️  Required Scope: {scope_info['required_scope']}", err=True)
                if scope_info.get('missing_scopes'):
                    click.echo(f"❌ Missing Scopes: {', '.join(scope_info['missing_scopes'])}", err=True)
                    click.echo("\n💡 To fix:", err=True)
                    if scope_info['token_type'] == 'Bot Token' and scope_info.get('required_scope') == 'users.profile:write':
                        click.echo("   users.profile:write is only available for User Token Scopes", err=True)
                        click.echo("   1. Go to OAuth & Permissions → User Token Scopes", err=True)
                        click.echo("   2. Add 'users.profile:write' scope", err=True)
                        click.echo("   3. Reinstall the app to get a user token", err=True)
                    else:
                        scope_type = 'User Token Scopes' if scope_info['token_type'] == 'User Token' else 'Bot Token Scopes'
                        click.echo(f"   1. Go to OAuth & Permissions → {scope_type}", err=True)
                        click.echo(f"   2. Add the missing scope(s): {', '.join(scope_info['missing_scopes'])}", err=True)
                        click.echo("   3. Reinstall the app to get a new token", err=True)
            click.echo(f"\n📋 Full Error Response:", err=True)
            click.echo(json.dumps(result.get("response", {}), indent=2, default=str), err=True)
        sys.exit(1)


@click.command('update')
@handle_display_options(display=True, exit_on_error=True)
@click.argument('identifier', type=SLACK_USER_IDENTIFIER, required=False)
@profile_options_from_model(SlackUserProfile, include_optional=True)
@click.pass_context
def update_user_cmd(
    ctx: click.Context,
    identifier: Optional[dict],
    **profile_fields
) -> Optional[SlackUser]:
    """
    Update Slack user profile fields using the leadership bot.
    
    Always shows a preview of changes before applying.
    
    IDENTIFIER: User's email address or Slack user ID (e.g., 'U01ABC123').
                If omitted, will prompt for input.
    
    Examples:
      bars slack user update chase@bigapplerecsports.com --title "Commissioner"
      bars slack user update U03LZKQSHEU --title "Director of Kickball"
      bars slack user update user@example.com --title "Commissioner" --phone "+1-555-123-4567"
      bars slack user update user@example.com --status-text "BARS Leadership" --status-emoji ":tada:"
    """
    json_output = ctx.obj.get('json_output', False) if ctx.obj else False
    
    try:
        # Look up user by identifier
        user = lookup_user_by_identifier(ctx, identifier, json_output)
        
        # Build profile updates from flags or collect interactively
        profile_updates = build_profile_updates_from_flags(profile_fields, user)
        
        # If no flags provided, enter interactive mode
        if not profile_updates:
            if json_output:
                click.echo(json.dumps({
                    "error": "No updates specified",
                    "message": "In JSON mode, interactive prompts are not available. Provide field updates via command-line flags.",
                    "example": "bars slack user update user@example.com --json --title \"New Title\" --phone \"+1-555-1234\""
                }, indent=2), err=True)
                sys.exit(1)
            
            profile_updates = collect_interactive_updates(user)
            
            if not profile_updates:
                click.echo("\n⚠️  No updates specified")
                sys.exit(0)
        
        # Validate that there are actual changes to make
        if not _has_actual_changes(user, profile_updates):
            _handle_no_changes(user, profile_updates, json_output)
        
        # Show preview only in non-JSON mode
        if not json_output:
            context = {
                "User": f"{user.real_name or 'Unknown'} ({user.name})",
                "Email": user.profile.email or 'N/A'
            }
            show_profile_changes(user, profile_updates, context)
        
        # Perform API call and handle response
        bot = ctx.meta['admin_bot']
        _execute_profile_update(bot, user, profile_updates, json_output)
    
    except SlackApiError as e:
        # Get token from context if available
        token = None
        try:
            bot = ctx.meta.get('admin_bot')
            if bot and hasattr(bot, 'client') and hasattr(bot.client, 'token'):
                token = bot.client.token
        except Exception:
            pass
        
        handle_slack_api_error(e, json_output=json_output, token=token, api_method='users.profile.set')
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo("\n❌ Cancelled", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
