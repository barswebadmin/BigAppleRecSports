"""
List groups command for Google Directory API.
"""

from typing import List

import click

from bars_cli._core.decorators.handle_display_options import handle_display_options
from bars_cli._core.utils.json_output import output_json_list, output_json_error

from bars_cli.backend_services.google.directory_client import GroupResource


@click.command('list')
@handle_display_options(display=True, exit_on_error=True)
@click.pass_context
def list_groups_cmd(ctx: click.Context) -> List[GroupResource]:
    """
    List all groups in Google Workspace.
    
    Examples:
      bars google groups list
      bars --json google groups list
    """
    json_output = ctx.obj.get('json_output', False)
    should_display = ctx.obj.get('should_display', True)
    
    # Client is guaranteed to be available (enforced in google group initialization)
    client = ctx.meta['google_directory_client']
    
    try:
        # Display lookup message
        if should_display and not json_output:
            click.echo("🔍 Fetching all groups...", err=True)
        
        # List all groups using Google Directory API
        groups: List[GroupResource] = client.list_all_groups()
        
        if not groups:
            if should_display and not json_output:
                click.echo("ℹ️  No groups found.")
            return []
        
        # Display result
        if should_display:
            if json_output:
                output_json_list(groups)
            else:
                _format_groups_list(groups)
        
        return groups
        
    except click.ClickException:
        raise
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        
        if json_output:
            output_json_error(error_msg, error_type=error_type)
        else:
            click.echo(f"❌ Unexpected error ({error_type}): {error_msg}", err=True)
        
        raise click.ClickException(error_msg) from e


def _format_groups_list(groups: List[GroupResource]) -> None:
    """Format groups list for display.
    
    Args:
        groups: List of GroupResource Pydantic models from Google Directory API
    """
    output = []
    output.append(f"\n✅ Found {len(groups)} group(s)")
    output.append("=" * 80)
    
    for group in groups:
        email = group.email or 'N/A'
        name = group.name or 'N/A'
        members_count = group.direct_members_count or 'N/A'
        output.append(f"{email:<40} {name:<30} ({members_count} members)")
    
    output.append("=" * 80)
    click.echo('\n'.join(output))

