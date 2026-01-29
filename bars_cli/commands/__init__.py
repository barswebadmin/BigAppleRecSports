"""BARS CLI Commands"""

from .slack import slack_grp
from .google import google_grp
from .shopify import shopify_grp

__all__ = ["slack_grp", "google_grp", "shopify_grp"]

