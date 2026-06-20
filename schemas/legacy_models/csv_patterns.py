from pydantic import BaseModel, Field, field_validator
from typing import List, Union, Dict, Literal


class ExactMatchPattern(BaseModel):
    """Pattern for exact position title match (case-insensitive)."""
    match_type: Literal["exact"] = "exact"
    value: str = Field(..., min_length=1, description="Exact string to match (case-insensitive)")


class KeywordMatchPattern(BaseModel):
    """Pattern for keyword-based matching (all keywords must be present)."""
    match_type: Literal["keywords"] = "keywords"
    required: List[str] = Field(..., min_length=1, description="All keywords must be present")
    alternatives: List[List[str]] = Field(
        default_factory=list,
        description="Alternative keyword combinations (any can match)"
    )
    
    @field_validator("required")
    @classmethod
    def validate_required_not_empty(cls, v: List[str]) -> List[str]:
        if not v or all(not k.strip() for k in v):
            raise ValueError("required must contain at least one non-empty keyword")
        return [k.strip().lower() for k in v]
    
    @field_validator("alternatives")
    @classmethod
    def validate_alternatives(cls, v: List[List[str]]) -> List[List[str]]:
        cleaned = []
        for alt_group in v:
            if not alt_group:
                continue
            cleaned_group = [k.strip().lower() for k in alt_group if k.strip()]
            if cleaned_group:
                cleaned.append(cleaned_group)
        return cleaned


class PositionPattern(BaseModel):
    """Defines how to match a CSV position title to a role identifier."""
    role_key: str = Field(
        ...,
        min_length=1,
        description="Role identifier (e.g., 'bowling.sunday.director')"
    )
    pattern: Union[ExactMatchPattern, KeywordMatchPattern] = Field(
        ...,
        discriminator="match_type",
        description="Pattern to match against CSV position titles"
    )
    
    def matches(self, position_text: str) -> bool:
        """Check if this pattern matches the given position text."""
        if not position_text:
            return False
        
        normalized = position_text.strip().lower()
        
        if isinstance(self.pattern, ExactMatchPattern):
            return normalized == self.pattern.value.lower()
        
        if isinstance(self.pattern, KeywordMatchPattern):
            if all(kw in normalized for kw in self.pattern.required):
                return True
            
            for alt_group in self.pattern.alternatives:
                if all(kw in normalized for kw in alt_group):
                    return True
        
        return False


class SectionPatterns(BaseModel):
    """Collection of patterns for a section (e.g., bowling, executive_board)."""
    section_name: str = Field(..., min_length=1, description="Section identifier")
    patterns: List[PositionPattern] = Field(
        default_factory=list,
        description="Position patterns for this section"
    )
    
    def find_matching_role(self, position_text: str) -> str | None:
        """Find the first role_key that matches the position text."""
        for pattern in self.patterns:
            if pattern.matches(position_text):
                return pattern.role_key
        return None


class CSVPatternRegistry(BaseModel):
    """Registry of all CSV parsing patterns for leadership hierarchy."""
    sections: Dict[str, SectionPatterns] = Field(
        default_factory=dict,
        description="section_name → SectionPatterns"
    )
    
    def get_section(self, section_name: str) -> SectionPatterns | None:
        """Get patterns for a specific section."""
        return self.sections.get(section_name)
    
    def find_role_in_section(self, section_name: str, position_text: str) -> str | None:
        """Find matching role in a specific section."""
        section = self.get_section(section_name)
        if not section:
            return None
        return section.find_matching_role(position_text)
    
    @classmethod
    def create_default(cls) -> "CSVPatternRegistry":
        """Create the default BARS leadership pattern registry."""
        return cls(sections={
            "executive_board": SectionPatterns(
                section_name="executive_board",
                patterns=[
                    PositionPattern(
                        role_key="commissioner",
                        pattern=ExactMatchPattern(value="commissioner")
                    ),
                    PositionPattern(
                        role_key="vice_commissioner",
                        pattern=KeywordMatchPattern(required=["vice", "commissioner"])
                    ),
                    PositionPattern(
                        role_key="wtnb_commissioner",
                        pattern=KeywordMatchPattern(required=["wtnb", "commissioner"])
                    ),
                    PositionPattern(
                        role_key="secretary",
                        pattern=KeywordMatchPattern(required=["secretary"])
                    ),
                    PositionPattern(
                        role_key="treasurer",
                        pattern=KeywordMatchPattern(required=["treasurer"])
                    ),
                    PositionPattern(
                        role_key="operations_commissioner",
                        pattern=KeywordMatchPattern(required=["operations", "commissioner"])
                    ),
                    PositionPattern(
                        role_key="bowling_commissioner",
                        pattern=KeywordMatchPattern(required=["bowling", "commissioner"])
                    ),
                    PositionPattern(
                        role_key="dei_commissioner",
                        pattern=KeywordMatchPattern(
                            required=["diversity", "commissioner"],
                            alternatives=[
                                ["dei", "commissioner"]
                            ]
                        )
                    ),
                    PositionPattern(
                        role_key="dodgeball_commissioner",
                        pattern=KeywordMatchPattern(required=["dodgeball", "commissioner"])
                    ),
                    PositionPattern(
                        role_key="kickball_commissioner",
                        pattern=KeywordMatchPattern(required=["kickball", "commissioner"])
                    ),
                    PositionPattern(
                        role_key="pickleball_commissioner",
                        pattern=KeywordMatchPattern(required=["pickleball", "commissioner"])
                    ),
                ]
            ),
            "cross_sport": SectionPatterns(
                section_name="cross_sport",
                patterns=[
                    PositionPattern(
                        role_key="communications",
                        pattern=KeywordMatchPattern(required=["communications"])
                    ),
                    PositionPattern(
                        role_key="events.open",
                        pattern=KeywordMatchPattern(required=["events", "open"])
                    ),
                    PositionPattern(
                        role_key="events.wtnb",
                        pattern=KeywordMatchPattern(required=["events", "wtnb"])
                    ),
                    PositionPattern(
                        role_key="dei.open",
                        pattern=KeywordMatchPattern(
                            required=["diversity", "open"],
                            alternatives=[
                                ["dei", "open"]
                            ]
                        )
                    ),
                    PositionPattern(
                        role_key="dei.wtnb",
                        pattern=KeywordMatchPattern(
                            required=["diversity", "wtnb"],
                            alternatives=[
                                ["dei", "wtnb"]
                            ]
                        )
                    ),
                    PositionPattern(
                        role_key="marketing",
                        pattern=KeywordMatchPattern(required=["marketing"])
                    ),
                    PositionPattern(
                        role_key="philanthropy",
                        pattern=KeywordMatchPattern(required=["philanthropy"])
                    ),
                    PositionPattern(
                        role_key="social_media.open",
                        pattern=KeywordMatchPattern(required=["social media", "open"])
                    ),
                    PositionPattern(
                        role_key="social_media.wtnb",
                        pattern=KeywordMatchPattern(required=["social media", "wtnb"])
                    ),
                    PositionPattern(
                        role_key="technology",
                        pattern=KeywordMatchPattern(required=["technology"])
                    ),
                    PositionPattern(
                        role_key="permits_equipment",
                        pattern=KeywordMatchPattern(required=["permits", "equipment"])
                    ),
                ]
            ),
            "bowling": SectionPatterns(
                section_name="bowling",
                patterns=[
                    PositionPattern(
                        role_key="sunday.director",
                        pattern=KeywordMatchPattern(required=["sunday", "director"])
                    ),
                    PositionPattern(
                        role_key="sunday.ops_manager",
                        pattern=KeywordMatchPattern(required=["sunday", "operations manager"])
                    ),
                    PositionPattern(
                        role_key="monday_open.director",
                        pattern=KeywordMatchPattern(required=["monday", "open", "director"])
                    ),
                    PositionPattern(
                        role_key="monday_open.ops_manager",
                        pattern=KeywordMatchPattern(required=["monday", "open", "operations manager"])
                    ),
                    PositionPattern(
                        role_key="monday_wtnb.director",
                        pattern=KeywordMatchPattern(required=["monday", "wtnb", "director"])
                    ),
                    PositionPattern(
                        role_key="monday_wtnb.ops_manager",
                        pattern=KeywordMatchPattern(required=["monday", "wtnb", "operations manager"])
                    ),
                    PositionPattern(
                        role_key="player_experience.open",
                        pattern=KeywordMatchPattern(required=["player experience", "open"])
                    ),
                    PositionPattern(
                        role_key="player_experience.wtnb",
                        pattern=KeywordMatchPattern(required=["player experience", "wtnb"])
                    ),
                ]
            ),
            "dodgeball": SectionPatterns(
                section_name="dodgeball",
                patterns=[
                    PositionPattern(
                        role_key="monday.director",
                        pattern=KeywordMatchPattern(required=["monday", "director"])
                    ),
                    PositionPattern(
                        role_key="monday.ops_manager",
                        pattern=KeywordMatchPattern(required=["monday", "operations manager"])
                    ),
                    PositionPattern(
                        role_key="tuesday_open.director",
                        pattern=KeywordMatchPattern(required=["tuesday", "open", "director"])
                    ),
                    PositionPattern(
                        role_key="tuesday_open.ops_manager",
                        pattern=KeywordMatchPattern(required=["tuesday", "open", "operations manager"])
                    ),
                    PositionPattern(
                        role_key="tuesday_wtnb.director",
                        pattern=KeywordMatchPattern(required=["tuesday", "wtnb", "director"])
                    ),
                    PositionPattern(
                        role_key="tuesday_wtnb.ops_manager",
                        pattern=KeywordMatchPattern(required=["tuesday", "wtnb", "operations manager"])
                    ),
                    PositionPattern(
                        role_key="thursday.director",
                        pattern=KeywordMatchPattern(required=["thursday", "director"])
                    ),
                    PositionPattern(
                        role_key="thursday.ops_manager",
                        pattern=KeywordMatchPattern(required=["thursday", "operations manager"])
                    ),
                    PositionPattern(
                        role_key="player_experience.open",
                        pattern=KeywordMatchPattern(required=["player experience", "open"])
                    ),
                    PositionPattern(
                        role_key="player_experience.wtnb",
                        pattern=KeywordMatchPattern(required=["player experience", "wtnb"])
                    ),
                ]
            ),
            "kickball": SectionPatterns(
                section_name="kickball",
                patterns=[
                    PositionPattern(
                        role_key="sunday_open.director",
                        pattern=KeywordMatchPattern(required=["sunday", "open", "director"])
                    ),
                    PositionPattern(
                        role_key="sunday_open.ops_manager",
                        pattern=KeywordMatchPattern(required=["sunday", "open", "operations manager"])
                    ),
                    PositionPattern(
                        role_key="sunday_wtnb.director",
                        pattern=KeywordMatchPattern(required=["sunday", "wtnb", "director"])
                    ),
                    PositionPattern(
                        role_key="sunday_wtnb.ops_manager",
                        pattern=KeywordMatchPattern(required=["sunday", "wtnb", "operations manager"])
                    ),
                    PositionPattern(
                        role_key="saturday_open.director",
                        pattern=KeywordMatchPattern(required=["saturday", "open", "director"])
                    ),
                    PositionPattern(
                        role_key="saturday_open.ops_manager",
                        pattern=KeywordMatchPattern(required=["saturday", "open", "operations manager"])
                    ),
                    PositionPattern(
                        role_key="saturday_wtnb.director",
                        pattern=KeywordMatchPattern(required=["saturday", "wtnb", "director"])
                    ),
                    PositionPattern(
                        role_key="saturday_wtnb.ops_manager",
                        pattern=KeywordMatchPattern(required=["saturday", "wtnb", "operations manager"])
                    ),
                    PositionPattern(
                        role_key="player_experience.open",
                        pattern=KeywordMatchPattern(required=["player experience", "open"])
                    ),
                    PositionPattern(
                        role_key="player_experience.wtnb",
                        pattern=KeywordMatchPattern(required=["player experience", "wtnb"])
                    ),
                ]
            ),
            "pickleball": SectionPatterns(
                section_name="pickleball",
                patterns=[
                    PositionPattern(
                        role_key="monday.director",
                        pattern=KeywordMatchPattern(required=["monday", "director"])
                    ),
                    PositionPattern(
                        role_key="monday.ops_manager",
                        pattern=KeywordMatchPattern(required=["monday", "operations manager"])
                    ),
                    PositionPattern(
                        role_key="tuesday_open.director",
                        pattern=KeywordMatchPattern(required=["tuesday", "open", "director"])
                    ),
                    PositionPattern(
                        role_key="tuesday_open.ops_manager",
                        pattern=KeywordMatchPattern(required=["tuesday", "open", "operations manager"])
                    ),
                    PositionPattern(
                        role_key="tuesday_wtnb.director",
                        pattern=KeywordMatchPattern(required=["tuesday", "wtnb", "director"])
                    ),
                    PositionPattern(
                        role_key="tuesday_wtnb.ops_manager",
                        pattern=KeywordMatchPattern(required=["tuesday", "wtnb", "operations manager"])
                    ),
                    PositionPattern(
                        role_key="wednesday.director",
                        pattern=KeywordMatchPattern(required=["wednesday", "director"])
                    ),
                    PositionPattern(
                        role_key="wednesday.ops_manager",
                        pattern=KeywordMatchPattern(required=["wednesday", "operations manager"])
                    ),
                    PositionPattern(
                        role_key="player_experience.open",
                        pattern=KeywordMatchPattern(required=["player experience", "open"])
                    ),
                    PositionPattern(
                        role_key="player_experience.wtnb",
                        pattern=KeywordMatchPattern(required=["player experience", "wtnb"])
                    ),
                ]
            ),
        })

