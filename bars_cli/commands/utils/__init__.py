"""Utility commands (not Shopify-specific)."""

from .compare_csv import compare_csv_cmd

import click


@click.group('utils')
@click.pass_context
def utils_group(ctx: click.Context):
    """Utility commands."""
    pass


utils_group.add_command(compare_csv_cmd, 'compare-csv')

__all__ = ["utils_group", "compare_csv_cmd"]
