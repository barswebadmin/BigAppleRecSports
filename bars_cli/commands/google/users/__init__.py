import click_extra as click

from .get import get_user_cmd
from .list import list_users_cmd
from .create import create_user_cmd

@click.group(
    name='users',
    aliases=['user'],
    context_settings={"ignore_unknown_options": True}
)
@click.pass_context
def google_users_grp(ctx: click.Context):
    """Google users management commands."""
    pass

__all__ = ["google_users_grp"]