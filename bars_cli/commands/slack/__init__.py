"""
Slack management commands for bars-cli.

Command structure:
- bars slack group *
- bars slack user *
"""
import click

from .groups import slack_group
from .users import slack_user


@click.group()
def slack():
    """Slack management commands."""
    pass


# Register subcommands
slack.add_command(slack_group)
slack.add_command(slack_user)


__all__ = ["slack"]

