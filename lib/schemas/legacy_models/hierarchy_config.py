"""
Leadership Hierarchy Configuration Loader.

Loads and validates the expected leadership hierarchy from YAML.
"""

import re
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any

from shared_utilities.pydantic_config import DEFAULT_CONFIG_DICT


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


class PositionConfig(BaseModel):
    model_config = DEFAULT_CONFIG_DICT
    """Configuration for a single leadership position."""
    role_key: str
    title: str
    match_patterns: Dict[str, Any]
    required: bool = False


class SectionConfig(BaseModel):
    model_config = DEFAULT_CONFIG_DICT
    """Configuration for a section of the leadership hierarchy."""
    name: str
    csv_section_headers: List[str]
    positions: List[PositionConfig]
    is_list: bool = False


class HierarchyConfig(BaseModel):
    model_config = DEFAULT_CONFIG_DICT
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
        HierarchyConfig object with validated structure
    
    Raises:
        FileNotFoundError: If config file doesn't exist
        ValidationError: If config structure is invalid (via Pydantic)
    """
    if config_path is None:
        # Config file is now in the same directory as this module
        config_path = Path(__file__).parent / "hierarchy.yaml"
    
    if not config_path.exists():
        raise FileNotFoundError(f"Hierarchy config not found: {config_path}")
    
    with open(config_path) as f:
        data = yaml.safe_load(f)
    
    # Pydantic validates the entire structure automatically
    return HierarchyConfig.model_validate(data)

