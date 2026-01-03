"""
Test workflow models for /update-bars-leadership workflow.

Tests: MemberProvisionStatus, RoleMapping, WorkflowState
"""
import pytest
from modules.leadership.domain.models import (
    LeadershipMember,
    ProvisionStepType,
    MemberProvisionStatus,
    RoleMapping,
    WorkflowState,
)


@pytest.fixture
def base_member():
    """Base LeadershipMember for testing."""
    return LeadershipMember(
        name="John Doe",
        personal_email="john@gmail.com",
        role="executive_board.commissioner"
    )


@pytest.fixture
def base_provision_status(base_member):
    """Base MemberProvisionStatus for testing."""
    return MemberProvisionStatus(member=base_member)


@pytest.fixture
def fully_provisioned_status(base_member):
    """Fully provisioned member status."""
    return MemberProvisionStatus(
        member=base_member,
        bars_email_created=True,
        phone_enriched=True,
        birthday_enriched=True,
        slack_user_created=True,
        slack_groups_added=["G1"],
        slack_channels_added=["C1"],
        google_groups_added=["GG1"],
        shopify_about_page_updated=True,
        errors=[]
    )


class TestMemberProvisionStatus:
    """Test MemberProvisionStatus model."""
    
    def test_initialization(self, base_provision_status, base_member):
        """Test default initialization of provision status."""
        assert base_provision_status.member == base_member
        assert base_provision_status.bars_email_created is False
        assert base_provision_status.phone_enriched is False
        assert base_provision_status.birthday_enriched is False
        assert base_provision_status.slack_user_created is False
        assert len(base_provision_status.slack_groups_added) == 0
        assert len(base_provision_status.slack_channels_added) == 0
        assert len(base_provision_status.google_groups_added) == 0
        assert base_provision_status.shopify_about_page_updated is False
        assert base_provision_status.shopify_role_assigned is False
        assert len(base_provision_status.errors) == 0
    
    def test_add_error(self, base_provision_status):
        """Test adding errors to provision status."""
        base_provision_status.add_error(ProvisionStepType.SLACK_USER_CREATION, "Failed to create user")
        base_provision_status.add_error(ProvisionStepType.GOOGLE_GROUPS, "Permission denied")
        
        assert len(base_provision_status.errors) == 2
        assert "[slack_user_creation]" in base_provision_status.errors[0]
        assert "Failed to create user" in base_provision_status.errors[0]
        assert "[google_groups]" in base_provision_status.errors[1]
        assert "Permission denied" in base_provision_status.errors[1]
    
    @pytest.mark.parametrize("field_to_change,expected_provisioned", [
        ({}, True),  # Fully provisioned
        ({"bars_email_created": False}, False),
        ({"phone_enriched": False}, False),
        ({"birthday_enriched": False}, False),
        ({"slack_user_created": False}, False),
        ({"slack_groups_added": []}, False),
        ({"slack_channels_added": []}, False),
        ({"google_groups_added": []}, False),
        ({"shopify_about_page_updated": False}, False),
        ({"errors": ["error"]}, False),
    ])
    def test_is_fully_provisioned(self, fully_provisioned_status, field_to_change, expected_provisioned):
        """Test is_fully_provisioned with various completion states."""
        for field, value in field_to_change.items():
            setattr(fully_provisioned_status, field, value)
        
        assert fully_provisioned_status.is_fully_provisioned() == expected_provisioned


class TestRoleMapping:
    """Test RoleMapping model."""
    
    def test_initialization(self):
        """Test role mapping initialization."""
        mapping = RoleMapping(
            role_key="executive_board.commissioner",
            display_name="Commissioner",
            slack_groups=["ExecutiveBoard", "Leadership"],
            slack_channels=["Leadership"],
            google_groups=["executive-board@bars.com"],
            shopify_role="Staff"
        )
        
        assert mapping.role_key == "executive_board.commissioner"
        assert mapping.display_name == "Commissioner"
        assert len(mapping.slack_groups) == 2
        assert "ExecutiveBoard" in mapping.slack_groups
        assert len(mapping.slack_channels) == 1
        assert len(mapping.google_groups) == 1
        assert mapping.shopify_role == "Staff"
    
    def test_empty_platform_assignments(self):
        """Test role mapping with no platform assignments."""
        mapping = RoleMapping(
            role_key="committee_members.member",
            display_name="Committee Member"
        )
        
        assert len(mapping.slack_groups) == 0
        assert len(mapping.slack_channels) == 0
        assert len(mapping.google_groups) == 0
        assert mapping.shopify_role is None


@pytest.fixture
def base_workflow_state():
    """Base WorkflowState for testing."""
    return WorkflowState()


@pytest.fixture
def second_member():
    """Second member for multi-member tests."""
    return LeadershipMember(
        name="Jane Smith",
        personal_email="jane@gmail.com",
        role="bowling.director"
    )


class TestWorkflowState:
    """Test WorkflowState model."""
    
    def test_initialization(self, base_workflow_state):
        """Test workflow state initialization."""
        assert len(base_workflow_state.members) == 0
        assert base_workflow_state.current_step is None
        assert len(base_workflow_state.completed_steps) == 0
        assert len(base_workflow_state.skipped_steps) == 0
        assert len(base_workflow_state.workflow_errors) == 0
    
    def test_add_member(self, base_workflow_state, base_member):
        """Test adding members to workflow state."""
        status = base_workflow_state.add_member(base_member)
        
        assert len(base_workflow_state.members) == 1
        assert base_workflow_state.members[0] == status
        assert status.member == base_member
    
    def test_get_member_status(self, base_workflow_state, base_member, second_member):
        """Test retrieving member status by email."""
        base_workflow_state.add_member(base_member)
        base_workflow_state.add_member(second_member)
        
        status = base_workflow_state.get_member_status("john@gmail.com")
        assert status is not None
        assert status.member.name == "John Doe"
        
        status = base_workflow_state.get_member_status("nonexistent@gmail.com")
        assert status is None
    
    def test_mark_step_complete(self, base_workflow_state):
        """Test marking workflow steps as complete."""
        base_workflow_state.current_step = ProvisionStepType.BARS_EMAIL_CREATION
        
        base_workflow_state.mark_step_complete(ProvisionStepType.BARS_EMAIL_CREATION)
        
        assert ProvisionStepType.BARS_EMAIL_CREATION in base_workflow_state.completed_steps
        assert base_workflow_state.current_step is None
        
        base_workflow_state.mark_step_complete(ProvisionStepType.BARS_EMAIL_CREATION)
        assert len(base_workflow_state.completed_steps) == 1
    
    def test_mark_step_skipped(self, base_workflow_state):
        """Test marking workflow steps as skipped."""
        base_workflow_state.current_step = ProvisionStepType.SHOPIFY_ROLES
        
        base_workflow_state.mark_step_skipped(ProvisionStepType.SHOPIFY_ROLES)
        
        assert ProvisionStepType.SHOPIFY_ROLES in base_workflow_state.skipped_steps
        assert base_workflow_state.current_step is None
        
        base_workflow_state.mark_step_skipped(ProvisionStepType.SHOPIFY_ROLES)
        assert len(base_workflow_state.skipped_steps) == 1
    
    def test_get_summary(self, base_workflow_state, fully_provisioned_status, second_member):
        """Test workflow summary generation."""
        base_workflow_state.members.append(fully_provisioned_status)
        
        status2 = base_workflow_state.add_member(second_member)
        status2.add_error(ProvisionStepType.SLACK_USER_CREATION, "Failed")
        
        base_workflow_state.mark_step_complete(ProvisionStepType.BARS_EMAIL_CREATION)
        base_workflow_state.mark_step_skipped(ProvisionStepType.SHOPIFY_ROLES)
        base_workflow_state.workflow_errors.append("General error")
        
        summary = base_workflow_state.get_summary()
        
        assert summary["total_members"] == 2
        assert summary["fully_provisioned"] == 1
        assert summary["members_with_errors"] == 1
        assert "bars_email_creation" in summary["completed_steps"]
        assert "shopify_roles" in summary["skipped_steps"]
        assert summary["workflow_errors"] == 1

