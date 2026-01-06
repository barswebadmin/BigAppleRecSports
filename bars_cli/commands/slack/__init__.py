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
    # Initialize leadership_bot once in meta (shared across all contexts)
    if 'leadership_bot' not in ctx.meta:
        try:
            # Import direct instance from leadership_bot module
            from bars_cli.clients.leadership_bot import leadership_bot
            ctx.meta['leadership_bot'] = leadership_bot
        except (RuntimeError, Exception) as e:
            # Store error in meta so commands can show helpful messages
            # Catch all exceptions (including BoltError for invalid tokens)
            ctx.meta['leadership_bot_error'] = str(e)
            ctx.meta['leadership_bot'] = None


# Register subcommands
slack.add_command(slack_group)
slack.add_command(slack_user)
slack.add_command(slack_channel)




__all__ = ["slack"]

