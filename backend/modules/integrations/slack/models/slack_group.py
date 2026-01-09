"""Slack Usergroup models for usergroups.info and usergroups.list API responses"""

from typing import List, Optional, Any, Dict
from pydantic import field_validator, ConfigDict
from shared.model_config import ApiModel


class SlackGroup(ApiModel):
    """
    Slack usergroup information from usergroups.info and usergroups.list API.
    
    Based on Slack's usergroups API response structure.
    Only essential fields are required. All other fields are optional without defaults,
    allowing distinction between API-provided values and default values.
    Extra fields from API responses are preserved via extra='allow'.
    
    Use model_fields_set to check which fields were actually provided in the API response.
    """
    model_config = ConfigDict(extra='allow')
    
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
    
    @field_validator('id')
    @classmethod
    def validate_group_id(cls, v: str) -> str:
        """Validate that group ID follows Slack format: starts with S, 11 chars, alphanumeric."""
        if not v:
            raise ValueError("Group ID cannot be empty")
        if not v.startswith('S'):
            raise ValueError(f"Invalid Slack usergroup ID: must start with 'S', got '{v}'")
        if len(v) != 11:
            raise ValueError(f"Invalid Slack usergroup ID: must be 11 characters, got {len(v)} characters")
        if not v.isalnum():
            raise ValueError(f"Invalid Slack usergroup ID: must be alphanumeric, got '{v}'")
        return v
    
    @staticmethod
    def is_valid_group_id(group_id: str) -> bool:
        """
        Check if a string is a valid Slack usergroup ID format.
        
        Args:
            group_id: String to validate
            
        Returns:
            True if valid Slack usergroup ID format, False otherwise
            
        Example:
            >>> SlackGroup.is_valid_group_id("S08L2521XAM")
            True
            >>> SlackGroup.is_valid_group_id("invalid")
            False
        """
        if not group_id or not isinstance(group_id, str):
            return False
        return (group_id.startswith('S') and 
                len(group_id) == 11 and 
                group_id.isalnum())


# --------------------
# Groups Constants (migrated from config_old_deprecated/slack.py)
# --------------------
class Groups:
    """Slack User Groups (subteams), accessible by PascalCase attributes only."""

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
    DodgeballWtnbSocial       = _Group("<!subteam^S09FKLN0SBX>", "dodgeball-wtnb-social")
    DodgeballWtnbDraft        = _Group("<!subteam^S09GFAVQ41E>", "dodgeball-wtnb-draft")
    DodgeballBigBall           = _Group("<!subteam^S09FHSR9ZNF>", "dodgeball-bigball")
    DodgeballSmallBallSocial  = _Group("<!subteam^S09FMV42FGA>", "dodgeball-smallball-social")
    DodgeballSmallBallAdvanced = _Group("<!subteam^S09FKKU1U4D>", "dodgeball-smallball-advanced")
    DodgeballFoamBall         = _Group("<!subteam^S09GFD2D67J>", "dodgeball-foamball")

    # Kickball
    KickballMonday      = _Group("<!subteam^S09FN0P7UTC>", "kickball-monday")
    KickballTuesday     = _Group("<!subteam^S09FSNWKTKN>", "kickball-tuesday")
    KickballWednesday   = _Group("<!subteam^S09G205V0JD>", "kickball-wednesday")
    KickballWtnbThursday= _Group("<!subteam^S09FN0WGZKL>", "kickball-wtnb-thursday")
    KickballWtnbSocial  = _Group("<!subteam^S09FKLYHB2R>", "kickball-wtnb-social")
    KickballThursday    = _Group("<!subteam^S09G22N4SG1>", "kickball-thursday")
    KickballSaturday    = _Group("<!subteam^S09G21RM22D>", "kickball-saturday-open")
    KickballSunday      = _Group("<!subteam^S09FSNVD5EY>", "kickball-sunday")

    # Pickleball
    PickleballTuesday   = _Group("<!subteam^S09G20K6LM7>", "pickleball-tuesday")
    PickleballThursday        = _Group("<!subteam^S09F7GCF91D>", "pickleball-thursday")
    PickleballSundayWtnb      = _Group("<!subteam^S09FN14308J>", "pickleball-sunday-wtnb")
    PickleballSundayOpen      = _Group("<!subteam^S09FKM2JA9K>", "pickleball-sunday-open")

    @classmethod
    def all(cls) -> dict[str, dict[str, str]]:
        """Return all groups as {PascalCaseName: {'id': mention, 'name': '#friendly'}}"""
        out = {}
        for k, v in cls.__dict__.items():
            if isinstance(v, cls._Group):
                out[k] = {"id": v.id, "name": f"#{v.name}"}
        return out

    @classmethod
    def get(cls, key: str) -> Dict[str, str]:
        """
        Lookup by PascalCase attribute name (e.g., 'Dodgeball')
        or by lowercase friendly name (e.g., 'dodgeball').
        Returns {'id': mention, 'name': '#friendly'}.
        """
        # Try PascalCase attribute
        if hasattr(cls, key):
            v = getattr(cls, key)
            if isinstance(v, cls._Group):
                return {"id": v.id, "name": f"#{v.name}"}

        # Try lowercase friendly
        for v in cls.__dict__.values():
            if isinstance(v, cls._Group) and v.name.lower() == key.lower():
                return {"id": v.id, "name": f"#{v.name}"}

        return {"id": "@here", "name": "@here"}


# Convenience alias for backward compatibility
SlackGroupConstants = Groups

