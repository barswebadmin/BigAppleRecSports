"""Get Slack usergroup details command."""
from typing import Optional, Dict, Any

import click

from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.param_types import SLACK_GROUP_IDENTIFIER
from bars_cli.commands.slack._shared.command_helpers import handle_slack_get_command, extract_group_identifier
from .._shared.slack_formatters import format_group


@click.command('get')
@handle_display_options(display=True, exit_on_error=True)
@click.argument('identifier', type=SLACK_GROUP_IDENTIFIER, required=False)
@click.pass_context
def cmd_slack_groups_get(ctx: click.Context, identifier: Optional[Dict[str, Any]]):
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
    from bars_cli.commands.slack._shared.command_helpers import get_admin_bot
    
    bot = get_admin_bot(ctx)
    
    return handle_slack_get_command(
        ctx=ctx,
        identifier=identifier,
        lookup_method=bot.lookup_group,
        format_func=format_group,
        entity_name="group",
        identifier_required_msg="Usergroup identifier is required (handle or group ID)",
        extract_identifier_value=extract_group_identifier
    )
