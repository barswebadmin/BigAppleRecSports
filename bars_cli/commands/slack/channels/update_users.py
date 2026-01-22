"""Update Slack channel members command."""
import json
import sys
from typing import Optional, List, Dict, Any, Tuple

import click
import questionary
from slack_sdk.errors import SlackApiError

from bars_cli._core.decorators.handle_display_options import handle_display_options
from ..utils import handle_slack_api_error


def _parse_channel_identifier(arg: str) -> Optional[str]:
    """Parse channel identifier from 'c:identifier' format."""
    if not arg:
        return None
    
    arg = arg.strip()
    if not arg.lower().startswith('c:'):
        return None
    
    identifier = arg[2:].strip()
    if not identifier:
        return None
    
    return identifier


def _parse_user_list(arg: str) -> Optional[List[str]]:
    """Parse user list from 'u:user1,user2,user3' format."""
    if not arg:
        return None
    
    arg = arg.strip()
    if not arg.lower().startswith('u:'):
        return None
    
    user_list_str = arg[2:].strip()
    if not user_list_str:
        return None
    
    # Split by comma and strip whitespace
    users = [u.strip() for u in user_list_str.split(',') if u.strip()]
    return users if users else None


def _get_channel_members(bot, channel_id: str) -> List[str]:
    """Get all member IDs for a channel."""
    members = []
    cursor = None
    
    while True:
        try:
            response = bot.conversations_members(channel=channel_id, cursor=cursor, limit=200)
            if response.get('ok'):
                response_members = response.get('members', [])
                if response_members:
                    members.extend(response_members)
                cursor = response.get('response_metadata', {}).get('next_cursor')
                if not cursor:
                    break
            else:
                break
        except Exception:
            break
    
    return members


def _lookup_users_by_identifiers(bot, identifiers: List[str]) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    """Look up users by email or user ID. Returns tuple of (users_dict, not_found_list)."""
    users = {}
    not_found = []
    
    for identifier in identifiers:
        identifier = identifier.strip()
        if not identifier:
            continue
        
        # Check if it's a user ID (starts with U, 11 chars)
        if identifier.startswith('U') and len(identifier) == 11 and identifier.isalnum():
            # Lookup by ID
            user_data = bot.lookup_user(identifier)
            if user_data:
                users[identifier] = user_data
            else:
                not_found.append(identifier)
        elif '@' in identifier:
            # Lookup by email
            user_data = bot.lookup_user(identifier)
            if user_data:
                users[identifier] = user_data
            else:
                not_found.append(identifier)
        else:
            # Invalid format
            not_found.append(identifier)
    
    return users, not_found


@click.command('update_users')
@handle_display_options(display=True, exit_on_error=True)
@click.argument('channel_arg', required=False)
@click.argument('users_arg', required=False)
@click.pass_context
def update_users_cmd(
    ctx: click.Context,
    channel_arg: Optional[str],
    users_arg: Optional[str]
) -> Optional[Dict[str, Any]]:
    """
    Update Slack channel members.
    
    CHANNEL_ARG: Channel identifier in format 'c:channel_id' or 'c:channel_name'
    USERS_ARG: User list in format 'u:user1,user2,user3' where users are emails or user IDs
    
    Examples:
      bars slack channel update_users c:general u:user1@example.com,user2@example.com
      bars slack channel update_users c:C092RU7R6PL u:U1234567890,U9876543210
      bars slack channel update_users c:kickball-leadership u:joe@example.com,kyle@example.com
    """
    json_output = ctx.obj.get('json_output', False) if ctx.obj else False
    display_override = ctx.obj.get('display_override') if ctx.obj else None
    exit_override = ctx.obj.get('exit_override') if ctx.obj else None
    should_display = display_override if display_override is not None else True
    
    # Parse arguments
    channel_identifier = _parse_channel_identifier(channel_arg) if channel_arg else None
    user_list = _parse_user_list(users_arg) if users_arg else None
    
    # Prompt for missing arguments
    if not channel_identifier:
        if json_output:
            raise click.ClickException("Channel identifier required in JSON mode")
        channel_input = questionary.text(
            "Enter channel identifier (c:channel_id or c:channel_name):",
            validate=lambda x: bool(x.strip())
        ).ask()
        if channel_input:
            channel_identifier = _parse_channel_identifier(channel_input)
    
    if not user_list:
        if json_output:
            raise click.ClickException("User list required in JSON mode")
        users_input = questionary.text(
            "Enter user list (u:user1,user2,user3):",
            validate=lambda x: bool(x.strip())
        ).ask()
        if users_input:
            user_list = _parse_user_list(users_input)
    
    if not channel_identifier:
        raise click.ClickException("Channel identifier is required")
    
    if not user_list:
        raise click.ClickException("User list is required")
    
    try:
        # Get admin_bot from context meta
        bot = ctx.meta['admin_bot']
        
        # Look up channel
        if should_display and not json_output:
            click.echo(f"🔍 Looking up channel: {channel_identifier}", err=True)
        
        channel_data = bot.lookup_channel(channel_identifier)
        if not channel_data:
            error_msg = f"Channel not found: {channel_identifier}"
            if should_display:
                if json_output:
                    click.echo(json.dumps({"error": error_msg}, indent=2), err=True)
                else:
                    click.echo(f"❌ {error_msg}", err=True)
            raise click.ClickException(error_msg)
        
        channel_id = channel_data.get('id')
        channel_name = channel_data.get('name', 'N/A')
        
        # Get current channel members
        if should_display and not json_output:
            click.echo(f"📋 Fetching current members of #{channel_name}...", err=True)
        
        current_member_ids = set(_get_channel_members(bot, channel_id))
        
        # Look up users
        if should_display and not json_output:
            click.echo(f"👥 Looking up {len(user_list)} user(s)...", err=True)
        
        users_by_identifier, not_found = _lookup_users_by_identifiers(bot, user_list)
        
        # Extract user IDs from looked up users
        target_user_ids = set()
        for user_data in users_by_identifier.values():
            user_id = user_data.get('id')
            if user_id:
                target_user_ids.add(user_id)
        
        # Calculate changes
        users_to_add = target_user_ids - current_member_ids
        users_to_remove = current_member_ids - target_user_ids
        
        # Warn about users not found
        if not_found:
            if should_display:
                if json_output:
                    click.echo(json.dumps({"warning": "Some users could not be found", "not_found": not_found}, indent=2), err=True)
                else:
                    click.echo(f"\n⚠️  Warning: Could not find {len(not_found)} user(s):", err=True)
                    for identifier in not_found:
                        click.echo(f"   • {identifier}", err=True)
                    click.echo()
        
        # Display changes summary
        if should_display and not json_output:
            click.echo(f"\n📊 Channel: #{channel_name} ({channel_id})")
            click.echo(f"   Current members: {len(current_member_ids)}")
            click.echo(f"   Target members: {len(target_user_ids)}")
            click.echo()
            
            if users_to_add:
                click.echo(f"➕ Users to add ({len(users_to_add)}):")
                for user_id in sorted(users_to_add):
                    # Find user data for display
                    user_data = None
                    for u_data in users_by_identifier.values():
                        if u_data.get('id') == user_id:
                            user_data = u_data
                            break
                    if user_data:
                        name = user_data.get('real_name') or user_data.get('name', 'N/A')
                        email = user_data.get('profile', {}).get('email', 'N/A')
                        click.echo(f"   • {name} ({email}) - {user_id}")
                    else:
                        click.echo(f"   • {user_id}")
                click.echo()
            
            if users_to_remove:
                click.echo(f"➖ Users to remove ({len(users_to_remove)}):")
                for user_id in sorted(users_to_remove):
                    click.echo(f"   • {user_id}")
                click.echo()
            
            if not users_to_add and not users_to_remove:
                click.echo("✅ No changes needed - channel members already match target list")
                return {
                    "channel_id": channel_id,
                    "channel_name": channel_name,
                    "current_members": list(current_member_ids),
                    "target_members": list(target_user_ids),
                    "added": [],
                    "removed": [],
                    "not_found": not_found
                }
        
        # Prompt for confirmation
        if should_display and not json_output:
            if users_to_add or users_to_remove:
                choice = questionary.select(
                    "Confirm changes?",
                    choices=[
                        questionary.Choice("Continue (c)", value="c"),
                        questionary.Choice("Retry (r)", value="r"),
                        questionary.Choice("Exit (e)", value="e"),
                    ],
                    default="c"
                ).ask()
                
                if choice == "e":
                    click.echo("❌ Cancelled by user")
                    sys.exit(0)
                elif choice == "r":
                    # Retry by re-running the command
                    return update_users_cmd(ctx, channel_arg, users_arg)
        
        # Apply changes
        added_results = []
        removed_results = []
        
        # Add users
        if users_to_add:
            if should_display and not json_output:
                click.echo(f"\n➕ Adding {len(users_to_add)} user(s)...", err=True)
            
            try:
                response = bot.conversations_invite(
                    channel=channel_id,
                    users=list(users_to_add)
                )
                if response.get('ok'):
                    added_results = list(users_to_add)
                    if should_display and not json_output:
                        click.echo(f"✅ Successfully added {len(users_to_add)} user(s)")
                else:
                    error = response.get('error', 'Unknown error')
                    if should_display:
                        if json_output:
                            click.echo(json.dumps({"error": f"Failed to add users: {error}"}, indent=2), err=True)
                        else:
                            click.echo(f"❌ Failed to add users: {error}", err=True)
            except SlackApiError as e:
                if should_display:
                    handle_slack_api_error(e, json_output=json_output, token=bot.client.token, api_method='conversations.invite')
                raise
        
        # Remove users
        if users_to_remove:
            if should_display and not json_output:
                click.echo(f"\n➖ Removing {len(users_to_remove)} user(s)...", err=True)
            
            for user_id in users_to_remove:
                try:
                    response = bot.conversations_kick(channel=channel_id, user=user_id)
                    if response.get('ok'):
                        removed_results.append(user_id)
                        if should_display and not json_output:
                            click.echo(f"   ✅ Removed {user_id}")
                    else:
                        error = response.get('error', 'Unknown error')
                        if should_display:
                            if json_output:
                                click.echo(json.dumps({"warning": f"Failed to remove {user_id}: {error}"}, indent=2), err=True)
                            else:
                                click.echo(f"   ⚠️  Failed to remove {user_id}: {error}", err=True)
                except SlackApiError as e:
                    if should_display:
                        if json_output:
                            click.echo(json.dumps({"warning": f"Failed to remove {user_id}: {e.response.get('error', str(e))}"}, indent=2), err=True)
                        else:
                            click.echo(f"   ⚠️  Failed to remove {user_id}: {e.response.get('error', str(e))}", err=True)
        
        # Get updated member list
        updated_member_ids = set(_get_channel_members(bot, channel_id))
        
        # Prepare result
        result = {
            "channel_id": channel_id,
            "channel_name": channel_name,
            "current_members": list(updated_member_ids),
            "target_members": list(target_user_ids),
            "added": added_results,
            "removed": removed_results,
            "not_found": not_found
        }
        
        # Display result
        if should_display:
            if json_output:
                click.echo(json.dumps(result, indent=2))
            else:
                click.echo(f"\n✅ Channel members updated successfully")
                click.echo(f"   Channel: #{channel_name} ({channel_id})")
                click.echo(f"   Total members: {len(updated_member_ids)}")
                if added_results:
                    click.echo(f"   Added: {len(added_results)} user(s)")
                if removed_results:
                    click.echo(f"   Removed: {len(removed_results)} user(s)")
        
        return result
    
    except SlackApiError as e:
        token = None
        try:
            bot = ctx.meta['admin_bot']
            if bot and hasattr(bot, 'client') and hasattr(bot.client, 'token'):
                token = bot.client.token
        except (KeyError, Exception):
            pass
        
        handle_slack_api_error(e, json_output=json_output, token=token, api_method='conversations.members')
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
                import traceback
                click.echo(traceback.format_exc(), err=True)
        if exit_override is None or exit_override:
            sys.exit(1)
        raise

