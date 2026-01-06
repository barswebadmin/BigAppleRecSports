"""Get Slack usergroup details command."""
import json
import sys
from typing import Optional, Dict, Any

import click
from slack_sdk.errors import SlackApiError

from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.param_types import SLACK_GROUP_IDENTIFIER
from ..utils import handle_slack_api_error


def format_group(group: Dict[str, Any]) -> str:
    """Format usergroup data for display."""
    name = group.get('name', 'N/A')
    handle = group.get('handle', 'N/A')
    group_id = group.get('id', 'N/A')
    description = group.get('description', '')
    is_disabled = group.get('date_delete', 0) > 0 if group.get('date_delete') else False
    
    output = []
    output.append("\n👥 Usergroup Details:\n")
    output.append(f"  Name: {name}")
    output.append(f"  Handle: @{handle}")
    output.append(f"  Group ID: {group_id}")
    
    if description:
        output.append(f"  Description: {description}")
    
    if is_disabled:
        output.append("  ⚠️  Status: DISABLED")
    
    users = group.get('users', [])
    user_count = len(users)
    output.append(f"  Members: {user_count}")
    
    if users:
        output.append(f"\n  Member IDs:")
        for user_id in users[:20]:  # Show first 20
            output.append(f"    - {user_id}")
        if len(users) > 20:
            output.append(f"    ... and {len(users) - 20} more")
    
    return '\n'.join(output)


@click.command('get')
@handle_display_options(display=True, exit_on_error=True)
@click.argument('identifier', type=SLACK_GROUP_IDENTIFIER, required=False)
@click.pass_context
def get_group_cmd(ctx: click.Context, identifier: Optional[Dict[str, Any]]):
    """
    Get Slack usergroup details by handle or ID.
    
    IDENTIFIER: Usergroup handle (with or without @) or Slack usergroup ID (e.g., 'S03LZKQSHEU').
                If omitted, will prompt for input.
    
    Examples:
      bars slack group get leadership
      bars slack group get @leadership
      bars slack group get S03LZKQSHEU
      bars --json slack group get leadership
    """
    json_output = ctx.obj.get('json_output', False) if ctx.obj else False
    display_override = ctx.obj.get('display_override') if ctx.obj else None
    exit_override = ctx.obj.get('exit_override') if ctx.obj else None
    should_display = display_override if display_override is not None else True
    
    if not identifier:
        error_msg = "Usergroup identifier required"
        if should_display:
            if json_output:
                click.echo(json.dumps({"error": error_msg}, indent=2), err=True)
            else:
                click.echo(f"❌ {error_msg}", err=True)
        raise click.ClickException(error_msg)
    
    try:
        # Get leadership_bot from context meta (initialized at slack group level)
        bot = ctx.meta['leadership_bot']
        
        # Extract identifier value from dict
        if 'group_id' in identifier:
            identifier_value = identifier['group_id']
            if should_display and not json_output:
                click.echo(f"🔍 Looking up usergroup ID: {identifier_value}", err=True)
        elif 'handle' in identifier:
            identifier_value = identifier['handle']
            if should_display and not json_output:
                click.echo(f"🔍 Looking up usergroup handle: {identifier_value}", err=True)
        else:
            raise ValueError("Invalid identifier format")
        
        # Use leadership_bot's lookup_group method
        group_data = bot.lookup_group(identifier_value)
        
        if not group_data:
            error_msg = f"Usergroup not found: {identifier_value}"
            if should_display:
                if json_output:
                    click.echo(json.dumps({"error": error_msg}, indent=2), err=True)
                else:
                    click.echo(f"❌ {error_msg}", err=True)
                    click.echo(f"💡 Try checking the handle/ID spelling or use 'bars slack group list' to see all groups", err=True)
            raise click.ClickException(error_msg)
        
        # Display result
        if json_output:
            click.echo(json.dumps(group_data, indent=2))
        elif should_display:
            click.echo(format_group(group_data))
        
        return group_data
    
    except SlackApiError as e:
        # Get token from bot if available
        token = None
        try:
            bot = ctx.meta.get('leadership_bot')
            if bot and hasattr(bot, 'client') and hasattr(bot.client, 'token'):
                token = bot.client.token
        except Exception:
            pass
        
        handle_slack_api_error(e, json_output=json_output, token=token, api_method='usergroups.info')
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
        if exit_override is None or exit_override:
            sys.exit(1)
        raise
