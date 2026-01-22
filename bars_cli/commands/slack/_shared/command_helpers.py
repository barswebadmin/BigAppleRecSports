"""
Shared helpers for Slack CLI commands.

Provides generic command handlers to reduce duplication across user, group, and channel commands.
"""

import json
import traceback
from typing import Dict, Any, Optional, List, Callable

import click
from slack_sdk.errors import SlackApiError

from bars_cli._core.utils.json_output import output_json_item
from ..utils import handle_slack_api_error
from .slack_formatters import format_error


def get_admin_bot(ctx: click.Context) -> Any:
    """Get admin bot from context or raise error.
    
    Args:
        ctx: Click context object
        
    Returns:
        Admin bot instance
        
    Raises:
        click.ClickException: If bot is not available
    """
    try:
        bot = ctx.meta['admin_bot']
        if not bot:
            error_msg = ctx.meta.get('admin_bot_error', 'Admin bot not available')
            raise click.ClickException(error_msg)
        return bot
    except KeyError:
        error_msg = ctx.meta.get('admin_bot_error', 'Admin bot not available')
        raise click.ClickException(error_msg)


def extract_group_identifier(identifier: Dict[str, Any]) -> str:
    """Extract group identifier value from dict.
    
    Args:
        identifier: Dict with keys: "group_id", "name", "handle", or "identifier"
        
    Returns:
        String value of the identifier (group_id, name, handle, or empty string)
    """
    return identifier.get("group_id") or identifier.get("name") or identifier.get("handle") or identifier.get("identifier", "")


def handle_slack_get_command(
    ctx: click.Context,
    identifier: Optional[Dict[str, Any]],
    lookup_method: Callable[[str], Optional[Dict[str, Any]]],
    format_func: Callable[[Any], str],
    entity_name: str,
    identifier_required_msg: Optional[str] = None,
    extract_identifier_value: Optional[Callable[[Dict[str, Any]], str]] = None
) -> Optional[Any]:
    """Generic handler for Slack GET commands (user, group, channel).
    
    Handles the complete flow:
    1. Extract display context
    2. Validate identifier
    3. Get leadership bot
    4. Call lookup method
    5. Handle errors
    6. Output JSON or formatted display
    
    Args:
        ctx: Click context object
        identifier: Identifier dict from parameter type converter
        lookup_method: Bot method to call (e.g., bot.lookup_user, bot.lookup_group)
        format_func: Function to format entity for display (e.g., format_user)
        entity_name: Entity name for messages (e.g., "user", "group", "channel")
        identifier_required_msg: Custom message when identifier is missing
        extract_identifier_value: Optional function to extract identifier value from dict.
            If None, tries common keys: email, user_id, group_id, handle, channel_id, name
    
    Returns:
        Entity object/dict, or None if error
    
    Raises:
        click.ClickException: For all errors (decorator handles exit)
    """
    ctx.ensure_object(dict)
    json_output = ctx.obj.get('json_output', False)
    should_display = ctx.obj.get('should_display', True)
    
    # Validate identifier
    if not identifier:
        error_msg = identifier_required_msg or f"{entity_name.capitalize()} identifier is required"
        format_error(error_msg, json_output=json_output, should_display=should_display)
        raise click.ClickException(error_msg)
    
    try:
        # Extract identifier value
        if extract_identifier_value:
            identifier_value = extract_identifier_value(identifier)
        else:
            # Try common identifier keys
            identifier_value = (
                identifier.get("email") or
                identifier.get("user_id") or
                identifier.get("group_id") or
                identifier.get("handle") or
                identifier.get("channel_id") or
                identifier.get("name") or
                identifier.get("identifier")
            )
        
        if not identifier_value:
            error_msg = f"Invalid identifier format for {entity_name}"
            format_error(error_msg, json_output=json_output, should_display=should_display)
            raise click.ClickException(error_msg)
        
        # Display lookup message
        if should_display and not json_output:
            click.echo(f"🔍 Looking up: {identifier_value}", err=True)
        
        # Get admin bot
        bot = get_admin_bot(ctx)
        
        # Call lookup method
        try:
            entity_data = lookup_method(identifier_value)
        except Exception as e:
            error_msg = f"Failed to lookup {entity_name} '{identifier_value}': {type(e).__name__}: {e}"
            format_error(error_msg, json_output=json_output, should_display=should_display)
            if should_display and not json_output:
                click.echo(traceback.format_exc(), err=True)
            raise click.ClickException(error_msg) from e
        
        # Check for empty results
        if not entity_data:
            error_msg = f"{entity_name.capitalize()} not found: {identifier_value}"
            format_error(error_msg, json_output=json_output, should_display=should_display)
            if should_display and not json_output:
                click.echo(f"💡 Try checking the identifier spelling or use 'bars slack {entity_name} list' to see all {entity_name}s", err=True)
            raise click.ClickException(error_msg)
        
        # Display result
        if should_display:
            if json_output:
                # Handle both dict and model objects
                if hasattr(entity_data, 'model_dump'):
                    output_json_item(entity_data.model_dump(exclude_none=True))
                elif hasattr(entity_data, 'dict'):
                    output_json_item(entity_data.dict(exclude_none=True))
                else:
                    output_json_item(entity_data)
            else:
                click.echo(format_func(entity_data))
        
        return entity_data
        
    except SlackApiError as e:
        # Get token from bot if available
        token = None
        try:
            bot = ctx.meta['admin_bot']
            if bot and hasattr(bot, 'client') and hasattr(bot.client, 'token'):
                token = bot.client.token
        except (KeyError, Exception):
            pass
        
        # Determine API method from entity_name
        api_method_map = {
            'user': 'users.info',
            'group': 'usergroups.info',
            'channel': 'conversations.info',
        }
        api_method = api_method_map.get(entity_name, None)
        
        handle_slack_api_error(e, json_output=json_output, token=token, api_method=api_method)
        raise click.ClickException(f"Slack API error: {e.response.get('error', 'Unknown error')}") from e
    except click.ClickException:
        # Re-raise Click exceptions - decorator will handle exit
        raise
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        format_error(error_msg, error_type=error_type, json_output=json_output, should_display=should_display)
        if should_display and not json_output:
            click.echo(traceback.format_exc(), err=True)
        raise click.ClickException(error_msg) from e

