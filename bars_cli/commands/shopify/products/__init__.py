"""Shopify product management commands."""

import click_extra as click

from .get import get_product_cmd
from .orders import product_orders_cmd
from .update_inventory import update_inventory_cmd


@click.group(
    name='products',
    aliases=['product'],
    context_settings={"ignore_unknown_options": True}
)
@click.pass_context
def products_group(ctx: click.Context):
    """Product management commands."""
    pass


products_group.add_command(get_product_cmd)
products_group.add_command(product_orders_cmd)
products_group.add_command(update_inventory_cmd)


__all__ = ["products_group", "get_product_cmd", "product_orders_cmd", "update_inventory_cmd"]
