"""
Slack user management commands.

Commands:
- bars slack user get <email/id>
"""
import click

from .get import get_user


@click.group(name='user')
def slack_user():
    """User management."""
    pass


# Register commands
slack_user.add_command(get_user)


__all__ = ["slack_user"]
