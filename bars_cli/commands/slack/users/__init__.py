"""
Slack user management commands.

Commands:
- bars slack user get <email/id>
- bars slack user list
- bars slack user update <email/id>
"""
import click_extra as click

from .get import get_user_cmd
from .list import list_users_cmd
from .update import update_user_cmd


@click.group(
    name='users',
    aliases=['user'],
    context_settings={"ignore_unknown_options": True}
)
def slack_users_grp(ctx: click.Context):
    """User management."""
    pass


# Register commands
slack_users_grp.add_command(get_user_cmd)
slack_users_grp.add_command(list_users_cmd)
slack_users_grp.add_command(update_user_cmd)


__all__ = ["slack_users_grp"]
