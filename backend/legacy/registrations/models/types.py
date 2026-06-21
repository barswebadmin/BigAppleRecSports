from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Annotated

from pydantic import BeforeValidator, Field


def last_url_path_element(v: str) -> str:
    return v.split("/")[-1]


def remove_special_chars(v: str) -> str:
    return v.strip("#+")


def shopify_id_digits_only(v: int | str) -> str:
    return remove_special_chars(last_url_path_element(str(v).strip()))


NormalizedInt = Annotated[int, BeforeValidator(shopify_id_digits_only)]

ProductHandle = str


class SeasonEnum(StrEnum):
    spring = "spring"
    summer = "summer"
    fall = "fall"
    winter = "winter"

    @classmethod
    def _missing_(cls, value: object) -> SeasonEnum | None:
        if isinstance(value, str):
            return cls(value.strip().lower().strip("#+"))
        return None


class SportEnum(StrEnum):
    bowling = "bowling"
    dodgeball = "dodgeball"
    kickball = "kickball"
    pickleball = "pickleball"

    @classmethod
    def _missing_(cls, value: object) -> SportEnum | None:
        if isinstance(value, str):
            return cls(value.strip().lower().strip("#+"))
        return None


class DayOfWeekEnum(StrEnum):
    sunday = "sunday"
    monday = "monday"
    tuesday = "tuesday"
    wednesday = "wednesday"
    thursday = "thursday"
    friday = "friday"
    saturday = "saturday"

    @classmethod
    def _missing_(cls, value: object) -> DayOfWeekEnum | None:
        if isinstance(value, str):
            return cls(value.strip().lower().strip("#+"))
        return None


class DivisionEnum(StrEnum):
    open = "open"
    wtnb = "wtnb"

    @classmethod
    def _missing_(cls, value: object) -> DivisionEnum | None:
        if isinstance(value, str):
            return cls(value.strip().lower().strip("#+"))
        return None


Year = Annotated[int, Field(ge=2009, le=2030)]
StartDate = Annotated[date, Field(description="Filter start date (inclusive)")]
EndDate = Annotated[date, Field(description="Filter end date (inclusive)")]
