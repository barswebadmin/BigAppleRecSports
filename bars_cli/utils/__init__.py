"""Utility commands and utilities (not Shopify-specific)."""

import click

from .compare_csv import compare_csv_cmd

# Export utility modules
from . import csv_utils, data_parsing, order_analysis

__all__ = [
    "utils_group",
    "compare_csv_cmd",
    "csv_utils",
    "data_parsing",
    "order_analysis",
]


@click.group('utils')
@click.pass_context
def utils_group(ctx: click.Context):
    """Utility commands."""
    pass


utils_group.add_command(compare_csv_cmd, 'compare-csv')
