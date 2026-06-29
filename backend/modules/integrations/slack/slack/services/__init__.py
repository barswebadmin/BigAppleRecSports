"""
Slack service layer.

Provides high-level Slack operations for usergroups, channels, and users.
"""

from .usergroup_service import UsergroupService
from .usergroup_provisioner import UsergroupProvisioner, normalize_handle

__all__ = [
    "UsergroupService",
    "UsergroupProvisioner",
    "normalize_handle",
]

