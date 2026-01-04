"""
Slack usergroup (team) management commands.

Commands:
- bars slack group list
- bars slack group get <name/id>
- bars slack group add-user <group> <user>
- bars slack group remove-user <group> <user>
- bars slack group sync <hierarchy-json>
"""
import click

from .list import list_groups
from .get import get_group
from .add_user import add_user_to_group
from .remove_user import remove_user_from_group
from .sync import sync_groups


@click.group(name='group')
def slack_group():
    """Usergroup (team) management."""
    pass


# Register commands
slack_group.add_command(list_groups)
slack_group.add_command(get_group)
slack_group.add_command(add_user_to_group)
slack_group.add_command(remove_user_from_group)
slack_group.add_command(sync_groups)


__all__ = ["slack_group"]
