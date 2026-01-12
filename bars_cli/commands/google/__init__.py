"""
Google management commands for bars-cli.

Command structure:
- bars google groups *
- bars google users *
- bars google sheets *
"""
import click


@click.group(
    context_settings={"ignore_unknown_options": True}
)
@click.pass_context
def google(ctx: click.Context):
    """Google management commands."""
    # Initialize Google clients once in meta (shared across all contexts)
    # Clients must be present - callbacks raise exceptions on failure (fail early)
    if 'google_directory_client' not in ctx.meta:
        create_client = ctx.meta.get('_create_google_directory_client')
        if not create_client:
            raise click.ClickException(
                "Google Directory client creation callback not found. This is a bug - callbacks should be initialized in context."
            )
        # Callback raises exception on failure - fail early
        ctx.meta['google_directory_client'] = create_client()
    
    if 'google_sheets_client' not in ctx.meta:
        create_client = ctx.meta.get('_create_google_sheets_client')
        if not create_client:
            raise click.ClickException(
                "Google Sheets client creation callback not found. This is a bug - callbacks should be initialized in context."
            )
        # Callback raises exception on failure - fail early
        ctx.meta['google_sheets_client'] = create_client()


# Create subcommand groups
@click.group('groups')
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
from .groups.add_member import add_member_cmd, add_user_cmd
from .groups.remove_member import remove_member_cmd, remove_user_cmd
from .users.get import get_user_cmd
from .users.list import list_users_cmd

groups_group.add_command(get_group_cmd, 'get')
groups_group.add_command(list_groups_cmd, 'list')
groups_group.add_command(add_member_cmd, 'add_member')
groups_group.add_command(add_user_cmd, 'add_user')
groups_group.add_command(remove_member_cmd, 'remove_member')
groups_group.add_command(remove_user_cmd, 'remove_user')
users_group.add_command(get_user_cmd, 'get')
users_group.add_command(list_users_cmd, 'list')

# Register groups
google.add_command(groups_group)
google.add_command(users_group)
google.add_command(sheets_group)


__all__ = ["google"]

