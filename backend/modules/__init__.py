# BARS Backend Modules
# This makes all modules importable as top-level packages

# Import and re-export all major modules
from . import orders
from . import products  
from . import refunds
from . import integrations

# Make integrations submodules available at top level
from .integrations import shopify
from .integrations import slack

__all__ = [
    "orders",
    "products", 
    "refunds",
    "integrations",
    "shopify",
    "slack",
]