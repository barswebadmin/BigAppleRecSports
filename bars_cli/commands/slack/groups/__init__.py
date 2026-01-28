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
from .add_member import add_member_cmd
from .remove_user import remove_slack_user_from_group
from .sync import sync_groups
from click_aliases import ClickAliasedGroup


@click.group(name='groups', cls=ClickAliasedGroup)
def slack_group():
    """Usergroup (team) management."""
    pass


# Register commands
slack_group.add_command(list_slack_groups)
slack_group.add_command(cmd_slack_groups_get)
slack_group.add_command(add_member_cmd, 'add-member', aliases=['add-user', 'add_member', 'add_user'])
slack_group.add_command(remove_slack_user_from_group)
slack_group.add_command(sync_groups)


__all__ = ["slack_group"]
