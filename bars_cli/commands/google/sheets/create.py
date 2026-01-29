import click_extra as click

@click.command('create', aliases=['create-sheet'])
@click.argument('name', type=str)
@click.argument('description', type=str)
@click.pass_context
def create_sheet_cmd(ctx: click.Context, name: str, description: str):
    """Create a new Google Sheet."""
    pass