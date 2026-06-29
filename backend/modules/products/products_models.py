"""Catalog ``Product`` model for registrations (fields aligned with sport-program YAML today).

Schema names in ``shared_utilities/schemas`` may be updated later; this type is named
``Product`` for consistency with the rest of the codebase.
"""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Literal

from pydantic import EmailStr, Field

from models.api_base_model import ApiBaseModel
from models.types import DayOfWeekEnum, DivisionEnum, SeasonEnum, SportEnum, Year

DodgeballBallType = Literal["Big Ball", "Small Ball", "Foam"]
LevelOfPlay = Literal[
    "Social",
    "Advanced",
    "Mixed Social/Advanced",
    "Competitive/Advanced",
    "Intermediate/Advanced",
]
TeamAssignment = Literal[
    "draft",
    "randomized",
    "buddy",
    "buddyNewbieOnly",
    "ladder",
]
ProductStatus = Literal[
    "tentative",
    "confirmed",
    "announced",
    "published",
    "veteranRegistration",
    "earlyRegistration",
    "general",
    "waitlisted",
]


class SessionTimeWindow(ApiBaseModel):
    start: time | None = None
    end: time | None = None


class SessionsBlock(ApiBaseModel):
    session1: SessionTimeWindow | None = None
    session2: SessionTimeWindow | None = None


class AdjustedScheduleDay(ApiBaseModel):
    date: date
    start_time: time
    end_time: time


class ScheduleDetails(ApiBaseModel):
    start_time: time | None = None
    end_time: time | None = None
    sessions: SessionsBlock | None = None
    adjusted_schedules: list[AdjustedScheduleDay] | None = None
    number_of_weeks: int | None = None
    season_start_date: date | None = None
    season_end_date: date | None = None
    off_dates: list[date] | None = None
    newbie_orientation: date | None = None
    scout_night: date | None = None
    rain_date: date | None = None
    opening_party: date | None = None
    closing_party: date | None = None


class RegistrationPeriodSlot(ApiBaseModel):
    start: datetime | None = None
    shopify_variant_id: str | None = None


class RegistrationPeriods(ApiBaseModel):
    """Registration window slots; ``general`` parallels ``early`` / ``veteran`` (JSON key ``general``)."""

    veteran: RegistrationPeriodSlot | None = None
    early: RegistrationPeriodSlot | None = None
    general: RegistrationPeriodSlot | None = None
    waitlist: RegistrationPeriodSlot | None = None


class Product(ApiBaseModel):
    """League / program product row (RegularSeason + league facets shape).

    ``sport``, ``division``, ``day_of_play``, and ``season`` use :mod:`models.types` so values
    match :class:`OrderRequest` filters. Inputs may be any casing; serialized JSON uses the
    normalized lowercase forms from those types.
    """

    id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
    notes: list[str] | None = None

    shopify_product_id: int | None = None
    location: str | None = None
    year: Year
    season: SeasonEnum
    schedule_details: ScheduleDetails | None = None
    players_per_team: int | None = Field(default=None, ge=1)
    max_teams: int | None = Field(default=None, ge=1)
    minimum_total_players: int | None = None
    max_capacity: int | None = None
    registration_periods: RegistrationPeriods | None = None
    status: ProductStatus

    sport: SportEnum
    division: DivisionEnum
    day_of_play: DayOfWeekEnum
    dodgeball_ball_type: DodgeballBallType | None = None
    level_of_play: LevelOfPlay | None = None
    team_assignment: list[TeamAssignment] | None = None
    game_duration: str | None = None
    contact_email: EmailStr


__all__ = [
    "AdjustedScheduleDay",
    "DodgeballBallType",
    "Product",
    "ProductStatus",
    "LevelOfPlay",
    "RegistrationPeriods",
    "RegistrationPeriodSlot",
    "ScheduleDetails",
    "SessionTimeWindow",
    "SessionsBlock",
    "TeamAssignment",
]
