import pytest
from pydantic import ValidationError

from modules.leadership.domain.csv_patterns import (
    ExactMatchPattern,
    KeywordMatchPattern,
    PositionPattern,
    SectionPatterns,
    CSVPatternRegistry,
)


class TestExactMatchPattern:
    """Test exact match pattern validation and matching."""
    
    def test_exact_match_creation(self):
        pattern = ExactMatchPattern(value="Commissioner")
        assert pattern.match_type == "exact"
        assert pattern.value == "Commissioner"
    
    def test_exact_match_requires_value(self):
        with pytest.raises(ValidationError):
            ExactMatchPattern(value="")


class TestKeywordMatchPattern:
    """Test keyword-based pattern validation and matching."""
    
    def test_keyword_pattern_creation(self):
        pattern = KeywordMatchPattern(required=["sunday", "director"])
        assert pattern.match_type == "keywords"
        assert pattern.required == ["sunday", "director"]
        assert pattern.alternatives == []
    
    def test_keyword_pattern_with_alternatives(self):
        pattern = KeywordMatchPattern(
            required=["commissioner"],
            alternatives=[
                ["diversity", "commissioner"],
                ["dei", "commissioner"]
            ]
        )
        assert pattern.required == ["commissioner"]
        assert len(pattern.alternatives) == 2
    
    def test_keyword_pattern_normalizes_keywords(self):
        pattern = KeywordMatchPattern(required=["  SUNDAY  ", "Director  "])
        assert pattern.required == ["sunday", "director"]
    
    def test_keyword_pattern_filters_empty_alternatives(self):
        pattern = KeywordMatchPattern(
            required=["test"],
            alternatives=[
                ["valid", "group"],
                [],
                ["", "  "],
                ["another", "valid"]
            ]
        )
        assert len(pattern.alternatives) == 2
        assert pattern.alternatives[0] == ["valid", "group"]
        assert pattern.alternatives[1] == ["another", "valid"]
    
    def test_keyword_pattern_requires_non_empty_required(self):
        with pytest.raises(ValidationError):
            KeywordMatchPattern(required=[])
        
        with pytest.raises(ValidationError):
            KeywordMatchPattern(required=["", "  "])


class TestPositionPattern:
    """Test position pattern matching logic."""
    
    @pytest.mark.parametrize("position_text,expected", [
        ("Commissioner", True),
        ("commissioner", True),
        ("  COMMISSIONER  ", True),
        ("Vice Commissioner", False),
        ("", False),
    ])
    def test_exact_match_patterns(self, position_text, expected):
        pattern = PositionPattern(
            role_key="commissioner",
            pattern=ExactMatchPattern(value="commissioner")
        )
        assert pattern.matches(position_text) == expected
    
    @pytest.mark.parametrize("position_text,expected", [
        ("Director of Bowling, Sunday", True),
        ("Sunday Bowling Director", True),
        ("BOWLING SUNDAY DIRECTOR", True),
        ("Director of Bowling", False),
        ("Sunday Director", False),
        ("", False),
    ])
    def test_keyword_match_patterns(self, position_text, expected):
        pattern = PositionPattern(
            role_key="bowling.sunday.director",
            pattern=KeywordMatchPattern(required=["bowling", "sunday", "director"])
        )
        assert pattern.matches(position_text) == expected
    
    @pytest.mark.parametrize("position_text,expected", [
        ("Diversity and Inclusion Commissioner", True),
        ("DEI Commissioner", True),
        ("Commissioner of Diversity", True),
        ("Commissioner of DEI", True),
        ("Diversity Coordinator", False),
        ("DEI Lead", False),
    ])
    def test_keyword_match_with_alternatives(self, position_text, expected):
        pattern = PositionPattern(
            role_key="dei_commissioner",
            pattern=KeywordMatchPattern(
                required=["commissioner"],
                alternatives=[
                    ["diversity", "commissioner"],
                    ["dei", "commissioner"]
                ]
            )
        )
        assert pattern.matches(position_text) == expected
    
    def test_position_pattern_requires_role_key(self):
        with pytest.raises(ValidationError):
            PositionPattern(
                role_key="",
                pattern=ExactMatchPattern(value="test")
            )


class TestSectionPatterns:
    """Test section pattern collections."""
    
    def test_section_creation(self):
        section = SectionPatterns(
            section_name="executive_board",
            patterns=[
                PositionPattern(
                    role_key="commissioner",
                    pattern=ExactMatchPattern(value="commissioner")
                ),
                PositionPattern(
                    role_key="vice_commissioner",
                    pattern=KeywordMatchPattern(required=["vice", "commissioner"])
                ),
            ]
        )
        assert section.section_name == "executive_board"
        assert len(section.patterns) == 2
    
    def test_find_matching_role_returns_first_match(self):
        section = SectionPatterns(
            section_name="test",
            patterns=[
                PositionPattern(
                    role_key="commissioner",
                    pattern=ExactMatchPattern(value="commissioner")
                ),
                PositionPattern(
                    role_key="vice_commissioner",
                    pattern=KeywordMatchPattern(required=["vice", "commissioner"])
                ),
            ]
        )
        assert section.find_matching_role("Commissioner") == "commissioner"
        assert section.find_matching_role("Vice Commissioner") == "vice_commissioner"
        assert section.find_matching_role("Unknown Position") is None
    
    def test_section_pattern_order_matters(self):
        section = SectionPatterns(
            section_name="test",
            patterns=[
                PositionPattern(
                    role_key="specific_role",
                    pattern=KeywordMatchPattern(required=["sunday", "bowling", "director"])
                ),
                PositionPattern(
                    role_key="general_role",
                    pattern=KeywordMatchPattern(required=["bowling", "director"])
                ),
            ]
        )
        assert section.find_matching_role("Sunday Bowling Director") == "specific_role"
        assert section.find_matching_role("Bowling Director") == "general_role"


class TestCSVPatternRegistry:
    """Test the full pattern registry."""
    
    def test_registry_creation(self):
        registry = CSVPatternRegistry(sections={
            "test_section": SectionPatterns(
                section_name="test_section",
                patterns=[
                    PositionPattern(
                        role_key="test_role",
                        pattern=ExactMatchPattern(value="test")
                    )
                ]
            )
        })
        assert "test_section" in registry.sections
    
    def test_get_section(self):
        registry = CSVPatternRegistry(sections={
            "executive_board": SectionPatterns(
                section_name="executive_board",
                patterns=[]
            )
        })
        section = registry.get_section("executive_board")
        assert section is not None
        assert section.section_name == "executive_board"
        
        assert registry.get_section("nonexistent") is None
    
    def test_find_role_in_section(self):
        registry = CSVPatternRegistry(sections={
            "test": SectionPatterns(
                section_name="test",
                patterns=[
                    PositionPattern(
                        role_key="commissioner",
                        pattern=ExactMatchPattern(value="commissioner")
                    )
                ]
            )
        })
        assert registry.find_role_in_section("test", "Commissioner") == "commissioner"
        assert registry.find_role_in_section("test", "Unknown") is None
        assert registry.find_role_in_section("nonexistent_section", "Commissioner") is None
    
    def test_create_default_registry(self):
        registry = CSVPatternRegistry.create_default()
        
        assert "executive_board" in registry.sections
        assert "bowling" in registry.sections
        assert "dodgeball" in registry.sections
        assert "kickball" in registry.sections
        assert "pickleball" in registry.sections
        assert "cross_sport" in registry.sections
    
    @pytest.mark.parametrize("section,position,expected_role", [
        ("executive_board", "Commissioner", "commissioner"),
        ("executive_board", "Vice Commissioner", "vice_commissioner"),
        ("executive_board", "WTNB Commissioner", "wtnb_commissioner"),
        ("executive_board", "Secretary", "secretary"),
        ("executive_board", "Treasurer", "treasurer"),
        ("executive_board", "Operations Commissioner", "operations_commissioner"),
        ("executive_board", "Diversity Commissioner", "dei_commissioner"),
        ("executive_board", "DEI Commissioner", "dei_commissioner"),
        ("executive_board", "Bowling Commissioner", "bowling_commissioner"),
    ])
    def test_default_registry_executive_board_patterns(self, section, position, expected_role):
        registry = CSVPatternRegistry.create_default()
        assert registry.find_role_in_section(section, position) == expected_role
    
    @pytest.mark.parametrize("section,position,expected_role", [
        ("bowling", "Sunday Director", "sunday.director"),
        ("bowling", "Director of Bowling, Sunday", "sunday.director"),
        ("bowling", "Sunday Operations Manager", "sunday.ops_manager"),
        ("bowling", "Monday Open Director", "monday_open.director"),
        ("bowling", "Monday WTNB Director", "monday_wtnb.director"),
        ("bowling", "Player Experience, Open", "player_experience.open"),
        ("bowling", "Player Experience, WTNB", "player_experience.wtnb"),
    ])
    def test_default_registry_bowling_patterns(self, section, position, expected_role):
        registry = CSVPatternRegistry.create_default()
        assert registry.find_role_in_section(section, position) == expected_role
    
    @pytest.mark.parametrize("section,position,expected_role", [
        ("cross_sport", "Communications", "communications"),
        ("cross_sport", "Events, Open", "events.open"),
        ("cross_sport", "Events, WTNB", "events.wtnb"),
        ("cross_sport", "Diversity, Open", "dei.open"),
        ("cross_sport", "DEI, Open", "dei.open"),
        ("cross_sport", "Diversity, WTNB", "dei.wtnb"),
        ("cross_sport", "DEI, WTNB", "dei.wtnb"),
        ("cross_sport", "Marketing", "marketing"),
        ("cross_sport", "Philanthropy", "philanthropy"),
        ("cross_sport", "Social Media, Open", "social_media.open"),
        ("cross_sport", "Social Media, WTNB", "social_media.wtnb"),
        ("cross_sport", "Technology", "technology"),
        ("cross_sport", "Permits and Equipment", "permits_equipment"),
    ])
    def test_default_registry_cross_sport_patterns(self, section, position, expected_role):
        registry = CSVPatternRegistry.create_default()
        assert registry.find_role_in_section(section, position) == expected_role
    
    def test_default_registry_case_insensitive(self):
        registry = CSVPatternRegistry.create_default()
        
        assert registry.find_role_in_section("executive_board", "commissioner") == "commissioner"
        assert registry.find_role_in_section("executive_board", "COMMISSIONER") == "commissioner"
        assert registry.find_role_in_section("executive_board", "Commissioner") == "commissioner"
    
    def test_default_registry_handles_unknown_positions(self):
        registry = CSVPatternRegistry.create_default()
        
        assert registry.find_role_in_section("executive_board", "Unknown Position") is None
        assert registry.find_role_in_section("bowling", "Invalid Role") is None

