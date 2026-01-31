"""List sheets command - placeholder for Google Sheets API."""

import click_extra as click


@click.command('list', aliases=['list-sheets'])
@click.pass_context
def list_sheets_cmd(ctx: click.Context):
    """List all Google Sheets (not implemented - requires Drive API)."""
    click.echo("ℹ️  Listing sheets requires Google Drive API integration", err=True)
    click.echo("ℹ️  Use 'bars google sheets get <id>' to get a specific sheet", err=True)
