"""
Optional League Information model for product creation
"""

from typing import List, Optional
from pydantic import BaseModel, field_validator
from ..regular_season_basic_details import (
    SportSubCategory,
    SocialOrAdvanced,
    LeagueAssignmentTypes,
)


class OptionalLeagueInfo(BaseModel):
    """Optional league information

    This provides additional league configuration options that are optional.
    """

    # League configuration options
    socialOrAdvanced: Optional[SocialOrAdvanced] = None
    sportSubCategory: Optional[SportSubCategory] = None
    types: Optional[List[LeagueAssignmentTypes]] = None

    @field_validator("socialOrAdvanced", "sportSubCategory", mode="before")
    @classmethod
    def empty_string_to_none(cls, v):
        """Convert empty strings to None for optional fields"""
        if v == "":
            return None
        return v
