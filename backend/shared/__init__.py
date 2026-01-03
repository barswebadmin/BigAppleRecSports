"""
Shared utilities used across the backend.
"""

from .dict_utils import (
    check_dict_equivalence,
    flatten_dict_data,
    flatten_dict_data_with_prefix
)

__all__ = [
    'check_dict_equivalence',
    'flatten_dict_data',
    'flatten_dict_data_with_prefix'
]

