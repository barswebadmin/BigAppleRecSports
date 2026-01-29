"""List Slack users command."""
import json
from typing import List, Optional

import click_extra as click
from slack_sdk.errors import SlackApiError

from bars_cli.backend_services.slack.models.slack_user import SlackUser
from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.context import get_service
from bars_cli._core.utils.json_output import output_json_list, output_json_error

from .._shared.slack_formatters import format_users


@click.command('list', aliases=['list-users'])
@handle_display_options(display=True, exit_on_error=True)
@click.option('--include-bots', is_flag=False, help='Include bot accounts')
@click.option('--include-deleted', is_flag=False, help='Include deleted users')
@click.pass_context
def list_users_cmd(ctx: click.Context, include_bots: bool, include_deleted: bool) -> Optional[List[SlackUser]]:
    """
    List all Slack users visible to the leadership bot.
    
    By default, only shows active human users (no bots, no deleted users).
    
    Examples:
      bars slack user list
      bars slack user list --include-bots
      bars slack user list --include-deleted
      bars --json slack user list
    """
    json_output = ctx.obj.get('json_output', False) if ctx.obj else False
    should_display = ctx.obj.get('should_display', True) if ctx.obj else True
    
    slack_service = get_service(ctx, 'slack_service')
    
    try:
        if should_display and not json_output:
            click.echo("🔍 Fetching users...", err=True)
        
        users_data = slack_service.list_users(
            bot_name='leadership',
            include_bots=include_bots,
            include_deleted=include_deleted
        )
        
        if not users_data:
            if should_display:
                if json_output:
                    output_json_list([])
                else:
                    click.echo("ℹ️  No users found")
            return []
        
        users = [SlackUser(**user_dict) for user_dict in users_data]
        
        if should_display:
            if json_output:
                output_json_list([u.model_dump(exclude_none=True) for u in users])
            else:
                click.echo(format_users(users))
        
        return users
    
    except SlackApiError as e:
        error_msg = e.response.get('error', 'Unknown error') if hasattr(e, 'response') else str(e)
        if json_output:
            output_json_error(error_msg, error_type='slack_api_error')
        else:
            click.echo(f"❌ Slack API error: {error_msg}", err=True)
        raise click.ClickException(error_msg) from e
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        if json_output:
            output_json_error(error_msg, error_type=error_type)
        else:
            click.echo(f"❌ Unexpected error ({error_type}): {error_msg}", err=True)
        raise click.ClickException(error_msg) from e

