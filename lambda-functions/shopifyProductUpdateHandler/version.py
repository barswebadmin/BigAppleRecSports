"""
Version information for shopifyProductUpdateHandler Lambda function
"""

__version__ = "1.0.0"
__description__ = "Shopify product image updater for sold-out sports products"
__author__ = "BARS"

def get_version():
    """Return the current version string"""
    return __version__

def get_version_info():
    """Return version information dictionary"""
    return {
        "version": __version__,
        "description": __description__,
        "author": __author__
    } 