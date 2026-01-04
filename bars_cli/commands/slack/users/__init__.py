"""
Slack user management commands.

Commands:
- bars slack user get <email/id>
- bars slack user list
- bars slack user update <email/id>
"""
import click

from .get import get_user_cmd
from .list import list_users_cmd
from .update import update_user_cmd


@click.group(name='user')
def slack_user():
    """User management."""
    pass


# Register commands
slack_user.add_command(get_user_cmd)
slack_user.add_command(list_users_cmd)
slack_user.add_command(update_user_cmd)


__all__ = ["slack_user"]
