"""
Leadership Domain Models using Pydantic.

Pure domain objects with NO external integration dependencies.
"""
from typing import Optional, Dict, Any, List, Set
from pydantic import BaseModel, Field, field_validator


class PersonInfo(BaseModel):
    """
    Person in leadership hierarchy.
    
    Vacant if name="Vacant" (case-insensitive).
    Complete if name + bars_email present.
    """
    name: str
    bars_email: str = Field(default="", description="Primary BARS email for Slack lookup")
    personal_email: Optional[str] = Field(default=None, description="Personal email address")
    phone: Optional[str] = Field(default=None, description="Phone number")
    birthday: Optional[str] = Field(default=None, description="Birthday (MM/DD format)")
    slack_user_id: Optional[str] = Field(default=None, description="Slack user ID (enriched)")
    
    @field_validator('bars_email', 'personal_email')
    @classmethod
    def normalize_email(cls, v: Optional[str]) -> Optional[str]:
        """Normalize emails: lowercase and strip whitespace."""
        if v is None or v == "":
            return v if v == "" else None
        return v.strip().lower()
    
    def is_vacant(self) -> bool:
        """Check if this position is vacant."""
        return self.name.lower().strip() == "vacant"
    
    def is_complete(self) -> bool:
        """Vacant positions always complete. Normal positions need name + bars_email."""
        if self.is_vacant():
            return True
        return bool(self.name and self.bars_email)
    
    model_config = {
        "str_strip_whitespace": True,
    }


class Position(BaseModel):
    """Single position in hierarchy with section/sub_section/team/role structure."""
    section: str = Field(description="Top-level section (executive_board, bowling, etc.)")
    role: str = Field(description="Specific role (commissioner, director, etc.)")
    person: PersonInfo = Field(description="Person in this position")
    sub_section: Optional[str] = Field(default=None, description="Nested sub-section (optional)")
    team: Optional[str] = Field(default=None, description="Team level (optional)")
    
    def display_name(self) -> str:
        """Generate human-readable name from hierarchy path."""
        parts = [self.section.replace("_", " ").title()]
        
        if self.sub_section:
            parts.append(self.sub_section.replace("_", " ").title())
        
        if self.team:
            parts.append(self.team.replace("_", " ").title())
        
        parts.append(self.role.replace("_", " ").title())
        
        return " - ".join(parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to flat dict for existing JSON format compatibility.
        
        Returns person fields as a flat dict (matches existing structure).
        """
        return {
            "name": self.person.name,
            "bars_email": self.person.bars_email,
            "personal_email": self.person.personal_email,
            "phone": self.person.phone,
            "birthday": self.person.birthday,
            "slack_user_id": self.person.slack_user_id,
        }


class LeadershipHierarchy(BaseModel):
    """Complete organizational hierarchy. Maintains existing JSON format compatibility."""
    sections: Dict[str, Any] = Field(
        default_factory=lambda: {
            "executive_board": {},
            "cross_sport": {},
            "bowling": {},
            "dodgeball": {},
            "kickball": {},
            "pickleball": {},
            "committee_members": [],
        },
        description="Hierarchical structure of all leadership positions"
    )
    vacant_positions: Set[str] = Field(
        default_factory=set,
        description="Set of position keys that are vacant"
    )
    
    def add_position(
        self,
        section: str,
        role: str,
        person: PersonInfo,
        sub_section: Optional[str] = None,
        team: Optional[str] = None
    ) -> None:
        """Add position. Vacant go to vacant_positions set, others to sections dict."""
        # Handle vacant positions
        if person.is_vacant():
            position_key = f"{section}"
            if sub_section:
                position_key += f".{sub_section}"
            if team:
                position_key += f".{team}"
            position_key += f".{role}"
            self.vacant_positions.add(position_key)
            return
        
        # Handle committee_members (list) specially
        if section == "committee_members":
            self.sections["committee_members"].append(person.model_dump(exclude_none=False))
            return
        
        # Navigate to correct location in hierarchy
        target = self.sections[section]
        
        if sub_section:
            if sub_section not in target:
                target[sub_section] = {}
            target = target[sub_section]
        
        if team:
            if team not in target:
                target[team] = {}
            target = target[team]
        
        # Store person data as dict
        target[role] = person.model_dump(exclude_none=False)
    
    def get_position(
        self,
        section: str,
        role: str,
        sub_section: Optional[str] = None,
        team: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get a position from the hierarchy."""
        try:
            target = self.sections.get(section, {})
            
            if sub_section:
                target = target.get(sub_section, {})
            
            if team:
                target = target.get(team, {})
            
            return target.get(role)
        except (KeyError, AttributeError):
            return None
    
    def get_all_emails(self) -> List[str]:
        """Extract all non-empty BARS emails (excludes vacant positions)."""
        emails = []
        
        def extract_emails(obj: Any) -> None:
            if isinstance(obj, dict):
                # Check if this is a person dict
                if "bars_email" in obj and obj["bars_email"]:
                    emails.append(obj["bars_email"])
                else:
                    # Recurse into nested dicts
                    for value in obj.values():
                        extract_emails(value)
            elif isinstance(obj, list):
                for item in obj:
                    extract_emails(item)
        
        extract_emails(self.sections)
        return emails
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dict for existing JSON format compatibility.
        
        Returns the sections dict directly (matches existing structure).
        """
        result = {}
        for section_key, section_value in self.sections.items():
            result[section_key] = section_value
        result["vacant_positions"] = list(self.vacant_positions)
        return result
    
    def get_summary(self) -> Dict[str, int]:
        """Get summary: total, with_slack_id, vacant counts."""
        total = 0
        with_slack_id = 0
        
        def count_positions(obj: Any) -> None:
            nonlocal total, with_slack_id
            
            if isinstance(obj, dict):
                # Check if this is a person dict
                if "name" in obj:
                    total += 1
                    if obj.get("slack_user_id"):
                        with_slack_id += 1
                else:
                    # Recurse into nested dicts
                    for value in obj.values():
                        count_positions(value)
            elif isinstance(obj, list):
                for item in obj:
                    count_positions(item)
        
        count_positions(self.sections)
        
        return {
            "total": total,
            "with_slack_id": with_slack_id,
            "vacant": len(self.vacant_positions)
        }
    
    model_config = {
        "arbitrary_types_allowed": True,
    }

