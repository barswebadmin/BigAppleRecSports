"""
Test domain models - write BEFORE implementing models (TDD).

Tests for:
- PersonInfo: Domain model for leadership person data
- Position: Domain model for a single leadership position
- LeadershipHierarchy: Domain model for entire hierarchy structure
"""
import pytest
from modules.leadership.domain.models import (
    PersonInfo,
    Position,
    LeadershipHierarchy,
)


class TestPersonInfo:
    """Test PersonInfo domain model."""
    
    def test_person_info_creation_minimal(self):
        """Test creating PersonInfo with minimal required fields."""
        person = PersonInfo(
            name="John Doe",
            bars_email="john@bigapplerecsports.com"
        )
        
        assert person.name == "John Doe"
        assert person.bars_email == "john@bigapplerecsports.com"
        assert person.personal_email is None
        assert person.phone is None
        assert person.birthday is None
        assert person.slack_user_id is None
    
    def test_person_info_creation_full(self):
        """Test creating PersonInfo with all fields."""
        person = PersonInfo(
            name="John Doe",
            bars_email="john@bigapplerecsports.com",
            personal_email="john@gmail.com",
            phone="555-0100",
            birthday="01/15",
            slack_user_id="U1234567890"
        )
        
        assert person.name == "John Doe"
        assert person.bars_email == "john@bigapplerecsports.com"
        assert person.personal_email == "john@gmail.com"
        assert person.phone == "555-0100"
        assert person.birthday == "01/15"
        assert person.slack_user_id == "U1234567890"
    
    def test_person_info_is_vacant(self):
        """Test vacant position detection."""
        vacant_person = PersonInfo(name="Vacant", bars_email="")
        assert vacant_person.is_vacant() is True
        
        vacant_person_whitespace = PersonInfo(name="  vacant  ", bars_email="")
        assert vacant_person_whitespace.is_vacant() is True
        
        normal_person = PersonInfo(name="John Doe", bars_email="john@bars.com")
        assert normal_person.is_vacant() is False
    
    def test_person_info_is_complete_normal(self):
        """Test completeness check for normal positions."""
        # Complete normal person (name + bars_email required)
        complete = PersonInfo(
            name="John Doe",
            bars_email="john@bars.com",
            personal_email="john@gmail.com",
            phone="555-0100",
            birthday="01/15"
        )
        assert complete.is_complete() is True
        
        # Incomplete - missing bars_email
        incomplete = PersonInfo(name="John Doe", bars_email="")
        assert incomplete.is_complete() is False
        
        # Incomplete - missing name
        incomplete2 = PersonInfo(name="", bars_email="john@bars.com")
        assert incomplete2.is_complete() is False
    
    def test_person_info_is_complete_vacant(self):
        """Test completeness check for vacant positions."""
        # Vacant positions are always considered complete
        vacant = PersonInfo(name="Vacant", bars_email="")
        assert vacant.is_complete() is True
    
    def test_person_info_email_normalization(self):
        """Test that emails are normalized (lowercased, stripped)."""
        person = PersonInfo(
            name="John Doe",
            bars_email="  John@BIGAPPLERECSPORTS.com  "
        )
        
        # Pydantic validator should normalize
        assert person.bars_email == "john@bigapplerecsports.com"
    
    def test_person_info_accepts_any_string_email(self):
        """
        Test that any string is accepted for email (lenient for CSV data).
        
        Business Rule: We normalize but don't strictly validate emails
        since CSV data might have various formats or be incomplete.
        """
        # Should accept any string and normalize it
        person = PersonInfo(name="John Doe", bars_email="NOT-perfect@email")
        assert person.bars_email == "not-perfect@email"  # Normalized
        
        # Even non-email strings accepted (CSV might have placeholders)
        person2 = PersonInfo(name="Jane Doe", bars_email="TBD")
        assert person2.bars_email == "tbd"


class TestPosition:
    """Test Position domain model."""
    
    def test_position_creation_simple(self):
        """Test creating a simple position."""
        person = PersonInfo(name="John Doe", bars_email="john@bars.com")
        position = Position(
            section="executive_board",
            role="commissioner",
            person=person
        )
        
        assert position.section == "executive_board"
        assert position.role == "commissioner"
        assert position.sub_section is None
        assert position.team is None
        assert position.person == person
    
    def test_position_creation_nested(self):
        """Test creating a nested position (with sub_section and team)."""
        person = PersonInfo(name="Jane Smith", bars_email="jane@bars.com")
        position = Position(
            section="dodgeball",
            role="director",
            person=person,
            sub_section="smallball_advanced",
            team="operations"
        )
        
        assert position.section == "dodgeball"
        assert position.sub_section == "smallball_advanced"
        assert position.team == "operations"
        assert position.role == "director"
    
    def test_position_display_name_simple(self):
        """Test display name for simple position."""
        person = PersonInfo(name="John Doe", bars_email="john@bars.com")
        position = Position(
            section="executive_board",
            role="commissioner",
            person=person
        )
        
        assert position.display_name() == "Executive Board - Commissioner"
    
    def test_position_display_name_nested(self):
        """Test display name for nested position."""
        person = PersonInfo(name="Jane Smith", bars_email="jane@bars.com")
        position = Position(
            section="dodgeball",
            role="director",
            person=person,
            sub_section="smallball_advanced"
        )
        
        # Should include sub_section in display name
        expected = "Dodgeball - Smallball Advanced - Director"
        assert position.display_name() == expected
    
    def test_position_to_dict(self):
        """Test serialization to dict (for existing JSON format compatibility)."""
        person = PersonInfo(
            name="John Doe",
            bars_email="john@bars.com",
            slack_user_id="U1234567890"
        )
        position = Position(
            section="executive_board",
            role="commissioner",
            person=person
        )
        
        result = position.to_dict()
        
        # Should match existing JSON structure
        assert result["name"] == "John Doe"
        assert result["bars_email"] == "john@bars.com"
        assert result["slack_user_id"] == "U1234567890"


class TestLeadershipHierarchy:
    """Test LeadershipHierarchy domain model."""
    
    def test_hierarchy_creation(self):
        """Test creating empty hierarchy."""
        hierarchy = LeadershipHierarchy()
        
        # Should have all sections initialized
        assert "executive_board" in hierarchy.sections
        assert "cross_sport" in hierarchy.sections
        assert "bowling" in hierarchy.sections
        assert "dodgeball" in hierarchy.sections
        assert "kickball" in hierarchy.sections
        assert "pickleball" in hierarchy.sections
        assert "committee_members" in hierarchy.sections
        
        # Vacant positions should be empty set
        assert isinstance(hierarchy.vacant_positions, set)
        assert len(hierarchy.vacant_positions) == 0
    
    def test_add_position_simple(self):
        """Test adding a simple position."""
        hierarchy = LeadershipHierarchy()
        person = PersonInfo(name="John Doe", bars_email="john@bars.com")
        
        hierarchy.add_position(
            section="executive_board",
            role="commissioner",
            person=person
        )
        
        # Should be retrievable
        result = hierarchy.get_position("executive_board", "commissioner")
        assert result is not None
        assert result["name"] == "John Doe"
    
    def test_add_position_nested(self):
        """Test adding a nested position with sub_section."""
        hierarchy = LeadershipHierarchy()
        person = PersonInfo(name="Jane Smith", bars_email="jane@bars.com")
        
        hierarchy.add_position(
            section="dodgeball",
            role="director",
            person=person,
            sub_section="smallball_advanced"
        )
        
        # Should be retrievable with sub_section
        result = hierarchy.get_position(
            "dodgeball",
            "director",
            sub_section="smallball_advanced"
        )
        assert result is not None
        assert result["name"] == "Jane Smith"
    
    def test_add_vacant_position(self):
        """Test that vacant positions are tracked separately."""
        hierarchy = LeadershipHierarchy()
        vacant_person = PersonInfo(name="Vacant", bars_email="")
        
        hierarchy.add_position(
            section="dodgeball",
            role="ops_manager",
            person=vacant_person,
            sub_section="foamball"
        )
        
        # Should be in vacant_positions set
        expected_key = "dodgeball.foamball.ops_manager"
        assert expected_key in hierarchy.vacant_positions
        
        # Should NOT be in regular sections
        result = hierarchy.get_position(
            "dodgeball",
            "ops_manager",
            sub_section="foamball"
        )
        assert result is None
    
    def test_get_all_emails(self):
        """Test extracting all BARS emails for lookup."""
        hierarchy = LeadershipHierarchy()
        
        person1 = PersonInfo(name="John Doe", bars_email="john@bars.com")
        person2 = PersonInfo(name="Jane Smith", bars_email="jane@bars.com")
        person3 = PersonInfo(name="Vacant", bars_email="")  # Should be excluded
        
        hierarchy.add_position("executive_board", "commissioner", person1)
        hierarchy.add_position("executive_board", "vice_commissioner", person2)
        hierarchy.add_position("dodgeball", "director", person3, sub_section="foamball")
        
        emails = hierarchy.get_all_emails()
        
        assert len(emails) == 2
        assert "john@bars.com" in emails
        assert "jane@bars.com" in emails
        assert "" not in emails
    
    def test_to_dict_compatibility(self):
        """Test serialization to existing JSON format."""
        hierarchy = LeadershipHierarchy()
        
        person = PersonInfo(
            name="John Doe",
            bars_email="john@bars.com",
            slack_user_id="U1234567890"
        )
        
        hierarchy.add_position("executive_board", "commissioner", person)
        
        result = hierarchy.to_dict()
        
        # Must match existing JSON structure
        assert "executive_board" in result
        assert result["executive_board"]["commissioner"]["name"] == "John Doe"
        assert result["executive_board"]["commissioner"]["bars_email"] == "john@bars.com"
        assert result["executive_board"]["commissioner"]["slack_user_id"] == "U1234567890"
    
    def test_get_summary(self):
        """Test getting summary statistics."""
        hierarchy = LeadershipHierarchy()
        
        person1 = PersonInfo(name="John Doe", bars_email="john@bars.com", slack_user_id="U123")
        person2 = PersonInfo(name="Jane Smith", bars_email="jane@bars.com")  # No Slack ID
        person3 = PersonInfo(name="Vacant", bars_email="")
        
        hierarchy.add_position("executive_board", "commissioner", person1)
        hierarchy.add_position("executive_board", "vice_commissioner", person2)
        hierarchy.add_position("dodgeball", "director", person3, sub_section="foamball")
        
        summary = hierarchy.get_summary()
        
        assert summary["total"] == 2  # Vacant not counted in total
        assert summary["with_slack_id"] == 1
        assert summary["vacant"] == 1

