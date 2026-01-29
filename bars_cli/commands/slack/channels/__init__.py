"""
Slack channel management commands.

Commands:
- bars slack channel get <name/id>
- bars slack channel list
"""
import click_extra as click

from .get import get_channel_cmd
from .list import list_channels_cmd
from .update_users import update_users_cmd


@click.group(
    name='channels',
    aliases=['channel'],
    context_settings={"ignore_unknown_options": True}
)
def slack_channels_grp(ctx: click.Context):
    """Channel management."""
    pass


# Register commands
slack_channels_grp.add_command(get_channel_cmd)
slack_channels_grp.add_command(list_channels_cmd)
slack_channels_grp.add_command(update_users_cmd)


__all__ = ["slack_channels_grp"]

