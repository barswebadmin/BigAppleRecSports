"""
Slack channel management commands.

Commands:
- bars slack channel get <name/id>
- bars slack channel list
"""
import click

from .get import get_channel_cmd
from .list import list_channels_cmd
from .update_users import update_users_cmd


@click.group(
    name='channel',
    context_settings={"ignore_unknown_options": True}
)
@click.pass_context
def slack_channel(ctx: click.Context):
    """Channel management."""
    # leadership_bot is already set in ctx.meta by the slack group
    # Commands can access it via ctx.meta['leadership_bot']
    pass


# Register commands
slack_channel.add_command(get_channel_cmd)
slack_channel.add_command(list_channels_cmd)
slack_channel.add_command(update_users_cmd)


__all__ = ["slack_channel"]

