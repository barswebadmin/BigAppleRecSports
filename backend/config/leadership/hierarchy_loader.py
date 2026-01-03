"""
Leadership Hierarchy Configuration Loader.

Loads and validates the expected leadership hierarchy from YAML.
"""

import re
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from shared.csv.clean_text import clean_unicode_control_chars


def normalize_title(title: str) -> str:
    """
    Normalize title for matching by removing invisible characters and extra whitespace.
    
    Args:
        title: The title string to normalize
        
    Returns:
        Normalized title (lowercase, single spaces, no control chars)
    """
    # First, replace all control characters and whitespace with a single space
    # This prevents words from running together after control char removal
    cleaned = re.sub(r'[\u0000-\u001f\u007f-\u009f\u200b-\u200f\u202a-\u202e\s]+', ' ', title)
    
    # Strip leading/trailing spaces
    cleaned = cleaned.strip()
    
    # Convert to lowercase for case-insensitive matching
    return cleaned.lower()


@dataclass
class PositionConfig:
    """Configuration for a single leadership position."""
    role_key: str
    title: str
    match_patterns: Dict[str, Any]
    required: bool = False


@dataclass
class SectionConfig:
    """Configuration for a section of the leadership hierarchy."""
    name: str
    csv_section_headers: List[str]
    positions: List[PositionConfig]
    is_list: bool = False  # True for committee_members (flat list, not position-based)


@dataclass
class HierarchyConfig:
    """Complete leadership hierarchy configuration."""
    version: str
    sections: Dict[str, SectionConfig]
    
    def get_section(self, section_key: str) -> Optional[SectionConfig]:
        """Get a section by its key."""
        return self.sections.get(section_key)
    
    def get_position(self, section_key: str, role_key: str) -> Optional[PositionConfig]:
        """Get a position by section and role key."""
        section = self.get_section(section_key)
        if not section:
            return None
        
        for position in section.positions:
            if position.role_key == role_key:
                return position
        return None
    
    def get_all_expected_positions(self) -> Dict[str, List[str]]:
        """Get all expected positions grouped by section."""
        result = {}
        for section_key, section in self.sections.items():
            if not section.is_list:
                result[section_key] = [pos.role_key for pos in section.positions]
        return result
    
    def get_required_positions(self) -> Dict[str, List[str]]:
        """Get all required positions grouped by section."""
        result = {}
        for section_key, section in self.sections.items():
            if not section.is_list:
                required = [pos.role_key for pos in section.positions if pos.required]
                if required:
                    result[section_key] = required
        return result


def load_hierarchy_config(config_path: Optional[Path] = None) -> HierarchyConfig:
    """
    Load leadership hierarchy configuration from YAML file.
    
    Args:
        config_path: Path to YAML file. If None, uses default location.
    
    Returns:
        HierarchyConfig object
    
    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is invalid
    """
    if config_path is None:
        config_path = Path(__file__).parent / "hierarchy.yaml"
    
    if not config_path.exists():
        raise FileNotFoundError(f"Hierarchy config not found: {config_path}")
    
    with open(config_path) as f:
        data = yaml.safe_load(f)
    
    if not data or "sections" not in data:
        raise ValueError("Invalid hierarchy config: missing 'sections'")
    
    sections = {}
    for section_key, section_data in data["sections"].items():
        positions = []
        
        # Parse positions (if not a list section like committee_members)
        if "positions" in section_data:
            for pos_data in section_data["positions"]:
                positions.append(PositionConfig(
                    role_key=pos_data["role_key"],
                    title=pos_data["title"],
                    match_patterns=pos_data["match_patterns"],
                    required=pos_data.get("required", False)
                ))
        
        sections[section_key] = SectionConfig(
            name=section_data["name"],
            csv_section_headers=section_data["csv_section_headers"],
            positions=positions,
            is_list=section_data.get("is_list", False)
        )
    
    return HierarchyConfig(
        version=data.get("version", "unknown"),
        sections=sections
    )

