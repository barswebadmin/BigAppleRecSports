"""
Test leadership hierarchy building logic.
Tests CSV parsing and hierarchy construction without requiring Slack API calls.
"""
import json
import os
import pytest
import sys

# Add backend to path for imports
backend_path = os.path.join(os.path.dirname(__file__), '../../../..')
sys.path.insert(0, backend_path)

from shared.check_dict_equivalence import check_dict_equivalence
from modules.integrations.slack.leadership.tests.test_helpers import (
    process_csv_to_hierarchy,
    normalize_hierarchy_for_comparison
)


@pytest.fixture
def mock_csv_path():
    """Path to mock CSV file."""
    return os.path.join(os.path.dirname(__file__), 'mock_leadership_contact_sheet.csv')


@pytest.fixture
def expected_hierarchy_path():
    """Path to expected hierarchy JSON."""
    return os.path.join(os.path.dirname(__file__), 'expected_hierarchy.json')


@pytest.fixture
def expected_hierarchy(expected_hierarchy_path):
    """Load expected hierarchy from JSON."""
    with open(expected_hierarchy_path, 'r') as f:
        return json.load(f)


def test_csv_processing_builds_correct_hierarchy(mock_csv_path, expected_hierarchy):
    """
    Test that processing the mock CSV produces the expected hierarchy structure.
    This validates that all position patterns are matching correctly.
    """
    # Process the mock CSV
    result = process_csv_to_hierarchy(mock_csv_path)
    actual_hierarchy = result['hierarchy']
    
    # Normalize both hierarchies (remove slack_user_id for comparison)
    actual_normalized = normalize_hierarchy_for_comparison(actual_hierarchy)
    expected_normalized = normalize_hierarchy_for_comparison(expected_hierarchy)
    
    # Compare hierarchies
    differences = check_dict_equivalence(expected_normalized, actual_normalized)
    
    # Assert no differences
    if differences:
        print("\n❌ Hierarchy mismatch:")
        for diff in differences:
            print(f"  • {diff}")
        pytest.fail(f"Found {len(differences)} difference(s) between expected and actual hierarchy")
    
    print("✅ Hierarchy matches expected output")


def test_all_sections_present(mock_csv_path):
    """Test that all expected sections are present in the hierarchy."""
    result = process_csv_to_hierarchy(mock_csv_path)
    hierarchy = result['hierarchy']
    
    expected_sections = [
        'executive_board',
        'cross_sport',
        'bowling',
        'dodgeball',
        'kickball',
        'pickleball',
        'committee_members'
    ]
    
    for section in expected_sections:
        assert section in hierarchy, f"Missing section: {section}"
    
    print(f"✅ All {len(expected_sections)} sections present")


def test_vacant_positions_identified(mock_csv_path):
    """Test that vacant positions are correctly identified."""
    result = process_csv_to_hierarchy(mock_csv_path)
    hierarchy = result['hierarchy']
    
    # Count vacant positions
    vacant_count = 0
    
    def count_vacant(obj):
        nonlocal vacant_count
        if isinstance(obj, dict):
            if obj.get('name', '').lower() == 'vacant':
                vacant_count += 1
            for value in obj.values():
                count_vacant(value)
        elif isinstance(obj, list):
            for item in obj:
                count_vacant(item)
    
    count_vacant(hierarchy)
    
    # Based on mock CSV: 5 vacant positions
    # - bowling.monday_open.ops_manager
    # - bowling.monday_wtnb.ops_manager
    # - dodgeball.player_experience.open
    # - kickball.monday.ops_manager
    # - pickleball.ladder.ops_manager
    expected_vacant = 5
    
    assert vacant_count == expected_vacant, f"Expected {expected_vacant} vacant positions, found {vacant_count}"
    print(f"✅ Correctly identified {vacant_count} vacant positions")


def test_wtnb_positions_correctly_matched(mock_csv_path):
    """Test that WTNB positions are correctly matched with WTNB-first priority."""
    result = process_csv_to_hierarchy(mock_csv_path)
    hierarchy = result['hierarchy']
    
    # Check specific WTNB positions that should be populated
    wtnb_positions = [
        ('bowling', 'monday_wtnb', 'director'),
        ('dodgeball', 'wtnb_draft', 'director'),
        ('dodgeball', 'wtnb_social', 'director'),
        ('kickball', 'draft_wtnb', 'director'),
        ('pickleball', 'wtnb', 'director'),
    ]
    
    for section, team, role in wtnb_positions:
        position_data = hierarchy[section][team][role]
        assert position_data is not None, f"WTNB position {section}.{team}.{role} should not be null"
        assert position_data.get('name') != 'Vacant', f"WTNB position {section}.{team}.{role} should not be vacant"
        assert 'wtnb' in position_data.get('position', '').lower(), f"Position {section}.{team}.{role} should contain 'wtnb'"
    
    print(f"✅ All {len(wtnb_positions)} WTNB positions correctly matched")


def test_player_experience_positions(mock_csv_path):
    """Test that player experience positions are correctly categorized."""
    result = process_csv_to_hierarchy(mock_csv_path)
    hierarchy = result['hierarchy']
    
    # Check bowling player experience
    assert hierarchy['bowling']['player_experience']['open'] is not None
    assert hierarchy['bowling']['player_experience']['wtnb'] is not None
    
    # Check dodgeball player experience
    assert hierarchy['dodgeball']['player_experience']['open'] is not None  # Vacant
    assert hierarchy['dodgeball']['player_experience']['wtnb'] is not None
    
    # Check kickball player experience (has multiple 'open' positions)
    assert isinstance(hierarchy['kickball']['player_experience']['open'], list)
    assert len(hierarchy['kickball']['player_experience']['open']) == 2
    assert hierarchy['kickball']['player_experience']['wtnb'] is not None
    
    # Check pickleball player experience
    assert hierarchy['pickleball']['player_experience']['open'] is not None
    assert hierarchy['pickleball']['player_experience']['wtnb'] is not None
    
    print("✅ Player experience positions correctly categorized")


def test_committee_members_collected(mock_csv_path):
    """Test that committee members are collected as a simple list."""
    result = process_csv_to_hierarchy(mock_csv_path)
    hierarchy = result['hierarchy']
    
    committee = hierarchy.get('committee_members', [])
    
    assert isinstance(committee, list), "committee_members should be a list"
    assert len(committee) == 1, f"Expected 1 committee member, found {len(committee)}"
    
    # Check first committee member has required fields
    if len(committee) > 0:
        member = committee[0]
        assert 'position' in member
        assert 'position_key' in member
        assert member['position_key'] == 'volunteer_coordinator'
    
    print(f"✅ Committee members collected correctly ({len(committee)} member(s))")


if __name__ == '__main__':
    # Allow running tests directly
    pytest.main([__file__, '-v'])

