import click_extra as click

@click.command('list', aliases=['list-sheets'])
@click.pass_context
def list_sheets_cmd(ctx: click.Context):
    """List all Google Sheets."""
    pass