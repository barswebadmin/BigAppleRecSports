"""List all Slack usergroups command."""
import sys
import json

import click
from slack_sdk.errors import SlackApiError


@click.command('list')
@click.option('--bot', default='leadership', help='Which bot to use')
@click.option('--include-disabled', is_flag=False, help='Include disabled groups')
@click.pass_context
def list_slack_groups(ctx: click.Context, bot: str, include_disabled: bool):
    """List all usergroups."""
    json_output = ctx.obj.get('json_output', False) if ctx.obj else False
    
    # Service is guaranteed to be available (initialized in slack group)
    from bars_cli._core.context import get_service
    slack_service = get_service(ctx, 'slack_service')
    
    try:
        service = slack_service.get_usergroup_service(bot)
        
        groups = service.list_groups(include_disabled=include_disabled)
        
        if json_output:
            click.echo(json.dumps(groups, indent=2))
        else:
            if not groups:
                click.echo("No usergroups found.")
                return
            
            click.echo(f"\nFound {len(groups)} usergroup(s):\n")
            for g in groups:
                user_count = g.get('user_count', len(g.get('users', [])))
                disabled = " (disabled)" if not g.get('date_delete') == 0 else ""
                click.echo(
                    f"  • {g['name']} (@{g['handle']}) - "
                    f"{user_count} member(s) - ID: {g['id']}{disabled}"
                )
    
    except SlackApiError as e:
        click.echo(f"❌ Slack API error: {e.response['error']}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)

