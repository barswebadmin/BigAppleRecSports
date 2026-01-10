"""Backward compatibility imports for leadership config.

This module redirects imports to the new location in modules/leadership/domain/.
"""

# Import from new location
from modules.leadership.domain.hierarchy_config import (
    load_hierarchy_config,
    HierarchyConfig,
    PositionConfig,
    SectionConfig,
    normalize_title
)

__all__ = [
    "load_hierarchy_config",
    "HierarchyConfig",
    "PositionConfig",
    "SectionConfig",
    "normalize_title"
]
