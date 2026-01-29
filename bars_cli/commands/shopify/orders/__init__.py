"""Shopify order management commands."""

import click_extra as click

from .get import get_order_cmd
from .cancel import cancel_order_cmd
from .refund import refund_order_cmd
from .apply_discount import apply_discount_cmd
from .restock import restock_cmd


@click.group(
    name='orders',
    aliases=['order'],
    context_settings={"ignore_unknown_options": True}
)
@click.pass_context
def orders_group(ctx: click.Context):
    """Order management commands."""
    pass


orders_group.add_command(get_order_cmd)
orders_group.add_command(cancel_order_cmd)
orders_group.add_command(refund_order_cmd)
orders_group.add_command(apply_discount_cmd)
orders_group.add_command(restock_cmd)


__all__ = ["orders_group", "get_order_cmd", "cancel_order_cmd", "refund_order_cmd", "apply_discount_cmd", "restock_cmd"]

