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

from .list import list_slack_groups
from .get import cmd_slack_groups_get
from .add_user import cmd_slack_groups_add_user
from .remove_user import remove_slack_user_from_group
from .sync import sync_groups


@click.group(name='groups')
def slack_group():
    """Usergroup (team) management."""
    pass


# Register commands
slack_group.add_command(list_slack_groups)
slack_group.add_command(cmd_slack_groups_get)
slack_group.add_command(cmd_slack_groups_add_user)
slack_group.add_command(remove_slack_user_from_group)
slack_group.add_command(sync_groups)


__all__ = ["slack_group"]
