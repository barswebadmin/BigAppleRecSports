"""Shopify customer management commands."""

import click_extra as click

from .get import get_customer_cmd
from .update import update_customer_cmd


@click.group(
    name='customers',
    aliases=['customer'],
    context_settings={"ignore_unknown_options": True}
)
@click.pass_context
def customers_group(ctx: click.Context):
    """Customer management commands."""
    pass


customers_group.add_command(get_customer_cmd)
customers_group.add_command(update_customer_cmd)


__all__ = ["customers_group", "get_customer_cmd", "update_customer_cmd"]
