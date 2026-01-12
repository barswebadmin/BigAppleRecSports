"""Shopify page management commands."""

import click

from .get import get_page_cmd
from .update_about import update_about_cmd


@click.group('pages')
@click.pass_context
def page_group(ctx: click.Context):
    """Page management commands."""
    pass


page_group.add_command(get_page_cmd, 'get')
page_group.add_command(update_about_cmd, 'update-about')

__all__ = ["page_group", "get_page_cmd", "update_about_cmd"]
