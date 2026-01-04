"""
Slack management commands for bars-cli.

Command structure:
- bars slack group *
- bars slack user *
- bars slack channel *
"""
import click

from .groups import slack_group
from .users import slack_user
from .channels import slack_channel


@click.group()
def slack():
    """Slack management commands."""
    pass


# Register subcommands
slack.add_command(slack_group)
slack.add_command(slack_user)
slack.add_command(slack_channel)


__all__ = ["slack"]

