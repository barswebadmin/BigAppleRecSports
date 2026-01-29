import click_extra as click

from .get import get_sheet_cmd
from .list import list_sheets_cmd
from .create import create_sheet_cmd
from .update import update_sheet_cmd

@click.group(
    name='sheets',
    aliases=['sheet'],
    context_settings={"ignore_unknown_options": True}
)
@click.pass_context
def google_sheets_grp(ctx: click.Context):
    """Google sheets management commands."""

google_sheets_grp.add_command(get_sheet_cmd, 'get')
google_sheets_grp.add_command(list_sheets_cmd, 'list')
google_sheets_grp.add_command(create_sheet_cmd, 'create')
google_sheets_grp.add_command(update_sheet_cmd, 'update')

__all__ = ["google_sheets_grp"]