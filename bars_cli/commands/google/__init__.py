"""
Google management commands for bars-cli.

Command structure:
- bars google group * / bars google groups *
- bars google user * / bars google users *
- bars google sheets *
"""
import click
from click_aliases import ClickAliasedGroup


@click.group(
    cls=ClickAliasedGroup,
    context_settings={"ignore_unknown_options": True}
)
@click.pass_context
def google(ctx: click.Context):
    """Google management commands."""
    # Service is lazily initialized on first access via ctx.meta['google_api_client']
    pass


# Create subcommand groups
@click.group('groups', cls=ClickAliasedGroup)
@click.pass_context
def groups_group(ctx: click.Context):
    """Google Groups management commands."""
    pass


@click.group('users')
@click.pass_context
def users_group(ctx: click.Context):
    """Google Users management commands."""
    pass


@click.group('sheets')
@click.pass_context
def sheets_group(ctx: click.Context):
    """Google Sheets management commands."""
    pass


# Register subcommands
from .groups.get import get_group_cmd
from .groups.list import list_groups_cmd
from .groups.add_member import add_member_cmd
from .groups.remove_member import remove_member_cmd
from .users.get import get_user_cmd
from .users.list import list_users_cmd
from .users.create import create_user_cmd

groups_group.add_command(get_group_cmd)
groups_group.add_command(list_groups_cmd)
groups_group.add_command(add_member_cmd, 'add-member', aliases=['add-user', 'add_member', 'add_user'])
groups_group.add_command(remove_member_cmd, 'remove-member', aliases=['remove-user', 'remove_member', 'remove_user'])
users_group.add_command(get_user_cmd)
users_group.add_command(list_users_cmd)
users_group.add_command(create_user_cmd)

# Register groups with aliases
google.add_command(groups_group, 'groups', aliases=['group'])
google.add_command(users_group, 'users', aliases=['user'])
google.add_command(sheets_group, 'sheets', aliases=['sheet'])


__all__ = ["google"]

