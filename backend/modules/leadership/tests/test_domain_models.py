"""
Test domain models using pytest parameterization.

Tests: LeadershipMember, Position, LeadershipHierarchy
"""
import pytest
from modules.leadership.domain.models import (
    LeadershipMember,
    Position,
    LeadershipHierarchy,
)


class TestLeadershipMember:
    """Test LeadershipMember (LeadershipMember) domain model."""
    
    @pytest.mark.parametrize("name,personal_email,role,expected_vacant", [
        ("Vacant", "vacant@placeholder.com", "test.role", True),
        ("  vacant  ", "vacant@placeholder.com", "test.role", True),
        ("John Doe", "john@gmail.com", "executive_board.commissioner", False),
    ])
    def test_is_vacant(self, name, personal_email, role, expected_vacant):
        """Test vacant position detection with various inputs."""
        person = LeadershipMember(name=name, personal_email=personal_email, role=role)
        assert person.is_vacant() == expected_vacant
    
    @pytest.mark.parametrize("name,personal_email,role,bars_email,slack_user_id,expected_complete", [
        ("John Doe", "john@gmail.com", "exec.comm", "john@bars.com", "U123", True),
        ("John Doe", "john@gmail.com", "exec.comm", "john@bars.com", None, False),
        ("John Doe", "john@gmail.com", "exec.comm", None, "U123", False),
        ("", "john@gmail.com", "exec.comm", "john@bars.com", "U123", False),
        ("Vacant", "vacant@placeholder.com", "exec.comm", None, None, True),
    ])
    def test_is_complete(self, name, personal_email, role, bars_email, slack_user_id, expected_complete):
        """Test completeness validation with various field combinations."""
        person = LeadershipMember(
            name=name,
            personal_email=personal_email,
            role=role,
            bars_email=bars_email,
            slack_user_id=slack_user_id
        )
        assert person.is_complete() == expected_complete
    
    @pytest.mark.parametrize("input_email,expected_email", [
        ("  John@BIGAPPLERECSPORTS.com  ", "john@bigapplerecsports.com"),
        ("NOT-perfect@email", "not-perfect@email"),
        ("TBD", "tbd"),
    ])
    def test_email_normalization(self, input_email, expected_email):
        """Test that emails are normalized (lowercased, stripped)."""
        person = LeadershipMember(
            name="John Doe",
            personal_email="john@gmail.com",
            role="test.role",
            bars_email=input_email
        )
        assert person.bars_email == expected_email
    
    def test_full_person_creation(self):
        """Test creating LeadershipMember with all fields."""
        person = LeadershipMember(
            name="John Doe",
            personal_email="john@gmail.com",
            role="executive_board.commissioner",
            bars_email="john@bigapplerecsports.com",
            phone="555-0100",
            birthday="01/15",
            slack_user_id="U1234567890",
            photo_url="https://example.com/photo.jpg"
        )
        
        assert person.name == "John Doe"
        assert person.personal_email == "john@gmail.com"
        assert person.role == "executive_board.commissioner"
        assert person.bars_email == "john@bigapplerecsports.com"
        assert person.phone == "555-0100"
        assert person.birthday == "01/15"
        assert person.slack_user_id == "U1234567890"
        assert person.photo_url == "https://example.com/photo.jpg"


class TestPosition:
    """Test Position domain model."""
    
    @pytest.mark.parametrize("section,sub_section,role,expected_display", [
        ("executive_board", None, "commissioner", "Executive Board - Commissioner"),
        ("dodgeball", "smallball_advanced", "director", "Dodgeball - Smallball Advanced - Director"),
        ("bowling", "sunday", "ops_manager", "Bowling - Sunday - Ops Manager"),
    ])
    def test_display_name(self, section, sub_section, role, expected_display):
        """Test display name generation for various position structures."""
        person = LeadershipMember(
            name="John Doe",
            personal_email="john@gmail.com",
            role=f"{section}.{role}",
            bars_email="john@bars.com"
        )
        position = Position(
            section=section,
            role=role,
            person=person,
            sub_section=sub_section
        )
        assert position.display_name() == expected_display
    
    def test_to_dict_serialization(self):
        """Test serialization to dict matches existing JSON format."""
        person = LeadershipMember(
            name="John Doe",
            personal_email="john@gmail.com",
            role="executive_board.commissioner",
            bars_email="john@bars.com",
            slack_user_id="U1234567890"
        )
        position = Position(
            section="executive_board",
            role="commissioner",
            person=person
        )
        
        result = position.to_dict()
        
        assert result["name"] == "John Doe"
        assert result["bars_email"] == "john@bars.com"
        assert result["slack_user_id"] == "U1234567890"


class TestLeadershipHierarchy:
    """Test LeadershipHierarchy domain model."""
    
    def test_initialization(self):
        """Test hierarchy is initialized with all required sections."""
        hierarchy = LeadershipHierarchy()
        
        required_sections = [
            "executive_board", "cross_sport", "bowling",
            "dodgeball", "kickball", "pickleball", "committee_members"
        ]
        
        for section in required_sections:
            assert section in hierarchy.sections
        
        assert isinstance(hierarchy.vacant_positions, set)
        assert len(hierarchy.vacant_positions) == 0
    
    @pytest.mark.parametrize("section,role,sub_section", [
        ("executive_board", "commissioner", None),
        ("dodgeball", "director", "smallball_advanced"),
        ("bowling", "ops_manager", "sunday"),
    ])
    def test_add_and_get_position(self, section, role, sub_section):
        """Test adding and retrieving positions with various structures."""
        hierarchy = LeadershipHierarchy()
        person = LeadershipMember(
            name="John Doe",
            personal_email="john@gmail.com",
            role=f"{section}.{role}",
            bars_email="john@bars.com"
        )
        
        hierarchy.add_position(
            section=section,
            role=role,
            person=person,
            sub_section=sub_section
        )
        
        result = hierarchy.get_position(section, role, sub_section=sub_section)
        assert result is not None
        assert result["name"] == "John Doe"
    
    def test_vacant_position_handling(self):
        """Test that vacant positions are tracked separately."""
        hierarchy = LeadershipHierarchy()
        vacant_person = LeadershipMember(
            name="Vacant",
            personal_email="vacant@placeholder.com",
            role="dodgeball.ops_manager"
        )
        
        hierarchy.add_position(
            section="dodgeball",
            role="ops_manager",
            person=vacant_person,
            sub_section="foamball"
        )
        
        expected_key = "dodgeball.foamball.ops_manager"
        assert expected_key in hierarchy.vacant_positions
        
        result = hierarchy.get_position("dodgeball", "ops_manager", sub_section="foamball")
        assert result is None
    
    def test_get_all_emails(self):
        """Test extracting all non-vacant BARS emails."""
        hierarchy = LeadershipHierarchy()
        
        person1 = LeadershipMember(
            name="John Doe",
            personal_email="john@gmail.com",
            role="executive_board.commissioner",
            bars_email="john@bars.com"
        )
        person2 = LeadershipMember(
            name="Jane Smith",
            personal_email="jane@gmail.com",
            role="executive_board.vice_commissioner",
            bars_email="jane@bars.com"
        )
        person3 = LeadershipMember(
            name="Vacant",
            personal_email="vacant@placeholder.com",
            role="dodgeball.director"
        )
        
        hierarchy.add_position("executive_board", "commissioner", person1)
        hierarchy.add_position("executive_board", "vice_commissioner", person2)
        hierarchy.add_position("dodgeball", "director", person3, sub_section="foamball")
        
        emails = hierarchy.get_all_emails()
        
        assert len(emails) == 2
        assert "john@bars.com" in emails
        assert "jane@bars.com" in emails
        assert "" not in emails
    
    def test_to_dict_compatibility(self):
        """Test serialization matches existing JSON format."""
        hierarchy = LeadershipHierarchy()
        person = LeadershipMember(
            name="John Doe",
            personal_email="john@gmail.com",
            role="executive_board.commissioner",
            bars_email="john@bars.com",
            slack_user_id="U1234567890"
        )
        
        hierarchy.add_position("executive_board", "commissioner", person)
        result = hierarchy.to_dict()
        
        assert "executive_board" in result
        assert result["executive_board"]["commissioner"]["name"] == "John Doe"
        assert result["executive_board"]["commissioner"]["slack_user_id"] == "U1234567890"
    
    def test_get_summary(self):
        """Test summary statistics generation."""
        hierarchy = LeadershipHierarchy()
        
        person1 = LeadershipMember(
            name="John Doe",
            personal_email="john@gmail.com",
            role="executive_board.commissioner",
            bars_email="john@bars.com",
            slack_user_id="U123"
        )
        person2 = LeadershipMember(
            name="Jane Smith",
            personal_email="jane@gmail.com",
            role="executive_board.vice_commissioner",
            bars_email="jane@bars.com"
        )
        person3 = LeadershipMember(
            name="Vacant",
            personal_email="vacant@placeholder.com",
            role="dodgeball.director"
        )
        
        hierarchy.add_position("executive_board", "commissioner", person1)
        hierarchy.add_position("executive_board", "vice_commissioner", person2)
        hierarchy.add_position("dodgeball", "director", person3, sub_section="foamball")
        
        summary = hierarchy.get_summary()
        
        assert summary["total"] == 2
        assert summary["with_slack_id"] == 1
        assert summary["vacant"] == 1
