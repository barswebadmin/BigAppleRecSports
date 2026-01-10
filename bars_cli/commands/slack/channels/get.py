"""Get Slack channel details command."""
from typing import Optional, Dict, Any

import click

from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.param_types import SLACK_CHANNEL_IDENTIFIER
from bars_cli.commands.slack._shared.command_helpers import handle_slack_get_command


def format_channel(channel: dict) -> str:
    """Format channel data for display."""
    name = channel.get('name', 'N/A')
    channel_id = channel.get('id', 'N/A')
    is_private = channel.get('is_private', False)
    is_archived = channel.get('is_archived', False)
    
    output = []
    output.append("\n📺 Channel Details:\n")
    output.append(f"  Name: #{name}")
    output.append(f"  Channel ID: {channel_id}")
    
    if is_private:
        output.append("  Type: Private Channel 🔒")
    else:
        output.append("  Type: Public Channel")
    
    if is_archived:
        output.append("  ⚠️  Status: ARCHIVED")
    
    topic = channel.get('topic', {}).get('value')
    if topic:
        output.append(f"  Topic: {topic}")
    
    purpose = channel.get('purpose', {}).get('value')
    if purpose:
        output.append(f"  Purpose: {purpose}")
    
    num_members = channel.get('num_members')
    if num_members is not None:
        output.append(f"  Members: {num_members}")
    
    return '\n'.join(output)


def _extract_channel_identifier(identifier: Dict[str, Any]) -> str:
    """Extract channel identifier value from dict."""
    return identifier.get("channel_id") or identifier.get("name") or identifier.get("identifier", "")


@click.command('get')
@handle_display_options(display=True, exit_on_error=True)
@click.argument('identifier', type=SLACK_CHANNEL_IDENTIFIER, required=False)
@click.pass_context
def get_channel_cmd(ctx: click.Context, identifier: Optional[Dict[str, Any]]):
    """
    Get Slack channel details by name or ID.
    
    IDENTIFIER: Channel name (with or without #) or Slack channel ID (e.g., 'C01ABC123').
                If omitted, will prompt for input.
    
    Examples:
      bars slack channel get general
      bars slack channel get kickball-leadership
      bars slack channel get C092RU7R6PL
      bars --json slack channel get general
    """
    from bars_cli.commands.slack._shared.command_helpers import get_admin_bot
    
    bot = get_admin_bot(ctx)
    
    return handle_slack_get_command(
        ctx=ctx,
        identifier=identifier,
        lookup_method=bot.lookup_channel,
        format_func=format_channel,
        entity_name="channel",
        identifier_required_msg="Channel identifier is required (name or channel ID)",
        extract_identifier_value=_extract_channel_identifier
    )

