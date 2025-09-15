"""
Optional League Information model for product creation
"""

from typing import List, Optional
from .regular_season_basic_details import (
    RegularSeasonBasicDetails,
    SportSubCategory,
    SocialOrAdvanced,
    LeagueAssignmentTypes,
)


class OptionalLeagueInfo(RegularSeasonBasicDetails):
    """Optional league information that extends RegularSeasonBasicDetails

    This class inherits all fields from RegularSeasonBasicDetails but makes them optional
    to provide additional league configuration options.
    """

    # Override inherited fields to make them optional for this use case
    year: Optional[int] = None
    season: Optional[str] = None
    dayOfPlay: Optional[str] = None
    division: Optional[str] = None
    location: Optional[str] = None
    leagueStartTime: Optional[str] = None
    leagueEndTime: Optional[str] = None

    # These fields remain as they were in the original OptionalLeagueInfo
    socialOrAdvanced: Optional[SocialOrAdvanced] = None
    sportSubCategory: Optional[SportSubCategory] = None
    types: Optional[List[LeagueAssignmentTypes]] = None
