"""
Backend re-export of ApiModel from shared_utilities.

This file maintains backward compatibility for backend code that imports:
    from shared.model_config import ApiModel

The actual implementation is now in shared_utilities.model_config
"""

from shared_utilities.model_config import ApiModel

__all__ = ['ApiModel']
