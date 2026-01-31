"""Get Slack usergroup details command."""
from typing import Optional, Dict, Any

import click_extra as click

from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.param_types import SLACK_GROUP_IDENTIFIER
from bars_cli._core.legacy_services import get_service
from bars_cli.commands.slack._shared.command_helpers import extract_group_identifier
from .._shared.slack_formatters import format_group


@click.command('get', aliases=['get-group'])
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
    slack_service = get_service(ctx, 'slack_service')
    json_output = ctx.obj.get('json_output', False) if ctx.obj else False
    should_display = ctx.obj.get('should_display', True) if ctx.obj else True
    
    if not identifier:
        error_msg = "Usergroup identifier is required (handle or group ID)"
        if json_output:
            from bars_cli._core.utils.json_output import output_json_error
            output_json_error(error_msg)
        else:
            click.echo(f"❌ {error_msg}", err=True)
        raise click.ClickException(error_msg)
    
    identifier_value = extract_group_identifier(identifier)
    
    if should_display and not json_output:
        click.echo(f"🔍 Looking up: {identifier_value}", err=True)
    
    try:
        group_data = slack_service.lookup_group(identifier_value, bot_name='leadership')
        
        if not group_data:
            error_msg = f"Usergroup not found: {identifier_value}"
            if json_output:
                from bars_cli._core.utils.json_output import output_json_error
                output_json_error(error_msg)
            else:
                click.echo(f"❌ {error_msg}", err=True)
                click.echo(f"💡 Try checking the identifier spelling or use 'bars slack group list' to see all groups", err=True)
            raise click.ClickException(error_msg)
        
        if should_display:
            if json_output:
                from bars_cli._core.utils.json_output import output_json_item
                output_json_item(group_data)
            else:
                click.echo(format_group(group_data))
        
        return group_data
    
    except click.ClickException:
        raise
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        if json_output:
            from bars_cli._core.utils.json_output import output_json_error
            output_json_error(error_msg, error_type=error_type)
        else:
            click.echo(f"❌ Unexpected error ({error_type}): {error_msg}", err=True)
        raise click.ClickException(error_msg) from e
