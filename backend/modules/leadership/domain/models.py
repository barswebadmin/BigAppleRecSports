"""
Leadership Domain Models using Pydantic.

Pure domain objects with NO external integration dependencies.
"""
from enum import Enum
from typing import Optional, Dict, Any, List, Set
from pydantic import BaseModel, Field, field_validator


class LeadershipMember(BaseModel):
    """
    A member of BARS leadership team.
    
    Minimal model focused on member identity and role, not provisioning state.
    Provisioning status is tracked separately in WorkflowState.
    """
    name: str = Field(description="Full name of the member")
    personal_email: str = Field(description="Personal email address (REQUIRED at instantiation)")
    role: str = Field(description="Leadership role key (e.g., 'bowling.director', 'executive_board.commissioner')")
    
    # Optional fields (may be missing until enriched)
    bars_email: Optional[str] = Field(default=None, description="BARS email (may not exist until created)")
    phone: Optional[str] = Field(default=None, description="Phone number")
    birthday: Optional[str] = Field(default=None, description="Birthday (MM/DD or MM/DD/YYYY)")
    slack_user_id: Optional[str] = Field(default=None, description="Slack user ID (enriched from Slack)")
    photo_url: Optional[str] = Field(default=None, description="Profile photo URL (for About page)")
    
    @field_validator('personal_email', 'bars_email')
    @classmethod
    def normalize_email(cls, v: Optional[str]) -> Optional[str]:
        """Normalize emails: lowercase and strip whitespace."""
        if v is None or v == "":
            return None
        return v.strip().lower()
    
    def is_vacant(self) -> bool:
        """Check if this position is vacant."""
        return self.name.lower().strip() == "vacant"
    
    def is_complete(self) -> bool:
        """
        Check if member has minimum required data for provisioning.
        
        Vacant positions always complete.
        Normal members need: name + personal_email + bars_email + slack_user_id
        """
        if self.is_vacant():
            return True
        return bool(self.name and self.personal_email and self.bars_email and self.slack_user_id)
    
    model_config = {
        "str_strip_whitespace": True,
        "extra": "allow"  # Allow _csv_row, _csv_columns for tracking
    }


class Position(BaseModel):
    """Single position in hierarchy with section/sub_section/team/role structure."""
    section: str = Field(description="Top-level section (executive_board, bowling, etc.)")
    role: str = Field(description="Specific role (commissioner, director, etc.)")
    person: LeadershipMember = Field(description="Person in this position")
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
        person: LeadershipMember,
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


class ProvisionStepType(str, Enum):
    """Types of provisioning steps in the workflow."""
    BARS_EMAIL_CREATION = "bars_email_creation"
    DATA_ENRICHMENT = "data_enrichment"
    SLACK_USER_CREATION = "slack_user_creation"
    SLACK_GROUPS = "slack_groups"
    SLACK_CHANNELS = "slack_channels"
    GOOGLE_GROUPS = "google_groups"
    SHOPIFY_ABOUT_PAGE = "shopify_about_page"
    SHOPIFY_ROLES = "shopify_roles"


class MemberProvisionStatus(BaseModel):
    """
    Tracks provisioning status for a single member across all steps.
    
    This is workflow state, not part of LeadershipMember itself.
    """
    member: LeadershipMember = Field(description="The member being provisioned")
    
    bars_email_created: bool = Field(default=False, description="BARS email created")
    phone_enriched: bool = Field(default=False, description="Phone number enriched")
    birthday_enriched: bool = Field(default=False, description="Birthday enriched")
    slack_user_created: bool = Field(default=False, description="Slack user created")
    slack_groups_added: List[str] = Field(default_factory=list, description="Slack group IDs successfully added")
    slack_channels_added: List[str] = Field(default_factory=list, description="Slack channel IDs successfully added")
    google_groups_added: List[str] = Field(default_factory=list, description="Google group IDs successfully added")
    shopify_about_page_updated: bool = Field(default=False, description="Shopify About page updated")
    shopify_role_assigned: bool = Field(default=False, description="Shopify role assigned")
    
    errors: List[str] = Field(default_factory=list, description="Provisioning errors for this member")
    
    def add_error(self, step: ProvisionStepType, message: str) -> None:
        """Add an error for a specific step."""
        self.errors.append(f"[{step.value}] {message}")
    
    def is_fully_provisioned(self) -> bool:
        """Check if all provisioning steps completed successfully."""
        return (
            self.bars_email_created
            and self.phone_enriched
            and self.birthday_enriched
            and self.slack_user_created
            and len(self.slack_groups_added) > 0
            and len(self.slack_channels_added) > 0
            and len(self.google_groups_added) > 0
            and self.shopify_about_page_updated
            and len(self.errors) == 0
        )


class RoleMapping(BaseModel):
    """
    Maps a leadership role to platform-specific groups/channels/roles.
    
    Attribute names (e.g., "Leadership", "ExecutiveBoard") are resolved 
    against SlackConfig, GoogleConfig, ShopifyConfig for actual IDs.
    """
    role_key: str = Field(description="Unique role identifier (e.g., 'executive_board.commissioner')")
    display_name: str = Field(description="Human-readable role name")
    
    slack_groups: List[str] = Field(default_factory=list, description="Slack group attribute names")
    slack_channels: List[str] = Field(default_factory=list, description="Slack channel attribute names")
    google_groups: List[str] = Field(default_factory=list, description="Google group attribute names")
    shopify_role: Optional[str] = Field(default=None, description="Shopify role attribute name")
    
    model_config = {
        "str_strip_whitespace": True,
    }


class WorkflowState(BaseModel):
    """
    Complete state of the /update-bars-leadership workflow.
    
    Tracks all members and their provisioning status.
    """
    members: List[MemberProvisionStatus] = Field(default_factory=list, description="All members and their status")
    
    current_step: Optional[ProvisionStepType] = Field(default=None, description="Currently executing step")
    completed_steps: List[ProvisionStepType] = Field(default_factory=list, description="Steps completed")
    skipped_steps: List[ProvisionStepType] = Field(default_factory=list, description="Steps user chose to skip")
    
    workflow_errors: List[str] = Field(default_factory=list, description="Workflow-level errors (not member-specific)")
    
    def add_member(self, member: LeadershipMember) -> MemberProvisionStatus:
        """Add a new member to track and return their status."""
        status = MemberProvisionStatus(member=member)
        self.members.append(status)
        return status
    
    def get_member_status(self, personal_email: str) -> Optional[MemberProvisionStatus]:
        """Get provision status by personal email."""
        for status in self.members:
            if status.member.personal_email == personal_email:
                return status
        return None
    
    def mark_step_complete(self, step: ProvisionStepType) -> None:
        """Mark a workflow step as complete."""
        if step not in self.completed_steps:
            self.completed_steps.append(step)
        self.current_step = None
    
    def mark_step_skipped(self, step: ProvisionStepType) -> None:
        """Mark a workflow step as skipped."""
        if step not in self.skipped_steps:
            self.skipped_steps.append(step)
        self.current_step = None
    
    def get_summary(self) -> Dict[str, Any]:
        """Get workflow summary stats."""
        total_members = len(self.members)
        fully_provisioned = sum(1 for m in self.members if m.is_fully_provisioned())
        members_with_errors = sum(1 for m in self.members if len(m.errors) > 0)
        
        return {
            "total_members": total_members,
            "fully_provisioned": fully_provisioned,
            "members_with_errors": members_with_errors,
            "completed_steps": [s.value for s in self.completed_steps],
            "skipped_steps": [s.value for s in self.skipped_steps],
            "workflow_errors": len(self.workflow_errors),
        }
