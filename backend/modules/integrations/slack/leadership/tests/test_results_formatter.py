import pytest
from typing import Dict, List, Any, Optional
from modules.leadership.domain.models import PersonInfo, Position, LeadershipHierarchy
from modules.integrations.slack.leadership.results_formatter import (
    LeadershipResultsFormatter,
    AnalysisResult,
    PositionStatus
)
from slack_sdk.models.blocks import HeaderBlock, SectionBlock, ContextBlock


# ============================================================================
# FACTORY FUNCTIONS
# ============================================================================

def create_person(
    name: str = "John Doe",
    bars_email: str = "john@bars.com",
    personal_email: Optional[str] = None,
    phone: Optional[str] = None,
    birthday: Optional[str] = None,
    slack_user_id: Optional[str] = None,
    csv_row: Optional[int] = None,
    csv_columns: Optional[Dict[str, int]] = None
) -> PersonInfo:
    """
    Factory function to create PersonInfo with optional fields.
    
    Args:
        name: Person's name (use "Vacant" for vacant positions)
        bars_email: Primary BARS email
        personal_email: Personal email
        phone: Phone number
        birthday: Birthday (MM/DD format)
        slack_user_id: Slack user ID
        csv_row: CSV row number for error reporting
        csv_columns: CSV column mapping for error reporting
    
    Returns:
        PersonInfo instance with extra fields if provided
    """
    kwargs = {
        "name": name,
        "bars_email": bars_email,
        "personal_email": personal_email,
        "phone": phone,
        "birthday": birthday,
        "slack_user_id": slack_user_id
    }
    
    if csv_row is not None:
        kwargs["_csv_row"] = csv_row  # type: ignore
    if csv_columns is not None:
        kwargs["_csv_columns"] = csv_columns  # type: ignore
    
    return PersonInfo(**kwargs)


def create_hierarchy_with_position(
    section: str,
    role: str,
    person: PersonInfo,
    sub_section: Optional[str] = None,
    team: Optional[str] = None
) -> LeadershipHierarchy:
    """
    Factory function to create hierarchy with a single position.
    
    Args:
        section: Section name
        role: Role name
        person: PersonInfo object
        sub_section: Optional subsection
        team: Optional team
    
    Returns:
        LeadershipHierarchy with one position added
    """
    hierarchy = LeadershipHierarchy()
    hierarchy.add_position(section, role, person, sub_section, team)
    return hierarchy


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def formatter():
    """Create a LeadershipResultsFormatter instance."""
    return LeadershipResultsFormatter()


@pytest.fixture
def complete_person():
    """Person with all fields filled."""
    return create_person(
        name="Complete Person",
        bars_email="complete@bars.com",
        personal_email="complete@personal.com",
        phone="555-0001",
        birthday="01/01",
        slack_user_id="U001"
    )


@pytest.fixture
def csv_columns():
    """Standard CSV column mapping."""
    return {"name": 0, "bars_email": 1, "personal_email": 2, "phone": 3, "birthday": 4}


# ============================================================================
# TESTS
# ============================================================================
# Note: CSV utilities (column_index_to_letter, cell_reference) are tested
# separately in modules/integrations/slack/utils/tests/test_csv_utils.py.
# Integration with CSV metadata is tested below.

class TestAnalyzeCompleteness:
    """Test completeness analysis for various position states."""
    
    @pytest.mark.parametrize("person_factory,lookup_results,expected_category", [
        # Complete position with all fields
        (
            lambda: create_person(
                name="Complete", bars_email="complete@bars.com",
                personal_email="p@email.com", phone="555-1234", birthday="01/01", slack_user_id="U123"
            ),
            {"complete@bars.com": "U123"},
            "successes"
        ),
        # Vacant position
        (
            lambda: create_person(name="Vacant", bars_email=""),
            {},
            "vacant_positions"
        ),
        # Missing birthday (warning)
        (
            lambda: create_person(
                name="Partial", bars_email="partial@bars.com",
                personal_email="p@email.com", phone="555-5678", slack_user_id="U456"
            ),
            {"partial@bars.com": "U456"},
            "warnings"
        ),
        # Missing Slack ID (failure)
        (
            lambda: create_person(
                name="No Slack", bars_email="noslack@bars.com",
                personal_email="n@email.com", phone="555-9999", birthday="02/14"
            ),
            {},
            "failures"
        ),
    ])
    def test_position_categorization(
        self, formatter, person_factory, lookup_results, expected_category
    ):
        """Test that positions are correctly categorized based on completeness."""
        person = person_factory()
        hierarchy = create_hierarchy_with_position("executive_board", "President", person)
        
        analysis = formatter.analyze_completeness(hierarchy, lookup_results)
        
        category_counts = {
            "successes": len(analysis.successes),
            "warnings": len(analysis.warnings),
            "failures": len(analysis.failures),
            "vacant_positions": len(analysis.vacant_positions)
        }
        
        assert category_counts[expected_category] == 1
        assert sum(category_counts.values()) == 1


class TestCommitteeMemberRules:
    """Test different completeness rules for committee members."""
    
    @pytest.mark.parametrize("person_kwargs,lookup_results,expected_category", [
        # Minimal fields (name + email) should succeed
        (
            {"name": "Member1", "bars_email": "m1@bars.com"},
            {},
            "successes"
        ),
        # All fields present should succeed
        (
            {
                "name": "Member2", "bars_email": "m2@bars.com",
                "phone": "555-1234", "birthday": "01/15"
            },
            {},
            "successes"
        ),
        # Missing name should fail
        (
            {"name": "", "bars_email": "m3@bars.com"},
            {},
            "failures"
        ),
        # Missing email should fail
        (
            {"name": "Member4", "bars_email": ""},
            {},
            "failures"
        ),
    ])
    def test_committee_member_completeness(
        self, formatter, person_kwargs, lookup_results, expected_category
    ):
        """Committee members have different rules than leadership positions."""
        person = create_person(**person_kwargs)
        hierarchy = create_hierarchy_with_position("committee_members", "Committee Member", person)
        
        analysis = formatter.analyze_completeness(hierarchy, lookup_results)
        
        category_results = {
            "successes": analysis.successes,
            "warnings": analysis.warnings,
            "failures": analysis.failures,
            "vacant_positions": analysis.vacant_positions
        }
        
        assert len(category_results[expected_category]) == 1


class TestCSVCellReferences:
    """Test CSV cell reference tracking for error reporting."""
    
    def test_missing_fields_include_csv_cells(self, formatter, csv_columns):
        """Missing fields should include CSV cell references when metadata provided."""
        person = create_person(
            name="Alice Brown",
            bars_email="alice@bars.com",
            csv_row=5,
            csv_columns=csv_columns
        )
        hierarchy = create_hierarchy_with_position("executive_board", "VP", person)
        
        analysis = formatter.analyze_completeness(hierarchy, {})
        
        assert len(analysis.failures) == 1
        failure = analysis.failures[0]
        assert len(failure.fields_missing_details) > 0
        
        slack_id_detail = next(
            (d for d in failure.fields_missing_details if d.field == "slack_user_id"),
            None
        )
        assert slack_id_detail is not None
        assert slack_id_detail.cell == "B5"
    
    def test_no_csv_metadata_no_cell_references(self, formatter):
        """Without CSV metadata, no cell references should be included."""
        person = create_person(name="Bob", bars_email="bob@bars.com")
        hierarchy = create_hierarchy_with_position("executive_board", "Secretary", person)
        
        analysis = formatter.analyze_completeness(hierarchy, {})
        
        assert len(analysis.failures) == 1
        failure = analysis.failures[0]
        assert len(failure.fields_missing_details) == 0


class TestSlackBlockFormatting:
    """Test Slack Block Kit message formatting."""
    
    def test_format_returns_typed_blocks(self, formatter, complete_person):
        """Format should return typed Slack Block objects."""
        hierarchy = create_hierarchy_with_position("executive_board", "President", complete_person)
        lookup_results = {"complete@bars.com": "U001"}
        
        analysis = formatter.analyze_completeness(hierarchy, lookup_results)
        blocks = formatter.format_results_for_slack(analysis)
        
        assert len(blocks) >= 3
        assert blocks[0].type == "header"
        assert blocks[1].type == "section"
    
    @pytest.mark.parametrize("num_successes,num_warnings,num_failures,num_vacant", [
        (1, 0, 0, 0),
        (0, 1, 0, 0),
        (0, 0, 1, 0),
        (0, 0, 0, 1),
        (1, 1, 1, 1),
    ])
    def test_summary_block_counts(
        self, formatter, num_successes, num_warnings, num_failures, num_vacant
    ):
        """Summary block should contain correct counts."""
        hierarchy = LeadershipHierarchy()
        
        # Add positions for each category
        for i in range(num_successes):
            person = create_person(
                name=f"Success{i}", bars_email=f"s{i}@bars.com",
                personal_email=f"s{i}@p.com", phone=f"555-000{i}",
                birthday="01/01", slack_user_id=f"U{i}"
            )
            hierarchy.add_position("executive_board", f"Role{i}", person)
        
        for i in range(num_warnings):
            person = create_person(
                name=f"Warning{i}", bars_email=f"w{i}@bars.com",
                personal_email=f"w{i}@p.com", phone=f"555-100{i}", slack_user_id=f"UW{i}"
            )
            hierarchy.add_position("executive_board", f"RoleW{i}", person)
        
        for i in range(num_failures):
            person = create_person(name=f"Failure{i}", bars_email=f"f{i}@bars.com")
            hierarchy.add_position("executive_board", f"RoleF{i}", person)
        
        for i in range(num_vacant):
            person = create_person(name="Vacant", bars_email="")
            hierarchy.add_position("executive_board", f"RoleV{i}", person)
        
        lookup_results = {
            f"s{i}@bars.com": f"U{i}" for i in range(num_successes)
        }
        lookup_results.update({
            f"w{i}@bars.com": f"UW{i}" for i in range(num_warnings)
        })
        
        analysis = formatter.analyze_completeness(hierarchy, lookup_results)
        blocks = formatter.format_results_for_slack(analysis)
        
        summary_block = blocks[1]
        summary_text = summary_block.text.text
        
        assert f"*{num_successes}* complete" in summary_text
        assert f"*{num_warnings}* partial" in summary_text
        assert f"*{num_failures}* failed" in summary_text
        assert f"*{num_vacant}* vacant" in summary_text
    
    def test_warnings_section_includes_details(self, formatter, csv_columns):
        """Warning sections should include person name and missing field details."""
        person = create_person(
            name="Bob Smith", bars_email="bob@bars.com",
            personal_email="bob@p.com", phone="555-5678", slack_user_id="U789",
            csv_row=6, csv_columns=csv_columns
        )
        hierarchy = create_hierarchy_with_position("executive_board", "Treasurer", person)
        
        lookup_results = {"bob@bars.com": "U789"}
        analysis = formatter.analyze_completeness(hierarchy, lookup_results)
        blocks = formatter.format_results_for_slack(analysis)
        
        warning_section = next(
            (b for b in blocks if b.type == "section" and "⚠️" in b.text.text and "Bob Smith" in b.text.text),
            None
        )
        assert warning_section is not None
        assert "birthday" in warning_section.text.text
    
    def test_failures_section_includes_csv_references(self, formatter, csv_columns):
        """Failure sections should include CSV cell references."""
        person = create_person(
            name="Carol White", bars_email="carol@bars.com",
            csv_row=7, csv_columns=csv_columns
        )
        hierarchy = create_hierarchy_with_position("executive_board", "Secretary", person)
        
        analysis = formatter.analyze_completeness(hierarchy, {})
        blocks = formatter.format_results_for_slack(analysis)
        
        failure_section = next(
            (b for b in blocks if b.type == "section" and "❌" in b.text.text and "Carol White" in b.text.text),
            None
        )
        assert failure_section is not None
        assert "B7" in failure_section.text.text


class TestMultiplePositions:
    """Test analysis with multiple positions in different states."""
    
    def test_mixed_status_positions(self, formatter):
        """Multiple positions with different statuses should be categorized correctly."""
        hierarchy = LeadershipHierarchy()
        
        # Success
        hierarchy.add_position(
            "executive_board", "President",
            create_person(
                name="Complete", bars_email="complete@bars.com",
                personal_email="c@p.com", phone="555-0001", birthday="01/01", slack_user_id="U001"
            )
        )
        
        # Warning
        hierarchy.add_position(
            "executive_board", "VP",
            create_person(
                name="Partial", bars_email="partial@bars.com",
                personal_email="p@p.com", phone="555-0002", slack_user_id="U002"
            )
        )
        
        # Failure
        hierarchy.add_position(
            "executive_board", "Treasurer",
            create_person(name="Failed", bars_email="failed@bars.com")
        )
        
        # Vacant
        hierarchy.add_position(
            "executive_board", "Secretary",
            create_person(name="Vacant", bars_email="")
        )
        
        lookup_results = {
            "complete@bars.com": "U001",
            "partial@bars.com": "U002"
        }
        
        analysis = formatter.analyze_completeness(hierarchy, lookup_results)
        
        assert len(analysis.successes) == 1
        assert len(analysis.warnings) == 1
        assert len(analysis.failures) == 1
        assert len(analysis.vacant_positions) == 1
