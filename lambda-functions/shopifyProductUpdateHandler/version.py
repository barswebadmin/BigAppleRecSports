"""
Version information for shopifyProductUpdateHandler Lambda function
"""

__version__ = "1.0.0"
__build__ = 1
__last_updated__ = "2025-09-08"
__description__ = "Shopify product image updater for sold-out sports products"
__author__ = "BARS"

def get_version():
    """Return the current version string"""
    return __version__

def get_version_info():
    """Return complete version information"""
    return {
        "version": __version__,
        "build": __build__,
        "full_version": f"{__version__}.{__build__}",
        "last_updated": __last_updated__,
        "description": __description__,
        "author": __author__
    } 