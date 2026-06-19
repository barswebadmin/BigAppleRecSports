"""
Integration bridge between hierarchy config (schema) and domain models (data).

This module connects:
- modules/leadership/domain/hierarchy_config.py (expected structure)
- modules/leadership/domain/models.py (actual people/data)
"""
from typing import Optional, List, Tuple

from modules.leadership.domain.hierarchy_config import HierarchyConfig, PositionConfig
from modules.leadership.domain.models import (
    Position,
    LeadershipMember,
    LeadershipHierarchy
)


def validate_member_role(member: LeadershipMember, hierarchy: HierarchyConfig) -> bool:
    """
    Validate that a member's role exists in the hierarchy config.
    
    Args:
        member: LeadershipMember with role like "executive_board.commissioner" or "bowling.sunday.open.director"
        hierarchy: HierarchyConfig defining expected structure
    
    Returns:
        True if role is valid, False otherwise
    
    Example:
        >>> member = LeadershipMember(name="Joe", personal_email="joe@example.com", role="executive_board.commissioner")
        >>> hierarchy = load_hierarchy_config()
        >>> validate_member_role(member, hierarchy)
        True
    """
    # Parse role format: "section.role_key" where role_key can be nested (e.g., "sunday.open.director")
    parts = member.role.split('.', 1)  # Split only on first dot
    if len(parts) < 2:
        return False
    
    section = parts[0]
    role_key = parts[1]  # Everything after section is the role_key
    
    return hierarchy.get_position(section, role_key) is not None


def get_position_config(
    member: LeadershipMember,
    hierarchy: HierarchyConfig
) -> Optional[PositionConfig]:
    """
    Get the PositionConfig for a member's role.
    
    Args:
        member: LeadershipMember with role
        hierarchy: HierarchyConfig
    
    Returns:
        PositionConfig if found, None otherwise
    """
    parts = member.role.split('.', 1)  # Split only on first dot
    if len(parts) < 2:
        return None
    
    section = parts[0]
    role_key = parts[1]
    
    return hierarchy.get_position(section, role_key)


def create_position_from_config(
    config: PositionConfig,
    section: str,
    member: LeadershipMember,
    sub_section: Optional[str] = None,
    team: Optional[str] = None
) -> Position:
    """
    Create a Position domain object from hierarchy config.
    
    Args:
        config: PositionConfig from hierarchy
        section: Section key
        member: LeadershipMember for this position
        sub_section: Optional sub-section
        team: Optional team
    
    Returns:
        Position domain object
    """
    return Position(
        section=section,
        role=config.role_key,
        person=member,
        sub_section=sub_section,
        team=team
    )


def validate_hierarchy_completeness(
    hierarchy_data: LeadershipHierarchy,
    hierarchy_config: HierarchyConfig
) -> Tuple[bool, List[str]]:
    """
    Validate that all required positions in config are filled in data.
    
    Args:
        hierarchy_data: Actual filled positions
        hierarchy_config: Expected structure with required positions
    
    Returns:
        Tuple of (is_complete, list_of_missing_positions)
    
    Example:
        >>> data = LeadershipHierarchy()
        >>> config = load_hierarchy_config()
        >>> is_complete, missing = validate_hierarchy_completeness(data, config)
        >>> if not is_complete:
        ...     print(f"Missing positions: {missing}")
    """
    missing = []
    required_positions = hierarchy_config.get_required_positions()
    
    for section_key, role_keys in required_positions.items():
        for role_key in role_keys:
            position_data = hierarchy_data.get_position(section_key, role_key)
            if not position_data:
                missing.append(f"{section_key}.{role_key}")
    
    return len(missing) == 0, missing


def get_expected_title(member: LeadershipMember, hierarchy: HierarchyConfig) -> Optional[str]:
    """
    Get the expected standardized title for a member's role.
    
    Args:
        member: LeadershipMember with role
        hierarchy: HierarchyConfig
    
    Returns:
        Standardized title from config, or None if role not found
    
    Example:
        >>> member = LeadershipMember(name="Joe", personal_email="joe@example.com", role="bowling.commissioner")
        >>> hierarchy = load_hierarchy_config()
        >>> get_expected_title(member, hierarchy)
        'Commissioner of Bowling'
    """
    position_config = get_position_config(member, hierarchy)
    if position_config:
        return position_config.title
    return None


def validate_all_members(
    members: List[LeadershipMember],
    hierarchy: HierarchyConfig
) -> Tuple[List[LeadershipMember], List[Tuple[LeadershipMember, str]]]:
    """
    Validate a list of members against hierarchy config.
    
    Args:
        members: List of LeadershipMember objects
        hierarchy: HierarchyConfig
    
    Returns:
        Tuple of (valid_members, invalid_members_with_reasons)
    
    Example:
        >>> members = [member1, member2, member3]
        >>> hierarchy = load_hierarchy_config()
        >>> valid, invalid = validate_all_members(members, hierarchy)
        >>> for member, reason in invalid:
        ...     print(f"{member.name}: {reason}")
    """
    valid = []
    invalid = []
    
    for member in members:
        if member.is_vacant():
            valid.append(member)
            continue
        
        if not validate_member_role(member, hierarchy):
            invalid.append((member, f"Invalid role: {member.role}"))
        else:
            valid.append(member)
    
    return valid, invalid

