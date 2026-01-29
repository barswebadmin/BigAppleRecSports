"""
Slack usergroup (team) management commands.

Commands:
- bars slack group list
- bars slack group get <name/id>
- bars slack group add-user <group> <user>
- bars slack group remove-user <group> <user>
- bars slack group sync <hierarchy-json>
"""
import click_extra as click

from .list import list_groups_cmd
from .get import get_group_cmd
from .add_member import add_member_cmd
from .remove_user import remove_user_from_group_cmd
from .sync import sync_groups_cmd


@click.group(
    name='groups',
    aliases=['group'],
    context_settings={"ignore_unknown_options": True}
)
def slack_groups_grp(ctx: click.Context):
    """Usergroup (team) management."""
    pass


# Register commands
slack_groups_grp.add_command(list_groups_cmd)
slack_groups_grp.add_command(get_group_cmd)
slack_groups_grp.add_command(add_member_cmd)
slack_groups_grp.add_command(remove_user_from_group_cmd)
slack_groups_grp.add_command(sync_groups_cmd)


__all__ = ["slack_groups_grp"]
