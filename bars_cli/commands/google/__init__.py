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
    # Initialize google_api_client once in meta (shared across all contexts)
    # Override LazyServiceProxy from main.py with actual service instance
    from bars_cli._core.context import LazyServiceProxy
    if 'google_api_client' not in ctx.meta or isinstance(ctx.meta.get('google_api_client'), LazyServiceProxy):
        try:
            from bars_cli.backend_services.google.google_api_client import GoogleApiClient
            ctx.meta['google_api_client'] = GoogleApiClient()
        except (RuntimeError, Exception) as e:
            # Store error in meta so commands can show helpful messages
            ctx.meta['google_api_client_error'] = str(e)
            ctx.meta['google_api_client'] = None

google_grp.add_command(google_groups_grp)
google_grp.add_command(google_users_grp)
google_grp.add_command(google_sheets_grp)


__all__ = ["google_grp"]

