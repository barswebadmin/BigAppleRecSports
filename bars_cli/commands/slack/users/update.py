"""Update Slack user profile command."""
import json
import re
import sys
from typing import Dict, Any, Optional, cast

import click
from slack_sdk.errors import SlackApiError

from bars_cli.backend_services.slack.models.slack_user import SlackUser, SlackUserProfile
from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.decorators.profile_options import profile_options_from_model
from bars_cli._core.prompts import prompt_text_input, prompt_confirmation, prompt_select_from_options
from bars_cli._core.param_types import SLACK_USER_IDENTIFIER


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






def handle_pronouns_update(
    profile_updates: Dict[str, Any],
    current_pronouns: Optional[str],
    current_display_name: str,
    slack_service: Any
) -> None:
    """
    Handle pronouns field update, syncing with display_name.
    
    Args:
        profile_updates: Dictionary to update with changes
        current_pronouns: Current pronouns value
        current_display_name: Current display_name value
        slack_service: SlackService instance
    """
    new_pronouns = prompt_text_input(
        "New pronouns (e.g., He/Him/His, She/Her/Hers, They/Them/Theirs)",
        default_value=current_pronouns or ""
    )
    
    if new_pronouns != current_pronouns:
        profile_updates["pronouns"] = new_pronouns if new_pronouns else ""
        
        display_name_to_update = profile_updates.get("display_name", current_display_name)
        if display_name_to_update == '(none)':
            display_name_to_update = ""
        
        updated_display_name = slack_service.append_pronouns_to_display_name(
            display_name_to_update,
            new_pronouns if new_pronouns else None
        )
        
        if updated_display_name:
            profile_updates["display_name"] = updated_display_name
            profile_updates["display_name_normalized"] = updated_display_name


def handle_display_name_update(
    profile_updates: Dict[str, Any],
    current_display_name: str,
    current_profile: SlackUserProfile,
    slack_service: Any
) -> None:
    """
    Handle display_name field update, preserving pronouns.
    
    Args:
        profile_updates: Dictionary to update with changes
        current_display_name: Current display_name value
        current_profile: Current user profile
        slack_service: SlackService instance
    """
    new_display_name = prompt_text_input(
        "New display name",
        default_value=current_display_name if current_display_name != '(none)' else ""
    )
    
    if new_display_name and new_display_name != current_display_name:
        pronouns_to_preserve = getattr(current_profile, 'pronouns', None)
        if not pronouns_to_preserve and "pronouns" in profile_updates:
            pronouns_to_preserve = profile_updates["pronouns"]
        
        updated_display_name = slack_service.append_pronouns_to_display_name(
            new_display_name,
            pronouns_to_preserve
        )
        
        profile_updates["display_name"] = updated_display_name
        profile_updates["display_name_normalized"] = updated_display_name


def collect_interactive_updates(user: SlackUser, slack_service: Any) -> Dict[str, Any]:
    """
    Collect profile updates interactively from user.
    
    Args:
        user: Current SlackUser instance
        slack_service: SlackService instance
        
    Returns:
        Dictionary of profile updates
    """
    profile_updates = {}
    if not user.profile:
        raise click.ClickException("User profile is not available")
    current_profile: SlackUserProfile = user.profile
    
    current_values = {
        'first_name': current_profile.first_name or '',
        'last_name': current_profile.last_name or '',
        'pronouns': getattr(current_profile, 'pronouns', None) or slack_service.extract_pronouns_from_display_name(current_profile.display_name or ''),
        'display_name': current_profile.display_name or '',
        'email': current_profile.email or '',
        'title': current_profile.title or '',
        'phone': current_profile.phone or '',
    }
    
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
    
    field_handlers = {
        "First Name": lambda: prompt_and_update_field("first_name", current_values['first_name'], "New first name", profile_updates),
        "Last Name": lambda: prompt_and_update_field("last_name", current_values['last_name'], "New last name", profile_updates),
        "Pronouns": lambda: handle_pronouns_update(profile_updates, current_values['pronouns'], current_values['display_name'], slack_service),
        "Display Name": lambda: handle_display_name_update(profile_updates, current_values['display_name'], current_profile, slack_service),
        "Email": lambda: prompt_and_update_field("email", current_values['email'], "New email", profile_updates),
        "Title": lambda: prompt_and_update_field("title", current_values['title'], "New title", profile_updates),
        "Phone": lambda: prompt_and_update_field("phone", current_values['phone'], "New phone", profile_updates),
        "Image": lambda: click.echo("⚠️  Image updates are not yet supported via CLI\n💡 Use Slack's UI to update profile images"),
    }
    
    while True:
        selected_field = prompt_select_from_options(
            "Select field to update",
            field_options,
            show_current="Select a field to update"
        )
        
        if selected_field is None:
            break
        
        field_name = selected_field.split(" (Current:")[0].strip()
        
        handler = field_handlers.get(field_name)
        if handler:
            handler()
        else:
            click.echo(f"⚠️  Unknown field: {field_name}")
        
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
        "Email": user.email or 'N/A'
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


def _format_profile_update_result(
    result: Dict[str, Any],
    profile_updates: Dict[str, Any],
    user: SlackUser,
    json_output: bool
) -> None:
    """Format and display profile update result."""
    if result.get("success"):
        response = result.get("response", {})
        response_data = response.data if hasattr(response, 'data') else dict(response) if hasattr(response, '__dict__') else response
        
        if json_output:
            click.echo(json.dumps(response_data, indent=2, default=str))
        else:
            click.echo("✅ Changes applied successfully")
            click.echo("\n📋 API Response:")
            click.echo(json.dumps(response_data, indent=2, default=str))
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
            click.echo("\n📋 Full Error Response:", err=True)
            click.echo(json.dumps(result.get("response", {}), indent=2, default=str), err=True)


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
    Update Slack user profile fields.
    
    Always shows a preview of changes before applying.
    
    IDENTIFIER: User's email address or Slack user ID (e.g., 'U01ABC123').
                If omitted, will prompt for input.
    
    Examples:
      bars slack user update chase@bigapplerecsports.com --title "Commissioner"
      bars slack user update U03LZKQSHEU --title "Director of Kickball"
      bars slack user update user@example.com --title "Commissioner" --phone "+1-555-123-4567"
      bars slack user update user@example.com --status-text "BARS Leadership" --status-emoji ":tada:"
    """
    from bars_cli._core.context import get_service
    
    json_output = ctx.obj.get('json_output', False) if ctx.obj else False
    should_display = ctx.obj.get('should_display', True) if ctx.obj else True
    slack_service = get_service(ctx, 'slack_service')
    
    try:
        if not identifier:
            if json_output:
                click.echo(json.dumps({"error": "Identifier required in JSON mode"}, indent=2), err=True)
                sys.exit(1)
            identifier_str = prompt_text_input("Enter user email or ID")
            identifier = {"email": identifier_str} if "@" in identifier_str else {"user_id": identifier_str}
        
        user_dict = slack_service.lookup_user(identifier, bot_name='leadership')
        if not user_dict:
            error_msg = f"User not found: {identifier.get('email') or identifier.get('user_id')}"
            if json_output:
                click.echo(json.dumps({"error": error_msg}, indent=2), err=True)
            else:
                click.echo(f"❌ {error_msg}", err=True)
            raise click.ClickException(error_msg)
        
        user = SlackUser(**user_dict)
        
        user_dict_for_service = user_dict
        
        if profile_fields:
            profile_updates = slack_service.build_profile_updates(profile_fields, user_dict_for_service)
        else:
            if json_output:
                click.echo(json.dumps({
                    "error": "No updates specified",
                    "message": "In JSON mode, interactive prompts are not available. Provide field updates via command-line flags.",
                    "example": "bars slack user update user@example.com --json --title \"New Title\" --phone \"+1-555-1234\""
                }, indent=2), err=True)
                sys.exit(1)
            
            profile_updates = collect_interactive_updates(user, slack_service)
            
            if not profile_updates:
                click.echo("\n⚠️  No updates specified")
                sys.exit(0)
        
        if not _has_actual_changes(user, profile_updates):
            _handle_no_changes(user, profile_updates, json_output)
        
        if should_display and not json_output:
            context = {
                "User": f"{user.real_name or 'Unknown'} ({user.name})",
                "Email": user.email or 'N/A'
            }
            show_profile_changes(user, profile_updates, context)
        
        result = slack_service.update_user_profile(
            user_id=user.id,
            profile_updates=profile_updates,
            bot_name='leadership'
        )
        
        _format_profile_update_result(result, profile_updates, user, json_output)
        
        if result.get("success"):
            return user
        else:
            sys.exit(1)
    
    except click.ClickException:
        raise
    except SlackApiError as e:
        error_msg = e.response.get('error', 'Unknown error') if hasattr(e, 'response') else str(e)
        if json_output:
            click.echo(json.dumps({"error": error_msg, "error_type": "slack_api_error"}, indent=2), err=True)
        else:
            click.echo(f"❌ Slack API error: {error_msg}", err=True)
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo("\n❌ Cancelled", err=True)
        sys.exit(0)
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        if json_output:
            click.echo(json.dumps({"error": error_msg, "error_type": error_type}, indent=2), err=True)
        else:
            click.echo(f"❌ Unexpected error ({error_type}): {error_msg}", err=True)
        sys.exit(1)
