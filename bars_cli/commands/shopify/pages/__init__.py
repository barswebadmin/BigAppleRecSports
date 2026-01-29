"""Shopify page management commands."""

import click_extra as click

from .get import get_page_cmd
from .update_about import update_about_cmd


@click.group(name='pages', aliases=['page'])
@click.pass_context
def pages_group(ctx: click.Context):
    """Page management commands."""
    pass


pages_group.add_command(get_page_cmd)
pages_group.add_command(update_about_cmd)

__all__ = ["pages_group", "get_page_cmd", "update_about_cmd"]
