import click_extra as click

@click.command('get', aliases=['get-sheet'])
@click.argument('id', type=str)
@click.pass_context
def get_sheet_cmd(ctx: click.Context, id: str):
    """Get a Google Sheet by ID."""
    pass