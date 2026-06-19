"""Slack Usergroup models for usergroups.list API responses"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, field_validator

from shared_utilities.pydantic_config import DEFAULT_CONFIG_DICT


class SlackGroup(BaseModel):
    model_config = ConfigDict(
        alias_generator=DEFAULT_CONFIG_DICT['alias_generator'],  # pyright: ignore[reportTypedDictNotRequiredAccess]
        populate_by_name=True,
        extra="allow"
    )

    id: str
    team_id: str
    name: str
    handle: str
    description: Optional[str] = None
    date_create: Optional[int] = None
    date_update: Optional[int] = None
    date_delete: Optional[int] = None
    auto_type: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    deleted_by: Optional[str] = None
    prefs: Optional[Dict[str, Any]] = None
    users: Optional[List[str]] = None
    user_count: Optional[int] = None
    channel_count: Optional[int] = None
    is_external: Optional[bool] = None
    is_usergroup: Optional[bool] = None

    @field_validator("id")
    @classmethod
    def validate_group_id(cls, v: str) -> str:
        if not v:
            raise ValueError("Group ID cannot be empty")
        if not v.startswith("S"):
            raise ValueError(f"Invalid Slack usergroup ID: must start with 'S', got '{v}'")
        if len(v) != 11:
            raise ValueError(f"Invalid Slack usergroup ID: must be 11 characters, got {len(v)}")
        if not v.isalnum():
            raise ValueError(f"Invalid Slack usergroup ID: must be alphanumeric, got '{v}'")
        return v

    @staticmethod
    def is_valid_group_id(group_id: str) -> bool:
        if not group_id or not isinstance(group_id, str):
            return False
        return group_id.startswith("S") and len(group_id) == 11 and group_id.isalnum()


class Groups:
    """Slack User Groups (subteams), accessible by PascalCase attributes."""

    class _Group:
        def __init__(self, id: str, name: str):
            self.id = id
            self.name = name

        def __str__(self) -> str:
            return self.id

    # Top-level
    Kickball   = _Group("<!subteam^S08L2521XAM>", "kickball")
    Bowling    = _Group("<!subteam^S08KJJ02738>", "bowling")
    Pickleball = _Group("<!subteam^S08KTJ33Z9R>", "pickleball")
    Dodgeball  = _Group("<!subteam^S08KJJ5CL4W>", "dodgeball")

    # Bowling
    BowlingMonday = _Group("<!subteam^S09FKLZGP7X>", "bowling-monday")
    BowlingSunday = _Group("<!subteam^S09F7G2B0VD>", "bowling-sunday")

    # Dodgeball
    DodgeballWtnbSocial        = _Group("<!subteam^S09FKLN0SBX>", "dodgeball-wtnb-social")
    DodgeballWtnbDraft         = _Group("<!subteam^S09GFAVQ41E>", "dodgeball-wtnb-draft")
    DodgeballBigBall           = _Group("<!subteam^S09FHSR9ZNF>", "dodgeball-bigball")
    DodgeballSmallBallSocial   = _Group("<!subteam^S09FMV42FGA>", "dodgeball-smallball-social")
    DodgeballSmallBallAdvanced = _Group("<!subteam^S09FKKU1U4D>", "dodgeball-smallball-advanced")
    DodgeballFoamBall          = _Group("<!subteam^S09GFD2D67J>", "dodgeball-foamball")

    # Kickball
    KickballMonday       = _Group("<!subteam^S09FN0P7UTC>", "kickball-monday")
    KickballTuesday      = _Group("<!subteam^S09FSNWKTKN>", "kickball-tuesday")
    KickballWednesday    = _Group("<!subteam^S09G205V0JD>", "kickball-wednesday")
    KickballWtnbThursday = _Group("<!subteam^S09FN0WGZKL>", "kickball-wtnb-thursday")
    KickballWtnbSocial   = _Group("<!subteam^S09FKLYHB2R>", "kickball-wtnb-social")
    KickballThursday     = _Group("<!subteam^S09G22N4SG1>", "kickball-thursday")
    KickballSaturday     = _Group("<!subteam^S09G21RM22D>", "kickball-saturday-open")
    KickballSunday       = _Group("<!subteam^S09FSNVD5EY>", "kickball-sunday")

    # Pickleball
    PickleballTuesday   = _Group("<!subteam^S09G20K6LM7>", "pickleball-tuesday")
    PickleballThursday  = _Group("<!subteam^S09F7GCF91D>", "pickleball-thursday")
    PickleballSundayWtnb = _Group("<!subteam^S09FN14308J>", "pickleball-sunday-wtnb")
    PickleballSundayOpen = _Group("<!subteam^S09FKM2JA9K>", "pickleball-sunday-open")

    @classmethod
    def all(cls) -> Dict[str, Dict[str, str]]:
        return {k: {"id": v.id, "name": f"#{v.name}"} for k, v in cls.__dict__.items() if isinstance(v, cls._Group)}

    @classmethod
    def get(cls, key: str) -> Dict[str, str]:
        if hasattr(cls, key):
            v = getattr(cls, key)
            if isinstance(v, cls._Group):
                return {"id": v.id, "name": f"#{v.name}"}
        for v in cls.__dict__.values():
            if isinstance(v, cls._Group) and v.name.lower() == key.lower():
                return {"id": v.id, "name": f"#{v.name}"}
        return {"id": "@here", "name": "@here"}


SlackGroupConstants = Groups
