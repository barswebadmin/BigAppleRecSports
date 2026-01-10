"""
Slack management commands for bars-cli.

Command structure:
- bars slack group *
- bars slack user *
- bars slack channel *
"""
import click

from .groups import slack_group
from .users import slack_user
from .channels import slack_channel


@click.group(
    context_settings={"ignore_unknown_options": True}
)
@click.pass_context
def slack(ctx: click.Context):
    """Slack management commands."""
    # Initialize SlackService once in meta (shared across all contexts)
    if 'slack_service' not in ctx.meta:
        create_service = ctx.meta.get('_create_slack_service')
        if not create_service:
            raise click.ClickException(
                "Slack service creation callback not found. This is a bug - callbacks should be initialized in context."
            )
        # Callback raises exception on failure - fail early
        ctx.meta['slack_service'] = create_service()
    
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


# Register subcommands
slack.add_command(slack_group)
slack.add_command(slack_user)
slack.add_command(slack_channel)




__all__ = ["slack"]

