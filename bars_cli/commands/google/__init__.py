"""
Google management commands for bars-cli.

Command structure:
- bars google group * / bars google groups *
- bars google user * / bars google users *
- bars google sheets *
"""
import click_extra as click

from .groups import google_groups_grp
from .users import google_users_grp
from .sheets import google_sheets_grp

@click.group(
    name='google',
    aliases=['g'],
    context_settings={"ignore_unknown_options": True}
)
@click.pass_context
def google_grp(ctx: click.Context):
    """Google management commands."""
    pass

google_grp.add_command(google_groups_grp)
google_grp.add_command(google_users_grp)
google_grp.add_command(google_sheets_grp)


__all__ = ["google_grp"]

