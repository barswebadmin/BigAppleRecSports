"""
Test CSV Parser Service - write BEFORE implementing (TDD).

Tests for:
- LeadershipCSVParser: Extracts leadership hierarchy from CSV data
- Position pattern matching (fuzzy, exact, WTNB priority)
- Section detection and categorization
"""
import pytest
from typing import List, Dict, Any
from modules.leadership.services.csv_parser import LeadershipCSVParser
from modules.leadership.domain.models import LeadershipHierarchy, PersonInfo


# Sample CSV data for testing
SAMPLE_CSV_SIMPLE = [
    ["POSITION", "NAME", "BARS EMAIL", "PERSONAL EMAIL", "PHONE", "BIRTHDAY"],
    ["Commissioner", "John Doe", "john@bars.com", "john@gmail.com", "555-0100", "01/15"],
    ["Vice Commissioner", "Jane Smith", "jane@bars.com", "", "", ""],
]

SAMPLE_CSV_WITH_SECTIONS = [
    ["POSITION", "NAME", "BARS EMAIL", "PERSONAL EMAIL", "PHONE", "BIRTHDAY"],
    ["EXECUTIVE BOARD", "", "", "", "", ""],
    ["Commissioner", "John Doe", "john@bars.com", "", "", ""],
    ["Vice Commissioner", "Jane Smith", "jane@bars.com", "", "", ""],
    ["", "", "", "", "", ""],
    ["BOWLING LEADERSHIP TEAM", "", "", "", "", ""],
    ["Director of Bowling, Sunday", "Bob Wilson", "bob@bars.com", "", "", ""],
]

SAMPLE_CSV_WITH_VACANT = [
    ["POSITION", "NAME", "BARS EMAIL", "PERSONAL EMAIL", "PHONE", "BIRTHDAY"],
    ["Commissioner", "John Doe", "john@bars.com", "", "", ""],
    ["Vice Commissioner", "Vacant", "", "", "", ""],
    ["WTNB+ Commissioner", "Vacant", "", "", "", ""],
]

SAMPLE_CSV_DODGEBALL = [
    ["POSITION", "NAME", "BARS EMAIL", "PERSONAL EMAIL", "PHONE", "BIRTHDAY"],
    ["DODGEBALL LEADERSHIP TEAM", "", "", "", "", ""],
    ["Director of Dodgeball, Small Ball (Advanced)", "Alice Jones", "alice@bars.com", "", "", ""],
    ["Operations Manager, Small Ball (Social)", "Bob Smith", "bob@bars.com", "", "", ""],
    ["Director of Player Experience, WTNB+", "Charlie Brown", "charlie@bars.com", "", "", ""],
]


class TestLeadershipCSVParser:
    """Test LeadershipCSVParser service."""
    
    def test_parser_initialization(self):
        """Test parser can be initialized."""
        parser = LeadershipCSVParser()
        assert parser is not None
    
    def test_find_header_row(self):
        """Test finding the header row containing POSITION and NAME."""
        parser = LeadershipCSVParser()
        
        header_idx = parser.find_header_row(SAMPLE_CSV_SIMPLE)
        assert header_idx == 0
        
        # CSV with blank rows before header
        csv_with_blanks = [
            ["", "", ""],
            ["Some Title", "", ""],
            ["POSITION", "NAME", "BARS EMAIL", "PERSONAL EMAIL", "PHONE", "BIRTHDAY"],
        ]
        header_idx = parser.find_header_row(csv_with_blanks)
        assert header_idx == 2
    
    def test_find_header_columns(self):
        """Test finding Position and BARS EMAIL column indices."""
        parser = LeadershipCSVParser()
        
        header_row = SAMPLE_CSV_SIMPLE[0]
        position_col, email_col = parser.find_header_columns(header_row)
        
        assert position_col == 0  # POSITION is first column
        assert email_col == 2  # BARS EMAIL is third column
    
    def test_detect_section(self):
        """Test section detection from CSV rows."""
        parser = LeadershipCSVParser()
        
        # Should detect "EXECUTIVE BOARD"
        assert parser.detect_section("EXECUTIVE BOARD", "") == "executive_board"
        
        # Should detect "BOWLING LEADERSHIP TEAM"
        assert parser.detect_section("BOWLING LEADERSHIP TEAM", "") == "bowling"
        
        # Should detect "DODGEBALL LEADERSHIP TEAM"
        assert parser.detect_section("DODGEBALL LEADERSHIP TEAM", "") == "dodgeball"
        
        # Should detect "KICKBALL LEADERSHIP TEAM"
        assert parser.detect_section("KICKBALL LEADERSHIP TEAM", "") == "kickball"
        
        # Should detect "PICKLEBALL LEADERSHIP TEAM"
        assert parser.detect_section("PICKLEBALL LEADERSHIP TEAM", "") == "pickleball"
        
        # Should detect "CROSS–SPORT LEADERSHIP TEAM" (with dash variations)
        assert parser.detect_section("CROSS-SPORT LEADERSHIP TEAM", "") == "cross_sport"
        assert parser.detect_section("CROSS–SPORT LEADERSHIP TEAM", "") == "cross_sport"
        
        # Should detect "COMMITTEE MEMBERS"
        assert parser.detect_section("COMMITTEE MEMBERS", "") == "committee_members"
        
        # Should return None for non-section rows
        assert parser.detect_section("Commissioner", "John Doe") is None
        assert parser.detect_section("", "John Doe") is None
    
    def test_parse_simple_hierarchy(self):
        """Test parsing simple CSV without sections."""
        parser = LeadershipCSVParser()
        
        hierarchy = parser.parse(SAMPLE_CSV_SIMPLE)
        
        assert isinstance(hierarchy, LeadershipHierarchy)
        # Positions should be in executive_board (default)
        commissioner = hierarchy.get_position("executive_board", "commissioner")
        assert commissioner is not None
        assert commissioner["name"] == "John Doe"
        assert commissioner["bars_email"] == "john@bars.com"
    
    def test_parse_with_sections(self):
        """Test parsing CSV with section headers."""
        parser = LeadershipCSVParser()
        
        hierarchy = parser.parse(SAMPLE_CSV_WITH_SECTIONS)
        
        # Executive board positions
        commissioner = hierarchy.get_position("executive_board", "commissioner")
        assert commissioner is not None
        assert commissioner["name"] == "John Doe"
        
        # Bowling positions
        sunday_director = hierarchy.get_position("bowling", "director", sub_section="sunday")
        assert sunday_director is not None
        assert sunday_director["name"] == "Bob Wilson"
    
    def test_parse_with_vacant_positions(self):
        """Test that vacant positions are tracked separately."""
        parser = LeadershipCSVParser()
        
        hierarchy = parser.parse(SAMPLE_CSV_WITH_VACANT)
        
        # Commissioner should be filled
        commissioner = hierarchy.get_position("executive_board", "commissioner")
        assert commissioner is not None
        assert commissioner["name"] == "John Doe"
        
        # Vacant positions should be in vacant_positions set
        assert "executive_board.vice_commissioner" in hierarchy.vacant_positions
        assert "executive_board.wtnb_commissioner" in hierarchy.vacant_positions
        
        # Vacant positions should NOT be in sections
        vice = hierarchy.get_position("executive_board", "vice_commissioner")
        assert vice is None
    
    def test_fuzzy_match_position(self):
        """Test fuzzy position matching (any order, case-insensitive)."""
        parser = LeadershipCSVParser()
        
        # Pattern: ["director", "bowling", "sunday"]
        patterns = [["director", "bowling", "sunday"]]
        
        # Should match various orders
        assert parser.fuzzy_match("Director of Bowling, Sunday", patterns) is True
        assert parser.fuzzy_match("Sunday Director Bowling", patterns) is True
        assert parser.fuzzy_match("BOWLING SUNDAY DIRECTOR", patterns) is True
        
        # Should not match missing terms
        assert parser.fuzzy_match("Director of Bowling", patterns) is False
        assert parser.fuzzy_match("Sunday Director", patterns) is False
    
    def test_exact_match_position(self):
        """Test exact position matching (case-insensitive, whitespace-stripped)."""
        parser = LeadershipCSVParser()
        
        # Should match exact string (ignoring case/whitespace)
        assert parser.exact_match("Commissioner", "commissioner") is True
        assert parser.exact_match("  COMMISSIONER  ", "commissioner") is True
        assert parser.exact_match("commissioner", "Commissioner") is True
        
        # Should not match with extra words
        assert parser.exact_match("Vice Commissioner", "commissioner") is False
        assert parser.exact_match("Commissioner of Pickleball", "commissioner") is False
    
    def test_wtnb_priority_matching(self):
        """Test that WTNB positions are matched with priority."""
        parser = LeadershipCSVParser()
        
        hierarchy = parser.parse(SAMPLE_CSV_DODGEBALL)
        
        # WTNB+ position should be matched correctly
        wtnb_player_exp = hierarchy.get_position(
            "dodgeball",
            "wtnb",
            sub_section="player_experience"
        )
        assert wtnb_player_exp is not None
        assert wtnb_player_exp["name"] == "Charlie Brown"
        
        # Non-WTNB positions should not overwrite WTNB positions
        # This tests the WTNB-first priority system
    
    def test_extract_person_data(self):
        """Test extracting person data from a CSV row."""
        parser = LeadershipCSVParser()
        
        row = ["Commissioner", "John Doe", "john@bars.com", "john@gmail.com", "555-0100", "01/15"]
        
        person = parser.extract_person_data(
            row,
            position="Commissioner",
            name_col=1,
            bars_email_col=2,
            personal_email_col=3,
            phone_col=4,
            birthday_col=5
        )
        
        assert isinstance(person, PersonInfo)
        assert person.name == "John Doe"
        assert person.bars_email == "john@bars.com"
        assert person.personal_email == "john@gmail.com"
        assert person.phone == "555-0100"
        assert person.birthday == "01/15"
    
    def test_extract_person_data_vacant(self):
        """Test extracting vacant person data stops early."""
        parser = LeadershipCSVParser()
        
        row = ["Vice Commissioner", "Vacant", "", "", "", ""]
        
        person = parser.extract_person_data(
            row,
            position="Vice Commissioner",
            name_col=1,
            bars_email_col=2,
            personal_email_col=3,
            phone_col=4,
            birthday_col=5
        )
        
        assert isinstance(person, PersonInfo)
        assert person.is_vacant() is True
        # Other fields should be empty for vacant positions
        assert person.bars_email == ""
        assert person.personal_email is None
    
    def test_parse_filters_position_header(self):
        """Test that the literal 'POSITION' header is not treated as a position."""
        parser = LeadershipCSVParser()
        
        csv_data = [
            ["POSITION", "NAME", "BARS EMAIL", "PERSONAL EMAIL", "PHONE", "BIRTHDAY"],
            ["Commissioner", "John Doe", "john@bars.com", "", "", ""],
        ]
        
        hierarchy = parser.parse(csv_data)
        
        # Should have commissioner but not "position" as a position
        commissioner = hierarchy.get_position("executive_board", "commissioner")
        assert commissioner is not None
        
        # Should not have "position" as a key anywhere
        hierarchy_dict = hierarchy.to_dict()
        
        def check_no_position_key(obj: Any, path: str = "") -> None:
            """Recursively check no 'position' key exists as a position."""
            if isinstance(obj, dict):
                for key, value in obj.items():
                    # Check that 'position' is not a role key
                    if key.lower() == "position" and "name" in value:
                        raise AssertionError(f"Found 'position' as a role at {path}.{key}")
                    check_no_position_key(value, f"{path}.{key}")
        
        check_no_position_key(hierarchy_dict)
    
    def test_parse_handles_unicode_control_chars(self):
        """Test that Unicode control characters are cleaned from CSV data."""
        parser = LeadershipCSVParser()
        
        # CSV with U+202C (POP DIRECTIONAL FORMATTING) in phone
        csv_data = [
            ["POSITION", "NAME", "BARS EMAIL", "PERSONAL EMAIL", "PHONE", "BIRTHDAY"],
            ["Commissioner", "John Doe", "john@bars.com", "", "555-0100\u202c", ""],
        ]
        
        hierarchy = parser.parse(csv_data)
        commissioner = hierarchy.get_position("executive_board", "commissioner")
        
        # Phone should have control character removed
        assert commissioner is not None
        assert "\u202c" not in commissioner["phone"]
        assert commissioner["phone"] == "555-0100"
    
    def test_parse_committee_members(self):
        """Test parsing committee members (no director/ops manager)."""
        parser = LeadershipCSVParser()
        
        csv_data = [
            ["POSITION", "NAME", "BARS EMAIL", "PERSONAL EMAIL", "PHONE", "BIRTHDAY"],
            ["COMMITTEE MEMBERS", "", "", "", "", ""],
            ["Marketing Volunteer", "Alice Smith", "alice@bars.com", "", "", ""],
            ["Social Media Coordinator", "Bob Jones", "bob@bars.com", "", "", ""],
        ]
        
        hierarchy = parser.parse(csv_data)
        
        # Committee members should be a list
        committee = hierarchy.sections.get("committee_members")
        assert isinstance(committee, list)
        assert len(committee) >= 2
        
        # Should have position_key in snake_case
        member_names = [m["name"] for m in committee]
        assert "Alice Smith" in member_names
        assert "Bob Jones" in member_names
        
        # Check for snake_case position_key
        for member in committee:
            if member["name"] == "Alice Smith":
                assert "position_key" in member
                assert member["position_key"] == "marketing_volunteer"


class TestCSVParserEdgeCases:
    """Test edge cases for CSV parser."""
    
    def test_empty_csv(self):
        """Test parsing empty CSV."""
        parser = LeadershipCSVParser()
        
        with pytest.raises(ValueError, match="CSV data is empty"):
            parser.parse([])
    
    def test_csv_no_header(self):
        """Test CSV with no valid header row."""
        parser = LeadershipCSVParser()
        
        csv_data = [
            ["Some random data", "More data"],
            ["No header here", "Nope"],
        ]
        
        with pytest.raises(ValueError, match="Could not find header row"):
            parser.parse(csv_data)
    
    def test_csv_no_position_column(self):
        """Test CSV missing Position column."""
        parser = LeadershipCSVParser()
        
        csv_data = [
            ["NAME", "BARS EMAIL"],  # No POSITION column
            ["John Doe", "john@bars.com"],
        ]
        
        with pytest.raises(ValueError, match="Could not find required columns"):
            parser.parse(csv_data)
    
    def test_csv_no_email_column(self):
        """Test CSV missing email column."""
        parser = LeadershipCSVParser()
        
        csv_data = [
            ["POSITION", "NAME"],  # No email column
            ["Commissioner", "John Doe"],
        ]
        
        with pytest.raises(ValueError, match="Could not find required columns"):
            parser.parse(csv_data)

