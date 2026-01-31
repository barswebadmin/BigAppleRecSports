"""Get sheet command for Google Sheets API."""

import json
from typing import Optional

import click_extra as click

from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.utils.json_output import output_json_item, output_json_error
from bars_cli._core.context import get_http_client


@click.command('get', aliases=['get-sheet'])
@handle_display_options(display=True, exit_on_error=True)
@click.argument('spreadsheet_id', type=str, required=False)
@click.pass_context
def get_sheet_cmd(ctx: click.Context, spreadsheet_id: Optional[str] = None) -> Optional[dict]:
    """
    Get a Google Sheet by ID.
    
    SPREADSHEET_ID: The ID of the spreadsheet
    
    Examples:
      bars google sheets get 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms
      bars --json google sheets get 1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms
    """
    json_output = ctx.obj.get('json_output', False)
    should_display = ctx.obj.get('should_display', True)
    
    if not spreadsheet_id:
        spreadsheet_id = click.prompt('Spreadsheet ID', type=str)
    
    client = get_http_client(ctx)
    endpoint = f'http://localhost:8000/admin/google/sheets/{spreadsheet_id}'
    
    try:
        if should_display and not json_output:
            click.echo(f"🔍 Looking up sheet: {spreadsheet_id}", err=True)
        
        response = client.get(endpoint)
        
        if response.status_code == 200:
            response_data = response.json()
            if should_display:
                if json_output:
                    output_json_item(response_data)
                else:
                    click.echo(f"\n✅ Sheet Found!", err=True)
                    click.echo("=" * 60, err=True)
                    data = response_data.get('data', {})
                    click.echo(f"{'Title':<15} {data.get('title')}", err=True)
                    click.echo(f"{'ID':<15} {data.get('spreadsheet_id')}", err=True)
                    click.echo(f"{'Sheets':<15} {len(data.get('sheets', []))}", err=True)
                    click.echo("=" * 60, err=True)
            return response_data
        
        error_msg = _extract_error_message(response)
        if json_output:
            output_json_error(error_msg, error_type="APIError")
        else:
            click.echo(f"❌ {error_msg}", err=True)
            click.echo(f"Status Code: {response.status_code}", err=True)
        raise click.ClickException(error_msg)
        
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        
        if json_output:
            output_json_error(error_msg, error_type=error_type)
        else:
            click.echo(f"❌ Unexpected error ({error_type}): {error_msg}", err=True)
        
        raise click.ClickException(error_msg) from e


def _extract_error_message(response) -> str:
    """Extract error message from API response."""
    error_msg = f"API request failed with status {response.status_code}"
    try:
        error_response = response.json()
        if isinstance(error_response, dict):
            if 'message' in error_response:
                error_msg = f"API Error: {error_response['message']}"
            elif 'detail' in error_response:
                detail = error_response['detail']
                if isinstance(detail, dict):
                    if 'message' in detail:
                        error_msg = f"API Error: {detail['message']}"
                    else:
                        error_msg = f"API Error: {detail}"
                elif isinstance(detail, str):
                    error_msg = f"API Error: {detail}"
    except json.JSONDecodeError:
        pass
    return error_msg
