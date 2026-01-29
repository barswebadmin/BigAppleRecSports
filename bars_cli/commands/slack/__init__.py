"""
Slack management commands for bars-cli.

Command structure:
- bars slack group * / bars slack groups *
- bars slack user * / bars slack users *
- bars slack channel * / bars slack channels *
"""
import click_extra as click

from .groups import slack_groups_grp
from .users import slack_users_grp
from .channels import slack_channels_grp


@click.group(
    name='slack',
    context_settings={"ignore_unknown_options": True}
)
@click.pass_context
def slack_grp(ctx: click.Context):
    """Slack management commands."""
    # Initialize slack_service once in meta (shared across all contexts)
    # Override LazyServiceProxy from main.py with actual service instance
    from bars_cli._core.context import LazyServiceProxy
    if 'slack_service' not in ctx.meta or isinstance(ctx.meta.get('slack_service'), LazyServiceProxy):
        try:
            from bars_cli.backend_services.slack.slack_service import SlackService
            ctx.meta['slack_service'] = SlackService()
        except (RuntimeError, Exception) as e:
            # Store error in meta so commands can show helpful messages
            ctx.meta['slack_service_error'] = str(e)
            ctx.meta['slack_service'] = None
    
    # Initialize admin_bot once in meta (shared across all contexts)
    if 'admin_bot' not in ctx.meta:
        try:
            # Import direct instance from bot_apps module via symlink
            from bars_cli.backend_services.slack.bot_apps.bot_apps import admin_bot
            ctx.meta['admin_bot'] = admin_bot
        except (RuntimeError, Exception) as e:
            # Store error in meta so commands can show helpful messages
            # Catch all exceptions (including BoltError for invalid tokens)
            ctx.meta['admin_bot_error'] = str(e)
            ctx.meta['admin_bot'] = None


# Register subcommands with aliases
slack_grp.add_command(slack_groups_grp)
slack_grp.add_command(slack_users_grp)
slack_grp.add_command(slack_channels_grp)




__all__ = ["slack_grp"]

