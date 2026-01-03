"""
Test CSV Parser Service using pytest parameterization.

Tests: LeadershipCSVParser - Extracts leadership hierarchy from CSV data
"""
import pytest
from typing import List, Any
from modules.leadership.services.csv_parser import LeadershipCSVParser
from modules.leadership.domain.models import LeadershipHierarchy, PersonInfo


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
    
    @pytest.mark.parametrize("csv_data,expected_header_idx", [
        (SAMPLE_CSV_SIMPLE, 0),
        ([["", "", ""], ["Some Title", "", ""], ["POSITION", "NAME", "BARS EMAIL", "PERSONAL EMAIL", "PHONE", "BIRTHDAY"]], 2),
    ])
    def test_find_header_row(self, csv_data, expected_header_idx):
        """Test finding header row in various CSV structures."""
        parser = LeadershipCSVParser()
        header_idx = parser.find_header_row(csv_data)
        assert header_idx == expected_header_idx
    
    def test_find_header_columns(self):
        """Test finding Position and BARS EMAIL column indices."""
        parser = LeadershipCSVParser()
        header_row = SAMPLE_CSV_SIMPLE[0]
        position_col, email_col = parser.find_header_columns(header_row)
        
        assert position_col == 0
        assert email_col == 2
    
    @pytest.mark.parametrize("position_text,name_text,expected_section", [
        ("EXECUTIVE BOARD", "", "executive_board"),
        ("BOWLING LEADERSHIP TEAM", "", "bowling"),
        ("DODGEBALL LEADERSHIP TEAM", "", "dodgeball"),
        ("KICKBALL LEADERSHIP TEAM", "", "kickball"),
        ("PICKLEBALL LEADERSHIP TEAM", "", "pickleball"),
        ("CROSS-SPORT LEADERSHIP TEAM", "", "cross_sport"),
        ("CROSS–SPORT LEADERSHIP TEAM", "", "cross_sport"),
        ("COMMITTEE MEMBERS", "", "committee_members"),
        ("Commissioner", "John Doe", None),
        ("", "John Doe", None),
    ])
    def test_detect_section(self, position_text, name_text, expected_section):
        """Test section detection from CSV rows."""
        parser = LeadershipCSVParser()
        assert parser.detect_section(position_text, name_text) == expected_section
    
    @pytest.mark.parametrize("csv_data,section,role,sub_section,expected_name", [
        (SAMPLE_CSV_SIMPLE, "executive_board", "commissioner", None, "John Doe"),
        (SAMPLE_CSV_WITH_SECTIONS, "executive_board", "commissioner", None, "John Doe"),
        (SAMPLE_CSV_WITH_SECTIONS, "bowling", "director", "sunday", "Bob Wilson"),
    ])
    def test_parse_hierarchy_structure(self, csv_data, section, role, sub_section, expected_name):
        """Test parsing various CSV structures into hierarchy."""
        parser = LeadershipCSVParser()
        hierarchy = parser.parse(csv_data)
        
        position = hierarchy.get_position(section, role, sub_section=sub_section)
        assert position is not None
        assert position["name"] == expected_name
    
    def test_parse_vacant_positions(self):
        """Test that vacant positions are tracked separately."""
        parser = LeadershipCSVParser()
        hierarchy = parser.parse(SAMPLE_CSV_WITH_VACANT)
        
        commissioner = hierarchy.get_position("executive_board", "commissioner")
        assert commissioner is not None
        assert commissioner["name"] == "John Doe"
        
        assert "executive_board.vice_commissioner" in hierarchy.vacant_positions
        assert "executive_board.wtnb_commissioner" in hierarchy.vacant_positions
        
        vice = hierarchy.get_position("executive_board", "vice_commissioner")
        assert vice is None
    
    @pytest.mark.parametrize("position,patterns,expected_match", [
        ("Director of Bowling, Sunday", [["director", "bowling", "sunday"]], True),
        ("Sunday Director Bowling", [["director", "bowling", "sunday"]], True),
        ("BOWLING SUNDAY DIRECTOR", [["director", "bowling", "sunday"]], True),
        ("Director of Bowling", [["director", "bowling", "sunday"]], False),
        ("Sunday Director", [["director", "bowling", "sunday"]], False),
    ])
    def test_fuzzy_match_position(self, position, patterns, expected_match):
        """Test fuzzy position matching (any order, case-insensitive)."""
        parser = LeadershipCSVParser()
        assert parser.fuzzy_match(position, patterns) == expected_match
    
    @pytest.mark.parametrize("position,exact_value,expected_match", [
        ("Commissioner", "commissioner", True),
        ("  COMMISSIONER  ", "commissioner", True),
        ("commissioner", "Commissioner", True),
        ("Vice Commissioner", "commissioner", False),
        ("Commissioner of Pickleball", "commissioner", False),
    ])
    def test_exact_match_position(self, position, exact_value, expected_match):
        """Test exact position matching (case-insensitive, whitespace-stripped)."""
        parser = LeadershipCSVParser()
        assert parser.exact_match(position, exact_value) == expected_match
    
    def test_wtnb_priority_matching(self):
        """Test that WTNB positions are matched with priority."""
        parser = LeadershipCSVParser()
        hierarchy = parser.parse(SAMPLE_CSV_DODGEBALL)
        
        wtnb_player_exp = hierarchy.get_position(
            "dodgeball",
            "wtnb",
            sub_section="player_experience"
        )
        assert wtnb_player_exp is not None
        assert wtnb_player_exp["name"] == "Charlie Brown"
    
    def test_extract_person_data(self):
        """Test extracting person data from CSV row."""
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
        commissioner = hierarchy.get_position("executive_board", "commissioner")
        assert commissioner is not None
        
        hierarchy_dict = hierarchy.to_dict()
        
        def check_no_position_key(obj: Any, path: str = "") -> None:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key.lower() == "position" and isinstance(value, dict) and "name" in value:
                        raise AssertionError(f"Found 'position' as a role at {path}.{key}")
                    check_no_position_key(value, f"{path}.{key}")
        
        check_no_position_key(hierarchy_dict)
    
    def test_parse_handles_unicode_control_chars(self):
        """Test that Unicode control characters are cleaned from CSV data."""
        parser = LeadershipCSVParser()
        csv_data = [
            ["POSITION", "NAME", "BARS EMAIL", "PERSONAL EMAIL", "PHONE", "BIRTHDAY"],
            ["Commissioner", "John Doe", "john@bars.com", "", "555-0100\u202c", ""],
        ]
        
        hierarchy = parser.parse(csv_data)
        commissioner = hierarchy.get_position("executive_board", "commissioner")
        
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
        committee = hierarchy.sections.get("committee_members")
        
        assert isinstance(committee, list)
        assert len(committee) >= 2
        
        member_names = [m["name"] for m in committee]
        assert "Alice Smith" in member_names
        assert "Bob Jones" in member_names
        
        for member in committee:
            if member["name"] == "Alice Smith":
                assert "position_key" in member
                assert member["position_key"] == "marketing_volunteer"


class TestCSVParserEdgeCases:
    """Test edge cases for CSV parser."""
    
    @pytest.mark.parametrize("csv_data,expected_error", [
        ([], "CSV data is empty"),
        ([["Some random data", "More data"], ["No header here", "Nope"]], "Could not find header row"),
        ([["NAME", "BARS EMAIL"]], "Could not find required columns"),
        ([["POSITION", "NAME"]], "Could not find required columns"),
    ])
    def test_invalid_csv_structures(self, csv_data, expected_error):
        """Test that invalid CSV structures raise appropriate errors."""
        parser = LeadershipCSVParser()
        
        with pytest.raises(ValueError, match=expected_error):
            parser.parse(csv_data)
