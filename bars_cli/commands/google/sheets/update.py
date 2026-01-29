import click_extra as click

@click.command('update', aliases=['update-sheet'])
@click.argument('id', type=str)
@click.argument('name', type=str)
@click.argument('description', type=str)
@click.pass_context
def update_sheet_cmd(ctx: click.Context, id: str, name: str, description: str):
    """Update a Google Sheet by ID."""
    pass