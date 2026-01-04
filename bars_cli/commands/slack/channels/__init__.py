"""
Slack channel management commands.

Commands:
- bars slack channel get <name/id>
- bars slack channel list
"""
import click

from .get import get_channel_cmd
from .list import list_channels_cmd


@click.group(name='channel')
def slack_channel():
    """Channel management."""
    pass


# Register commands
slack_channel.add_command(get_channel_cmd)
slack_channel.add_command(list_channels_cmd)


__all__ = ["slack_channel"]

