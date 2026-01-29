import click_extra as click

from .add_member import add_member_cmd
from .create import create_group_cmd
from .get import get_group_cmd
from .list import list_groups_cmd
from .remove_member import remove_member_cmd

@click.group(
    name='groups',
    aliases=['group'],
    context_settings={"ignore_unknown_options": True}
)
@click.pass_context
def google_groups_grp(ctx: click.Context):
    """Google groups management commands."""

google_groups_grp.add_command(create_group_cmd, 'create-group')
google_groups_grp.add_command(create_group_cmd, 'create')  # Add the alias
google_groups_grp.add_command(get_group_cmd, 'get')
google_groups_grp.add_command(list_groups_cmd, 'list')
google_groups_grp.add_command(remove_member_cmd, 'remove-member')
google_groups_grp.add_command(add_member_cmd, 'add-member')

__all__ = ["google_groups_grp"]