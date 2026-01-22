"""
Slack management commands for bars-cli.

Command structure:
- bars slack group * / bars slack groups *
- bars slack user * / bars slack users *
- bars slack channel * / bars slack channels *
"""
import click
from click_aliases import ClickAliasedGroup

from .groups import slack_group
from .users import slack_user
from .channels import slack_channel


@click.group(
    cls=ClickAliasedGroup,
    context_settings={"ignore_unknown_options": True}
)
@click.pass_context
def slack(ctx: click.Context):
    """Slack management commands."""
    # Service is lazily initialized on first access via ctx.meta['slack_service']
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
slack.add_command(slack_group, 'groups', aliases=['group'])
slack.add_command(slack_user, 'users', aliases=['user'])
slack.add_command(slack_channel, 'channels', aliases=['channel'])




__all__ = ["slack"]

